#!/usr/bin/env python3
"""Find security verdicts computed by all() or any() over a collection that
can be empty.

    python3 detector/vacuous.py <path>

`all([])` is True and `any([])` is False. When a verdict is aggregated with
all() over a collection some configuration path can empty, the verdict
reports success having inspected nothing, and the response carries no field
distinguishing "checked and passed" from "nothing was checked".

This checks one shape. It is the shape that, of the five recorded in
CWE-PROPOSAL.md, has no existing CWE entry and is mechanically detectable.
The other four are better served by CWE-390, CWE-697 and CWE-561, and by
reading.

Two report classes, kept separate on purpose:

  EMPTIABLE    the argument has a visible path to empty in this file
  INDETERMINATE  the argument's emptiness cannot be decided from this file

INDETERMINATE is not a softer EMPTIABLE. It means the question is open and
a person has to answer it. A checker that collapsed the two would be
committing the defect it looks for.

Exit codes: 0 nothing found, 1 findings, 2 could not run.
"""

import ast
import pathlib
import sys

# A verdict-shaped name. Deliberately narrow: broadening this is the fastest
# way to turn the tool into noise, and a noisy checker gets uninstalled.
VERDICT_WORDS = (
    "valid", "invalid", "pass", "passed", "passing", "allow", "allowed",
    "safe", "authoriz", "authoris", "permit", "permitted", "grant", "granted",
    "approv", "approved", "compliant", "verdict", "ok",
)

AGGREGATORS = ("all", "any")


def _is_verdict_name(name):
    if not name:
        return False
    low = name.lower()
    return any(w in low for w in VERDICT_WORDS)


class _Finding:
    def __init__(self, path, node, agg, reason, verdict_ctx, certainty):
        self.path = path
        self.line = node.lineno
        self.col = node.col_offset
        self.agg = agg
        self.reason = reason
        self.verdict_ctx = verdict_ctx
        self.certainty = certainty

    def __str__(self):
        return (
            "%s:%d  %s()  ->  %s\n"
            "    %s\n"
            "    verdict context: %s"
            % (self.path, self.line, self.agg, self.certainty,
               self.reason, self.verdict_ctx)
        )


class _Scope:
    """Assignments seen in one function body, enough to answer 'can this be
    empty' for the common cases without whole-program analysis."""

    def __init__(self):
        self.assigned = {}   # name -> list of assigned value nodes
        self.mutated = set()  # names that got .append/.update/[k]= etc

    def record_assign(self, name, value):
        self.assigned.setdefault(name, []).append(value)

    def record_mutation(self, name):
        self.mutated.add(name)


def _empty_literal(node):
    """True if node is a literal empty container."""
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and not node.elts:
        return True
    if isinstance(node, ast.Dict) and not node.keys:
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("list", "dict", "set", "tuple") and not node.args:
            return True
    return False


def _nonempty_literal(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and node.elts:
        return True
    if isinstance(node, ast.Dict) and node.keys:
        return True
    return False


def _describe(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _base_name(arg):
    """The name of the collection being aggregated, if there is one."""
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
        if arg.func.attr in ("values", "keys", "items") \
                and isinstance(arg.func.value, ast.Name):
            return arg.func.value.id
        return None
    if isinstance(arg, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        if arg.generators:
            return _base_name(arg.generators[0].iter)
    return None


def _guards_nonempty(test, name):
    """True if `test` establishes that `name` is non-empty.

    Covers `if name:`, `if len(name) > 0:`, `if len(name) == 1:` and
    `if name and ...`. Anything subtler is not recognised, which means the
    finding stands and a person decides.
    """
    if name is None:
        return False
    if isinstance(test, ast.Name) and test.id == name:
        return True
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return any(_guards_nonempty(v, name) for v in test.values)
    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Call):
        f = test.left.func
        if isinstance(f, ast.Name) and f.id == "len" and test.left.args:
            a = test.left.args[0]
            if _base_name(a) == name:
                for op, comp in zip(test.ops, test.comparators):
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, int):
                        if isinstance(op, ast.Gt) and comp.value >= 0:
                            return True
                        if isinstance(op, (ast.Eq, ast.GtE)) and comp.value >= 1:
                            return True
    return False


DENY_WORDS = ("deny", "denied", "block", "blocked", "reject", "rejected",
              "forbid", "refuse", "refused", "unauthor", "abort", "raise")


def _denies(body):
    """True if this branch looks like it refuses something.

    Deliberately conservative. A branch that raises, or that returns a
    falsy/deny-shaped value, is treated as a denial; anything else is not.
    """
    for node in body or []:
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Return):
            v = node.value
            if v is None:
                continue
            if isinstance(v, ast.Constant) and v.value in (False, None):
                return True
            txt = _describe(v).lower()
            if any(w in txt for w in DENY_WORDS):
                return True
        if isinstance(node, (ast.If, ast.With, ast.Try)):
            if _denies(getattr(node, "body", None)):
                return True
    return False


