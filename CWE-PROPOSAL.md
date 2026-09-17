# Draft CWE proposal: a protection mechanism that executes, reports success, and never evaluates its decision condition

Status: draft for discussion in the CWE AI Working Group. Not submitted.
Written to be argued with. Sections I am least sure of are marked.

## Name

Three options, no strong preference. Naming is the group's call.

1. Vacuous Satisfaction of a Protection Mechanism's Decision Condition
2. Unevaluated Decision Condition in a Protection Mechanism
3. Protection Mechanism Reports Success Without Evaluating Its Condition

"Vacuous" is the technically precise term: a comparison that never executes
is vacuously satisfied in the same sense that `all([])` is `True`, and one
confirmed instance is literally that expression. Precise and useful are not
always the same thing, so options 2 and 3 trade accuracy for readability.

## Description

The product implements a protection mechanism that executes on every
request and reports a permissive result, because the comparison that
decides the outcome silently fails to evaluate, is unreachable, or cannot
reach the value it is meant to inspect.

## Extended description

This is distinct from a protection mechanism that is missing, disabled, or
bypassed, and distinct from one whose logic is incorrect. Here the
mechanism is present, configured, invoked, and observably running. It
returns the result that means "permitted" without the deciding comparison
ever having been evaluated against the value in question.

The practical consequence is that every signal an operator would normally
rely on indicates health. The check appears in traces and logs. Code
coverage marks the deciding line as covered, because the line executes.
Unit tests pass, because they are written from the same understanding of
the value space as the code. Type annotations appear to constrain the
compared value, but the value arrives from `json.loads`, a subprocess, or
a model completion, so the annotation documents an intent that nothing
enforces at runtime.

A maintainer receiving a report of this class currently has no identifier
to map it to. The distinction that matters to them is between "this is
documented as dangerous" and "this claims to check and does not," and that
distinction has no name.

## Related weaknesses

- **ChildOf CWE-693** (Protection Mechanism Failure). 693's extended
  description does cover "ignored mechanisms where available protections
  aren't applied in certain code paths," which is adjacent. But that is
  prose in a parent entry rather than a classified weakness, and none of
  693's 18 children describes a mechanism that runs and reports success
  without evaluating. Checked against CWE 4.20.
- **PeerOf CWE-697** (Incorrect Comparison). 697 covers a comparison that
  is performed incorrectly. This class covers a comparison that is not
  performed at all, or is performed against an operand that cannot carry
  the answer. Several instances are arguably both, and the boundary
  between them is the part of this proposal I am least confident about.
- **PeerOf CWE-184** (Incomplete List of Disallowed Inputs). Where the
  unevaluated condition is a blocklist match, the two overlap. 184 is the
  better fit when the list is merely incomplete; this class is the better
  fit when the matching logic cannot see the input at all.
- **Not CWE-1288** (Improper Validation of Consistency within Input).
  1288 concerns consistency between input elements, not a comparison that
  fails to evaluate.
- **Not CWE-754** (Improper Check for Unusual or Exceptional Conditions).
  754 covers checks that are missing or that fail to consider a condition.
  This class covers a check that is present, configured and executing. I
  raise it explicitly because I invited this comparison myself and it is
  the most likely place a reviewer would try to file this.

## Prior art found on re-check, and how it narrows the class

I originally scoped this against CWE-693's children plus 697, 184 and 1288.
That was too narrow a search, and a broader pass found existing homes for
some of the five forms below. Recording the result rather than the
conclusion I wanted:

- **Form 4 is substantially CWE-390** (Detection of Error Condition Without
  Action, ChildOf CWE-755). An `except` that logs and returns, leaving the
  caller to read a permissive default, is what 390 describes. Two of the
  confirmed instances are textbook 390 and should be mapped there rather
  than counted as novel.
- **Form 2 may simply be CWE-697** (Incorrect Comparison). In this form the
  comparison does execute; it just cannot match, because the value's
  runtime domain is wider than the literal it is tested against. Calling
  that "never evaluated" overstates it. I now think 697 is the honest
  mapping and that the interesting part is a documentation note about
  unconstrained values from deserializers and model output, not a new
  entry.
