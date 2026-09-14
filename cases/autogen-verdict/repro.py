"""microsoft/autogen: a governance sample executes on any verdict it does not recognise.

Source: python/samples/agentchat_external_governance/main.py, PR #7960.

The sample asks an external governance service whether a high-risk action is
allowed, then branches on the answer. `deny` blocks, `require_approval` pauses,
and every other value falls through to execute. `json.loads` returns whatever
the service sent, so the Literal annotation on the verdict enforces nothing at
runtime.

Reported: https://github.com/microsoft/autogen/pull/7960
"""

import os

TITLE = "autogen governance sample executes on unrecognised verdicts"
UPSTREAM = "https://github.com/microsoft/autogen/pull/7960"


def governed_export(decision):
    """The decision block from main.py, lines 143-171, structurally verbatim."""
    if decision["verdict"] == "deny":
        return "blocked"
    if (
        decision["verdict"] == "require_approval"
        and os.environ.get("AUTO_APPROVE_EXTERNAL_GOVERNANCE") != "1"
    ):
        return "approval_required"
    return "EXECUTED"


CASES = [
    ("deny", "blocked", "the one spelling that works"),
    ("require_approval", "approval_required", "correct"),
    ("allow", "EXECUTED", "correct"),
    ("denied", "blocked", "past tense"),
    ("DENY", "blocked", "different casing"),
    ("block", "blocked", "a synonym the service might use"),
    ("error", "blocked", "an error object carrying a verdict key"),
    ("", "blocked", "empty string"),
]


def run():
    print("A governance service answers, and the sample decides:\n")
    print("  %-18s %-20s %s" % ("verdict", "sample does", "should"))
    failures = 0
    for verdict, should, note in CASES:
        got = governed_export({"verdict": verdict})
        bad = got != should
        failures += bad
        print("  %-18r %-20s %s%s"
              % (verdict, got, should, "   <-- customer records exported" if bad else ""))
    print()
    if failures:
        print("%d of %d verdicts export the records when they should not."
              % (failures, len(CASES)))
        print("Refusal needs an exact string match. Permission needs nothing.")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
