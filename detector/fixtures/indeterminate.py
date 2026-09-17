"""Shapes the checker should classify INDETERMINATE.

These are the honest limit of a single-file check. The emptiness question is
real in each case, but answering it needs the caller, which this checker
does not look at.
"""


def respond(results_valid):
    """The real llm-guard shape: the aggregate is in a different function
    from where the dict is built, so emptiness depends on the caller."""
    return {"is_valid": all(results_valid.values())}


def verdict_from_parameter(checks):
    """Aggregated straight off a parameter."""
    is_valid = all(checks)
    return is_valid


def reassigned_both_ways(flag, checks):
    """Assigned twice, one path possibly empty."""
    outcomes = []
    if flag:
        outcomes = [c.ok() for c in checks]
    allowed = all(outcomes)
    return allowed
