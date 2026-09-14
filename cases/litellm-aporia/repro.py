"""litellm: the Aporia guardrail acts on one of four verdicts and forwards the rest.

Source: litellm/proxy/guardrails/guardrail_hooks/aporia_ai/aporia_ai.py:128-139.

The line's own comment names the four values Aporia returns. Only `block`
raises. `modify` and `rephrase` are interventions, meaning the content should
not go out as written, and litellm forwards the original unmodified with a 200
and no log line marking a skipped verdict.

Reported: https://github.com/BerriAI/litellm/issues/41097
"""

TITLE = "litellm forwards content Aporia asked it to modify"
UPSTREAM = "https://github.com/BerriAI/litellm/issues/41097"


class _HTTPException(Exception):
    pass


def guard(json_response):
    """aporia_ai.py:131-139, structurally verbatim, with the source's own comment."""
    action = json_response.get("action")  # possible values are modify, passthrough, block, rephrase
    if action == "block":
        raise _HTTPException()
    return "FORWARDED UNMODIFIED"


CASES = [
    ("block", True, "the only handled verdict"),
    ("passthrough", False, "correct, allow"),
    ("modify", True, "Aporia says rewrite this before sending"),
    ("rephrase", True, "Aporia says rewrite this before sending"),
    ("BLOCK", True, "casing"),
    ("blocked", True, "past tense"),
    (None, True, "no action key, or an error object"),
]


def run():
    print("Aporia returns one of four verdicts. litellm handles one.\n")
    print("  %-16s %-24s %s" % ("verdict", "litellm does", "note"))
    failures = 0
    for action, should_block, note in CASES:
        payload = {} if action is None else {"action": action}
        try:
            got = guard(payload)
        except _HTTPException:
            got = "blocked"
        bad = should_block and got != "blocked"
        failures += bad
        print("  %-16r %-24s %s%s"
              % (action, got, note, "   <-- sent anyway" if bad else ""))
    print()
    if failures:
        print("%d verdict(s) that are not permission are treated as permission."
              % failures)
        print("The comment on that line names four values. The code handles one.")
        print()
        print("Vigil Guard in the same directory does the affirmative version:")
        print("  if decision not in _VALID_DECISIONS: <refuse>")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
