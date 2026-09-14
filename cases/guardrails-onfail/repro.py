"""guardrails-ai: the config file path defaults to doing nothing, the Python API defaults to raising.

Source:
  guardrails/validator_base.py:139-140   on_fail defaults to OnFailAction.EXCEPTION
  guardrails/schema/rail_schema.py:50-52 on_fail defaults to OnFailAction.NOOP

Same library, same validator, opposite defaults depending on how it was
declared. The RAIL path is also keyed on an alias transformation, so an
attribute name that looks right can miss and resolve to NOOP: the validator
runs, detects the violation, and does nothing. Nothing warns.

Reported: https://github.com/guardrails-ai/guardrails/issues/1656
"""

TITLE = "guardrails-ai RAIL config silently downgrades a validator to a no-op"
UPSTREAM = "https://github.com/guardrails-ai/guardrails/issues/1656"

NOOP, EXCEPTION = "noop", "exception"


def resolve(xml_attr, rail_alias):
    """rail_schema.py:44 builds handlers from the attribute name.
    rail_schema.py:50-52 looks them up by rail_alias.replace("/", "_"), default NOOP.
    """
    handlers = {xml_attr[len("on-fail-"):]: EXCEPTION}
    return handlers.get(rail_alias.replace("/", "_"), NOOP)


CASES = [
    ("on-fail-two-words", "two-words", EXCEPTION, "matches"),
    ("on-fail-valid-length", "valid_length", EXCEPTION, "underscored alias, hyphenated attribute"),
    ("on-fail-toxic-language", "guardrails/toxic_language", EXCEPTION, "namespaced alias"),
    ("on-fail-guardrails_toxic_language", "guardrails/toxic_language", EXCEPTION, "the spelling that works"),
]


def run():
    print("Python API, validator_base.py:139-140: on_fail defaults to %s" % EXCEPTION)
    print("RAIL config,  rail_schema.py:50-52:    on_fail defaults to %s\n" % NOOP)
    print("  %-36s %-30s %s" % ("XML attribute written", "validator rail_alias", "resolved"))
    failures = 0
    for attr, alias, expected, note in CASES:
        got = resolve(attr, alias)
        bad = got != expected
        failures += bad
        print("  %-36s %-30s %s%s"
              % (attr, alias, got, "   <-- validator becomes a no-op" if bad else ""))
    print()
    if failures:
        print("%d attribute spelling(s) that look correct resolve to %s."
              % (failures, NOOP))
        print("The validator still runs and still detects the violation. It just")
        print("does nothing about it, and a miss is not an error.")
        print()
        print("Either default is defensible alone. Having two is the problem, and")
        print("the permissive one is reached by the format aimed at people who are")
        print("not writing Python.")
        return True
    print("No divergence. The defect did not reproduce.")
    return False
