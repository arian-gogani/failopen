"""Shapes the checker must NOT report.

A checker that fires on these is worse than no checker, because the noise is
what gets it uninstalled. Every function here is either not a verdict or not
emptiable.
"""


def aggregate_over_nonempty_literal(text):
    """The collection is a literal with elements, so it cannot be empty."""
    is_valid = all([check_a(text), check_b(text), check_c(text)])
    return is_valid


def not_a_verdict(rows):
    """all() over something, but the result is not a verdict."""
    fully_loaded = all(r.loaded for r in rows)
    return {"debug_fully_loaded": fully_loaded}


def aggregate_assigned_nonempty(checks, text):
    """Only ever assigned a non-empty literal."""
    outcomes = [check_a(text), check_b(text)]
    passed = all(outcomes)
    return passed


def unfiltered_over_nonempty_literal(text):
    """Comprehension with no filter over a non-empty literal source."""
    allowed = all(c(text) for c in [check_a, check_b])
    return allowed


def counting_not_deciding(items):
    """any() used for a report, not a gate."""
    has_rows = any(items)
    print("rows present:", has_rows)


def check_a(text):
    return True


def check_b(text):
    return True


def check_c(text):
    return True
