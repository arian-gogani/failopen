# vacuous.py

Finds security verdicts computed by `all()` or `any()` over a collection that
can be empty.

```
python3 detector/vacuous.py path/to/your/code
```

`all([])` is `True`. When a verdict is aggregated that way over a collection
some configuration path can empty, the verdict reports success having
inspected nothing, and the response usually carries no field distinguishing
"checked and passed" from "nothing was checked".

This is one shape of the five in [../CWE-PROPOSAL.md](../CWE-PROPOSAL.md). It
is here rather than the other four for two reasons: it is the only one I
could find no existing CWE entry for, and it is the only one a static pass
decides well. The others are better served by CWE-390, CWE-697 and CWE-561,
and by reading.

## What it reports

Two classes, kept separate deliberately.

**EMPTIABLE**, the collection has a visible path to empty in this file. A
dict that starts `{}` and is filled only inside a loop, a comprehension with
a filter that can exclude everything, a name assigned empty on at least one
branch.

**INDETERMINATE**, the collection's emptiness cannot be decided from this
file alone, usually because it arrives as a parameter or a return value.

INDETERMINATE is not a quieter EMPTIABLE. It means the question is open and a
person has to answer it. Collapsing the two would make this tool commit the
defect it looks for, so it does not.

## Measured behaviour

Against the Python 3.14 standard library, 1,868 files:

```
scanned 1868 file(s): 0 emptiable, 8 indeterminate
```

Zero EMPTIABLE claims on mature, heavily reviewed code. The eight
indeterminates are all cases where a collection arrives from a caller, which
is the honest limit of a single-file check rather than a defect claim.

Against `protectai/llm-guard`, where a confirmed instance of this defect
lives:

```
llm_guard_api/app/app.py:248  all()  ->  INDETERMINATE
    `results_valid.values()` is not assigned in this function, so whether it
    can be empty depends on the caller
    verdict context: passed as `is_valid=`
```

Both real sites, 248 and 380, are reported. It reaches them as INDETERMINATE
rather than EMPTIABLE because the dict is built in `llm_guard/evaluate.py`
and aggregated in `app.py`, so proving emptiness needs both files. A reviewer
following that one pointer finds it in about a minute: `scan_prompt` returns
`results_valid` untouched when the scanner list is empty, and a
caller-supplied `scanners_suppress` can empty that list.

So on this finding the tool does the useful half, pointing at the line and
naming the question, and leaves the answer to a person.

## Yield so far

Run across four guardrail and evaluation products, 2,873 Python files:

```
4 products, 2,873 files    0 emptiable, 9 indeterminate
```

Zero EMPTIABLE across all four. Nine pointers. The per-product split is
withheld for now because one finding is under coordinated disclosure and
publishing the counts would narrow it to two candidates. It goes in when the
vendor has responded.

I read all nine. Seven are ordinary control flow that happens to use `any()`,
one is a module-level constant that cannot be empty, and **one is a real
defect**: a guardrail verdict function that returns "passed" when its
upstream API returns an empty result set, under that integration's default
strategy, with the outcome recorded as a successful check. It is with the
vendor under coordinated disclosure and is not named here or included in the
reproductions until they have responded.

That ratio is the honest pitch for this tool, and it is deliberately not
"it finds bugs". It found nothing it could confirm by itself. What it did was
turn 2,873 files into nine lines worth reading, one of which was worth
reporting. A checker that claimed the other eight were bugs would have been
useless; a checker that stayed silent would have missed the ninth.

## What it does not do

It does not do cross-file analysis, so the most realistic version of this
defect lands in INDETERMINATE rather than EMPTIABLE.

It does not understand enclosing guards beyond `if coll:`, `if coll and ...`,
and `len(coll)` compared against an integer. It used to report one false
positive in `asyncio/base_events.py`, where an `all()` sits inside
`elif exceptions:` and therefore cannot be vacuous. That case is handled now.
Subtler proofs of non-emptiness are not recognised, which means the finding
stands and you decide.

The verdict-name list is deliberately narrow. Widening it is the fastest way
to turn this into noise, and a noisy checker gets uninstalled.

It checks Python only.

## Fixtures

`fixtures/` is the test corpus, and running the tool against it is the test:

```
python3 detector/vacuous.py detector/fixtures/emptiable.py      # 4 emptiable
python3 detector/vacuous.py detector/fixtures/indeterminate.py  # 1 emptiable, 2 indeterminate
python3 detector/vacuous.py detector/fixtures/clean.py          # 0, must stay 0
```

`clean.py` is the important one. Every function in it is either not a verdict
or not emptiable, and a change that makes it report anything has made the
tool worse regardless of what else it caught.

One fixture is worth calling out. `indeterminate.py` contains
`reassigned_both_ways`, which I wrote expecting INDETERMINATE and which the
tool classifies EMPTIABLE. The tool is right and my expectation was wrong:
the variable is assigned `[]` and then reassigned only inside an `if`, so the
falsy path really does leave the aggregate vacuous. It stays in that file as
a reminder that the fixture is not the oracle.
