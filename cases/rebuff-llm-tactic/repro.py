"""protectai/rebuff: the LLM detection tactic's score is a raw parseFloat of a
model completion, and an unparseable reply is silently scored as "not
detected" rather than raising or flagging indeterminate.

Source, structurally verbatim from the shipped file:
  javascript-sdk/src/tactics/OpenAI.ts, OpenAI.execute()
  javascript-sdk/src/sdk.ts, Rebuff.detectInjection()

The tactic asks the model to reply with "only a single floating point
number". OpenAI.ts then does:

    // FIXME: Handle when parseFloat returns NaN.
    const score = parseFloat(completion.data.choices[0].message.content || "");
    return { score };

sdk.ts computes detected as `execution.score > threshold`. In JavaScript,
NaN > threshold is always false. So a completion parseFloat cannot parse at
all, a refusal, an explanation, markdown, an empty string, silently becomes
"not detected" instead of an error or an indeterminate result. The FIXME
comment is the developer's own record that this was known and never fixed.

Not reported: the repository has been archived since 2024-08-07, more than
two years before this was found, and no SECURITY.md was ever added to it.
There is no channel this could have gone through.

Severity note this case does not overstate: detectInjection runs three
independent tactics (Heuristic, Vector, this one) and ORs their verdicts, so
a malformed completion degrades this one layer to a false negative rather
than disabling detection outright. The other two tactics still run on the
same input.

https://github.com/protectai/rebuff/blob/main/javascript-sdk/src/tactics/OpenAI.ts
https://github.com/protectai/rebuff/blob/main/javascript-sdk/src/sdk.ts
"""

import math
import re

TITLE = "rebuff: an unparseable LLM completion silently scores as not-detected"
UPSTREAM = "not reported -- archived since 2024, no SECURITY.md was ever added"


def js_parse_float(text):
    """Python stand-in for JavaScript's parseFloat: parses the leading
    numeric prefix after leading whitespace, and returns NaN when no
    prefix is a valid number, matching JS semantics closely enough for
    this trace."""
    match = re.match(r'\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?', text)
    if not match or not match.group(0).strip():
        return float("nan")
    try:
        return float(match.group(0))
    except ValueError:
        return float("nan")


def openai_tactic_execute(model_reply, threshold=0.9):
    """OpenAI.execute(), structurally verbatim: parse, return a score."""
    score = js_parse_float(model_reply)
    return score


def detect_injection(model_reply, threshold=0.9):
    """sdk.ts's `execution.score > threshold`, the exact comparison."""
    score = openai_tactic_execute(model_reply, threshold)
    return score > threshold  # NaN > threshold is always False


CASES = [
    ("0.98", True, "the model followed instructions exactly"),
    ("The score is 0.98.", False, "parseFloat only reads from position 0: NaN"),
    ("I cannot provide a numeric score for this input.", False, "no leading number: NaN"),
    ("**0.98**", False, "markdown asterisks before the digit: NaN"),
    ("", False, "empty completion: NaN"),
]


def run():
    print("A model completion, and what the LLM tactic decides:\n")
    print("  %-55s %-10s %s" % ("completion", "detected", "note"))
    anomalies = 0
    for reply, expected_pattern_break, note in CASES:
        detected = detect_injection(reply)
        flag = ""
        if not detected and "NaN" in note:
            anomalies += 1
            flag = "   <-- silently scored as safe"
        print("  %-55r %-10s %s%s" % (reply, detected, note, flag))
    print()
    if anomalies:
        print("%d of %d completions produce NaN, and NaN > threshold is always"
              " False in both JavaScript and here." % (anomalies, len(CASES)))
        print("A refusal or a markdown-wrapped number scores identically to a")
        print("clean below-threshold result: not detected.")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
