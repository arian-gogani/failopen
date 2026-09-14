"""openai-agents-python: a bad approval config raises in one runner and is ignored in the other.

Source: src/agents/util/_approvals.py:32-51, shared by the core runner and
realtime sessions.

The helper raises UserError when `needs_approval` is neither a bool nor a
callable, unless the caller passes strict=False, in which case it returns
`default` (False). The core runner at run_internal/tool_execution.py:1312 calls
it without strict, so it raises. realtime/session.py:662 passes strict=False,
and session.py:730 reads a False result as "proceed".

FunctionTool is a plain dataclass with no validation of needs_approval, so
nothing rejects the value where it is written.

This downloads the real helper and executes it rather than retyping it.

Reported: https://github.com/openai/openai-agents-python/issues/5024
"""

import asyncio
import types
import urllib.request

TITLE = "openai-agents skips tool approval on a misconfigured needs_approval"
UPSTREAM = "https://github.com/openai/openai-agents-python/issues/5024"

SRC = ("https://raw.githubusercontent.com/openai/openai-agents-python/main/"
       "src/agents/util/_approvals.py")

CASES = [
    (True, "bool, honoured by both"),
    (False, "bool, honoured by both"),
    ("always", "reads like a valid setting, and is truthy"),
    ("never", "a string"),
    (1, "an int"),
    (None, "unset"),
    ({"tool": "x"}, "a dict"),
]


def _load_shipped_helper():
    src = urllib.request.urlopen(SRC, timeout=30).read().decode("utf-8")
    mod = types.ModuleType("_approvals_shipped")
    mod.__dict__["UserError"] = type("UserError", (Exception,), {})
    body = src.replace("from ..exceptions import UserError", "")
    exec(compile(body, "_approvals.py", "exec"), mod.__dict__)
    return mod.evaluate_needs_approval_setting


async def _collect(ev):
    rows = []
    for value, note in CASES:
        try:
            core = "needs_approval=%s" % await ev(value, None, {}, "call1")
        except Exception as exc:
            core = "raises %s" % type(exc).__name__
        realtime = await ev(value, None, {}, "call1", strict=False)
        rows.append((value, core, realtime, note))
    return rows


def run():
    ev = _load_shipped_helper()
    print("lifted evaluate_needs_approval_setting verbatim from the shipped file\n")
    rows = asyncio.run(_collect(ev))

    print("  %-24s %-24s %s" % ("needs_approval", "core runner", "realtime session"))
    divergent = 0
    for value, core, realtime, note in rows:
        bad = "raises" in core and realtime is False
        divergent += bad
        print("  %-24r %-24s %s%s"
              % (value, core, "needs_approval=%s" % realtime,
                 "   <-- tool runs, no approval" if bad else ""))
    print()
    if divergent:
        print("%d value(s) are a fatal error on one path and 'no approval needed'"
              % divergent)
        print("on the other. Which behaviour you get depends on which runner you use,")
        print("and the quieter one is the permissive one.")
        print()
        print("The same file gets the adjacent case right: parse_function_tool_arguments")
        print("returns None when arguments cannot be inspected, and both call sites")
        print("treat None as approval required. Unreadable arguments fail closed.")
        print("An uninterpretable policy fails open.")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