- **Form 1 overlaps CWE-561** (Dead Code) at the mechanism level. An `elif`
  made unreachable by its enclosing conditional is dead code. 561 does not
  carry the security consequence, but the mechanism is not novel.

What survives as genuinely unmapped is narrower than the original framing:
the cases where nothing is evaluated at all and the mechanism still returns
the permissive result. Form 1 and Form 5 are the clearest, Form 5 most of
all, since `all([])` returning `True` means the aggregate reports success
having inspected nothing, and no existing entry I found names a vacuously
satisfied security aggregate.

So there are two defensible readings and I do not think the choice is mine:

1. **Five mappings, not one entry.** Forms 1 through 4 map to 561, 697, an
   inconsistency pattern, and 390 respectively, and only Form 5 needs new
   content. This is the conservative reading and it may be correct.
2. **One entry organized by consequence.** What the five share is not a
   mechanism but an outcome: a protection mechanism affirmatively reports
   that enforcement occurred when it did not, which is why it survives
   review, tests, coverage and monitoring. 697, 390 and 561 are all
   mechanism-level entries and none of them carries that consequence. CWE
   does have entries organized around consequence, so this reading is
   available, but it is a harder case to make and it should be made by
   someone with submission experience rather than asserted by me.

I lean toward reading 2 and I am aware that is the reading which favours my
own candidate, which is a reason to discount my lean rather than to trust
it.

## Applicable platforms

Language-independent. Observed instances are in Python, TypeScript, Go and
Rust. Concentrated in enforcement, authorization, approval-gating and
content-filtering code rather than in application logic generally.

## Common consequences

- Scope: Access Control. Impact: Bypass Protection Mechanism.
- Scope: Integrity. Impact: Execute Unauthorized Code or Commands, where
  the unevaluated condition gates command or tool execution.
- Scope: Non-Repudiation. Impact: Hide Activities. The permissive result
  is recorded as a successful check, so audit records affirmatively state
  that enforcement occurred.

The third consequence is the one that distinguishes this class from a
missing check. A missing control is visible in review. A control that runs,
passes CI, and evaluates nothing is not, and it produces evidence that it
worked.

## Observed structural forms

Five forms recur. Each is drawn from a confirmed, reproduced instance.

**1. A conditional bound to the wrong enclosing conditional.**

```python
if self.category_thresholds is not None:
    if category_scores is not None:
        ...per-category threshold checks...
elif flagged is True:
    raise HTTPException(...)
return
```

The `elif` binds to the outer `if`, not the inner one. Once any per-category
threshold is configured, the global `flagged` verdict becomes unreachable
for every other category. Configuring one category silently disables the
catch-all for the rest.

**2. An unconstrained verdict compared by equality, with the permissive
branch as the fallthrough.**

```python
if verdict == "deny":
    return blocked
return allowed
```

`verdict` is typed `str` and arrives from a model completion or a provider
response. `"denied"`, `"DENY"`, `"block"`, `""` and `None` all reach
`allowed`. Refusal requires an exact match; permission requires nothing.

**3. Two code paths to one decision with opposite defaults.**

The same validation helper is called with `strict=True` from one runner,
where invalid configuration raises, and `strict=False` from another, where
it returns the value meaning "no approval needed." Identical input, opposite
outcome, and the quieter path is the permissive one.

**4. An error path that omits the field the verdict logic reads.**

```python
# success path
return {"verdict": v, "fail_on_error": cfg.get("failOnError", False)}
# error path
return {"error": str(e)}          # fail_on_error absent

# verdict computation
passed = result.verdict or (result.error and not result.fail_on_error)
```

For an errored check, `not None` is `True`, so the whole expression is
truthy and the failed check counts as passing, even with `failOnError`
set. A variant of this form swallows the exception entirely and returns an
empty result set, which a downstream aggregator reads as "nothing found."

**5. An aggregation over a collection a configuration path can empty.**

