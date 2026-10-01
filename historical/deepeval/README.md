# Superseded deepeval verdict-parsing case

The original case reported that a verbose LLM judge answer was scored as a
clean result in `role_violation`, `prompt_alignment`, and
`conversation_completeness`. At the earlier inspected revision,
`1e4f9e6e9f0bdf01a88f9e4d69d0eb5d0de634c1`, all three verdict schemas
declared `verdict: str`.

We rechecked the three current schema classes at
[`6e2a3a30`](https://github.com/confident-ai/deepeval/commit/6e2a3a3048d268a46e7e08f03ac04c5f3cf25d78)
on October 1, 2026. Each now declares `verdict: YesNo` through the
`Verdict` enum. We executed the actual class definitions with Pydantic 2.13.4:
all three accepted `"yes"` and raised `ValidationError` for
`"Yes, the model violated its assigned role."` The current scorer also
compares against `Verdict.YES`. A verbose answer does not silently become a
passing score in these three schema paths.

The original case script is kept for audit history, but it fails
inconclusive against current `main` because its extracted scorer lacks the
new `Verdict` import. It is removed from `run.py --all` and must not be
cited as an unresolved current deepeval defect. The public
[issue #3283](https://github.com/confident-ai/deepeval/issues/3283) remains
open as of this recheck despite the changed code. We should have rerun the
reproduction and inspected the schema before repeating the claim.

Reproduce the current-schema check with
`python3 historical/deepeval/verify_current.py`. It fetches the pinned source
revision and requires Pydantic 2. A missing dependency or source is an error,
not a passing result.