def _walk_own_body(fnnode):
    """Yield nodes belonging to this function, not to functions nested in it.

    Without this, a nested `def` is visited once as part of its parent's
    subtree and once in its own right, and every finding inside it is
    reported twice.
    """
    stack = list(ast.iter_child_nodes(fnnode))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.Lambda, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _analyse_iterable(arg, scope):
    """Return (certainty, reason) for the aggregated iterable.

    certainty is 'EMPTIABLE', 'INDETERMINATE', or None to skip.
    """
    # all(x for x in y if cond) -- the filter can exclude everything.
    if isinstance(arg, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        for gen in arg.generators:
            if gen.ifs:
                return ("EMPTIABLE",
                        "comprehension has a filter (%s), which can exclude "
                        "every element, leaving the aggregate vacuous"
                        % _describe(gen.ifs[0]))
        # No filter: emptiness follows the source being iterated.
        src = arg.generators[0].iter if arg.generators else None
        if src is not None:
            inner = _analyse_iterable(src, scope)
            if inner[0] is None:
                return (None, "")
            return (inner[0],
                    "comprehension has no filter, so it is empty exactly when "
                    "its source is; source: " + inner[1])
        return ("INDETERMINATE", "comprehension over an unresolved source")

    # all(d.values()) -- empty dict gives an empty view.
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
        if arg.func.attr in ("values", "keys", "items"):
            base = arg.func.value
            if isinstance(base, ast.Name):
                return _analyse_name(base.id, scope, via=".%s()" % arg.func.attr)
            return ("INDETERMINATE",
                    "%s() on an expression this checker cannot resolve"
                    % arg.func.attr)
        return (None, "")

    if isinstance(arg, ast.Name):
        return _analyse_name(arg.id, scope)

    if _empty_literal(arg):
        return ("EMPTIABLE", "aggregates a literal empty collection")

    if _nonempty_literal(arg):
        return (None, "")

    return (None, "")


def _analyse_name(name, scope, via=""):
    label = name + via
    values = scope.assigned.get(name)
    if values is None:
        return ("INDETERMINATE",
                "`%s` is not assigned in this function, so whether it can be "
                "empty depends on the caller" % label)

    starts_empty = any(_empty_literal(v) for v in values)
    has_nonempty = any(_nonempty_literal(v) for v in values)

    if starts_empty and name in scope.mutated:
        return ("EMPTIABLE",
                "`%s` starts empty and is filled conditionally, so a path "
                "that fills nothing leaves the aggregate vacuous" % label)
    if starts_empty and len(values) == 1:
        return ("EMPTIABLE", "`%s` is only ever assigned empty" % label)
    if starts_empty:
        return ("EMPTIABLE",
                "`%s` is assigned empty on at least one path (%d assignments "
                "seen), and that path leaves the aggregate vacuous"
                % (label, len(values)))
    if has_nonempty:
        return (None, "")
    return ("INDETERMINATE",
            "`%s` is assigned from an expression this checker cannot decide "
            "emptiness for" % label)


class _FunctionChecker(ast.NodeVisitor):
    def __init__(self, path, findings):
        self.path = path
        self.findings = findings
        self.scope = _Scope()

    # -- collect assignments and mutations first -----------------------------
    def collect(self, fnnode):
        for node in _walk_own_body(fnnode):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.scope.record_assign(t.id, node.value)
                    elif isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                        self.scope.record_mutation(t.value.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value is not None:
                    self.scope.record_assign(node.target.id, node.value)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    self.scope.record_mutation(node.target.id)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("append", "extend", "update", "add",
                                      "setdefault", "insert", "pop", "remove"):
                    if isinstance(node.func.value, ast.Name):
                        self.scope.record_mutation(node.func.value.id)

    # -- then look for aggregated verdicts -----------------------------------
    def check(self, fnnode):
        parents = {}
        for parent in _walk_own_body(fnnode):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        for node in _walk_own_body(fnnode):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in AGGREGATORS
                    and len(node.args) == 1):
                continue
            ctx = self._verdict_context(fnnode, node)
            if ctx is None:
                continue
            certainty, reason = _analyse_iterable(node.args[0], self.scope)
            if certainty is None:
                continue
            # An enclosing `if coll:` / `elif coll:` already proves the
            # collection is non-empty, so the aggregate cannot be vacuous.
            if self._guarded(node, _base_name(node.args[0]), parents):
                continue
            self.findings.append(
                _Finding(self.path, node, node.func.id, reason, ctx, certainty))

    @staticmethod
    def _guarded(call, name, parents):
        if name is None:
            return False
        cur = call
        while cur in parents:
            parent = parents[cur]
            if isinstance(parent, ast.If) and cur is not parent.test:
                if _guards_nonempty(parent.test, name):
                    return True
            cur = parent
        return False

    def _verdict_context(self, fnnode, call):
        """Return a description if this aggregate feeds a verdict, else None."""
        for node in _walk_own_body(fnnode):
            # verdict = all(...)
            if isinstance(node, ast.Assign) and node.value is call:
                for t in node.targets:
                    if isinstance(t, ast.Name) and _is_verdict_name(t.id):
                        return "assigned to `%s`" % t.id
                    if isinstance(t, ast.Attribute) and _is_verdict_name(t.attr):
                        return "assigned to `.%s`" % t.attr
            # f(is_valid=all(...))
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.value is call and _is_verdict_name(kw.arg):
                        return "passed as `%s=`" % kw.arg
            # {"is_valid": all(...)} -- the shape the llm-guard finding took,
            # where the verdict is a response field rather than a variable.
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if v is call and isinstance(k, ast.Constant) \
                            and isinstance(k.value, str) \
                            and _is_verdict_name(k.value):
                        return "dict value under key `%s`" % k.value
            # return all(...) -- only counts if the function itself is named
            # like a verdict. Without this restriction every `return all(...)`
            # in a codebase is a finding, which is noise.
            if isinstance(node, ast.Return) and node.value is call:
                if _is_verdict_name(getattr(fnnode, "name", "")):
                    return "returned from `%s()`" % fnnode.name
            # if all(...): ... -- only counts when the branch actually denies
            # something. `if any(x for x in y)` as ordinary control flow is
            # not a verdict and must not be reported.
            if isinstance(node, ast.If) and node.test is call:
                if _denies(node.body) or _denies(node.orelse):
                    return "`if` condition guarding a denial"
        return None


def check_source(src, path):
    findings = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print("%s: could not parse (%s)" % (path, e), file=sys.stderr)
        return findings, False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            c = _FunctionChecker(path, findings)
            c.collect(node)
            c.check(node)
    return findings, True


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    root = pathlib.Path(argv[1])
    files = [root] if root.is_file() else sorted(root.rglob("*.py"))
    if not files:
        print("no python files under %s" % root, file=sys.stderr)
        return 2

    all_findings = []
    parsed = 0
    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found, ok = check_source(src, str(f))
        parsed += 1 if ok else 0
        all_findings.extend(found)

    emptiable = [f for f in all_findings if f.certainty == "EMPTIABLE"]
    indet = [f for f in all_findings if f.certainty == "INDETERMINATE"]

    for group, label in ((emptiable, "EMPTIABLE"), (indet, "INDETERMINATE")):
        if not group:
            continue
        print("=" * 72)
        print("%s (%d)" % (label, len(group)))
        print("=" * 72)
        for f in group:
            print(f)
            print()

    print("scanned %d file(s): %d emptiable, %d indeterminate"
          % (parsed, len(emptiable), len(indet)))
    if indet and not emptiable:
        print("Nothing decided. INDETERMINATE means a person has to answer "
              "the emptiness question, not that the code is fine.")
    return 1 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
