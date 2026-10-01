# Withdrawn current-defect claim: AutoGen governance sample

The initial revision of [AutoGen PR #7960](https://github.com/microsoft/autogen/pull/7960), commit
[`0cd67042`](https://github.com/microsoft/autogen/pull/7960/commits/0cd67042ab4bb65653c9ba454f9c3bd60b0829e0),
executed the sample action when the external verdict was `denied`, `DENY`,
`block`, `error`, empty, or `None`. The original branch-model reproduction
captures that historical behavior.

The contributor hardened the same PR in commit
[`ec6cf48c`](https://github.com/microsoft/autogen/pull/7960/commits/ec6cf48c026b1a879ef2063fbe5404482d40c873)
on September 14, 2026. The current PR head validates the response against
the allowed verdict set and the proposed action hash, then has a second
explicit non-permit check before the execution branch. The sample is still
in an **open PR**, not merged into AutoGen `main`.

On October 1, we fetched both pinned source revisions and executed the
`governed_export_customer_records` function from each using the same nine
verdict inputs. Six unknown verdicts executed in the initial revision; all
six blocked in the hardened head. The three recognized verdicts retained
their intended behavior. The local comparison script used AST extraction of
the real function and a stubbed checkpoint response, so it tests the branch
without requiring AutoGen or a network service.

Reproduce the comparison with `python3 historical/autogen-verdict/verify_revisions.py`.
It downloads the two pinned source files from GitHub and exits nonzero if
either revision's behavior changes or cannot be checked. It also exercises
the hardened response normalizer on the same six unknown values.

[Issue #8301](https://github.com/microsoft/autogen/issues/8301) was filed
after the hardening commit and incorrectly presented the flaw as current.
The issue and our earlier public case were wrong on timing. We should have
checked the current PR head before filing. This page preserves the mistake
and the correction. Do not cite the issue as evidence of an unresolved
AutoGen defect.
