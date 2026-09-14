"""deepeval: a judge that explains itself is scored as reporting no problem.

Source: deepeval/metrics/role_violation/role_violation.py:285-295, and the same
shape in prompt_alignment and conversation_completeness.

Three metrics declare `verdict: str` rather than Literal["yes","no"], compare
it with an exact match, and fall through to the permissive branch. `toxicity`,
`bias` and `hallucination` use Literal and so reject a verbose verdict loudly.

This downloads the real file and executes the shipped `_calculate_score` body
rather than a retyped copy, so the logic under test is the logic they ship.

Reported: https://github.com/confident-ai/deepeval/issues/3283
"""

import re
import urllib.request

TITLE = "deepeval scores a verbose judge verdict as a pass"
UPSTREAM = "https://github.com/confident-ai/deepeval/issues/3283"

SRC = ("https://raw.githubusercontent.com/confident-ai/deepeval/main/"
       "deepeval/metrics/role_violation/role_violation.py")

CASES = [
    ("yes", 0.0, "bare token, caught"),
    ("Yes", 0.0, "casing handled by .lower()"),
    ("YES", 0.0, "casing handled"),
    (" yes ", 0.0, "whitespace handled by .strip()"),
    ("Yes, the model violated its assigned role.", 0.0, "a judge that explains itself"),
    ("yes - the assistant claimed to be a human doctor", 0.0, "a judge that cites evidence"),
    ("no", 1.0, "correct"),
]


class _Verdict:
    """Stands in for RoleViolationVerdict, whose schema declares `verdict: str`."""

    def __init__(self, v):
        self.verdict = v


def _load_shipped_score_fn():
    src = urllib.request.urlopen(SRC, timeout=30).read().decode("utf-8")
    m = re.search(r"    def _calculate_score\(self\) -> float:\n(.*?)\n    @property",
                  src, re.S)
    if not m:
        raise SystemExit("could not locate _calculate_score; upstream may have moved")
    ns = {}
    exec("def _calculate_score(self):\n" + m.group(1), ns)
    return ns["_calculate_score"], len(m.group(1).splitlines())


def run():
    calc, nlines = _load_shipped_score_fn()
    print("lifted %d lines of _calculate_score verbatim from the shipped file\n" % nlines)

    holder = type("S", (), {})()
    print("  %-48s %-7s %s" % ("judge verdict", "score", "meaning"))
    failures = 0
    for verdict, expected, note in CASES:
        holder.verdicts = [_Verdict(verdict)]
        score = calc(holder)
        bad = score != expected
        failures += bad
        meaning = "violation caught" if score == 0.0 else "scored as full adherence"
        print("  %-48r %-7.1f %s%s"
              % (verdict, score, meaning, "   <-- wrong" if bad else ""))
    print()
    if failures:
        print("%d verdict(s) reporting a violation were scored as full adherence."
              % failures)
        print("A judge answering in a sentence rather than a bare token is read")
        print("as reporting no violation.")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