`all([])` is `True`. Where a caller-supplied parameter can remove every
configured check, the aggregate verdict reports success with zero checks
having run, and the response carries no field distinguishing "checked and
passed" from "nothing was checked."

## Detection methods

**Automated static analysis, partial.** Forms 1, 4 and 5 have mechanical
signatures: an `elif` whose enclosing conditional makes it unreachable
under a configuration predicate; a return along an exception path that
omits a key the caller dereferences; `all()` or `any()` over a collection
with a reachable empty state. Form 2 is detectable with taint analysis
where the compared value originates from a deserializer or an external
call and its declared type is unconstrained.

Effectiveness: Moderate. Reported as such because this is a claim about
what is mechanizable in principle, and I have implemented only one of
these signatures. I would rather understate it.

**Manual analysis, effective but unscalable.** Most confirmed instances
were found by reading enforcement code and asking, for each comparison,
what else the compared value can be.

**Mutation testing, the strongest available check.** Disable the guard or
re-plant the defect deliberately and confirm that some test fails. A guard
that has never caught a re-planted instance of the defect it exists to
catch is not demonstrated to work. Applied to the confirmed instances,
this is what distinguishes them from a reading: in several cases the
project's own test suite stayed green with the defect present.

## Potential mitigations

- **Phase: Architecture and Design.** Make the permissive outcome require
  an affirmative, evaluated decision rather than being the absence of a
  refusal. Represent "not evaluated" as a distinct third state that the
  caller must handle, rather than collapsing it into "permitted."
- **Phase: Implementation.** Constrain the compared value at the boundary
  where it enters the process, not at the point of comparison. A
  `Literal["allow","deny"]` annotation on a value from `json.loads`
  documents an intent that is not enforced; validating at deserialization
  enforces it.
- **Phase: Testing.** For every guard, add a test that re-plants the
  defect and asserts the guard fires. Assert on the guard's own verdict,
  not only on the end-to-end outcome, since an unrelated component can
  produce the correct end state while the guard does nothing.
- **Phase: Operation.** Emit "evaluated" and "outcome" as separate
  signals. A mechanism that cannot distinguish "ran and permitted" from
  "ran and evaluated nothing" cannot be monitored for this class.

## Observed examples

This section is currently thin, and that is the main weakness of the
proposal as it stands.

- One credited advisory, `GHSA-vchv-45fj-59x7`, state triage at time of
  writing. Form 1.
- Four instances filed as public issues rather than through coordinated
  disclosure, which forfeited the credited-instance trail that this
  section wants. That was my error and it is not recoverable for those
  four.
- Several further instances are with vendors and unsubmitted.

The honest remedy is time rather than argument: route the remaining
instances through coordinated disclosure so there are identifiers to cite.
I would rather this entry go up later with three or four solid observed
examples than now with one.

## Prevalence

Reproductions and the measurement write-up, including what the numbers do
not support, are in this repository. Summary as published:

- Zero findings across 1,128,865 lines of mature reviewed Python
  (certbot, bandit, pyjwt, sigstore-python, python-tuf, detect-secrets),
  using a detector covering one of the five forms above. The zero bounds
  that one form, not the class.
- Fourteen findings across thirty-six projects whose enforcement code is
  roughly eighteen months old or younger, twenty-two of which were read
  and found clean. Found by reading, not by the detector.
- The thirty-six-project sample was selected for having enforcement code
  worth reading, so the rate is an observation about a chosen sample and
  not a population estimate.

Read together these support a narrower claim than "this is everywhere":
the class is reviewed out of mature codebases and concentrates in
enforcement layers written recently and quickly.

## References

- CWE-693, Protection Mechanism Failure, and its child list, CWE 4.20.
- CWE-697, Incorrect Comparison.
- CWE-184, Incomplete List of Disallowed Inputs.
- Reproductions: https://github.com/arian-gogani/failopen
- Measurement and stated limits: MEASUREMENT.md in the same repository.

## Submitter

Arian Gogani, goganiarian@gmail.com, github.com/arian-gogani.
No prior CWE submission experience.
