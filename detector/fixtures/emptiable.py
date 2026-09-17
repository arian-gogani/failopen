"""Shapes the checker should classify EMPTIABLE."""


def scan_and_verdict(scanners, text):
    """A dict that starts empty and is filled only inside a loop.

    This is the shape behind the confirmed llm-guard finding, collapsed into
    one function. If `scanners` is empty, results_valid stays {} and
    all({}.values()) is True.
    """
    results_valid = {}
    for scanner in scanners:
        results_valid[scanner.name] = scanner.check(text)
    is_valid = all(results_valid.values())
    return is_valid


def verdict_from_filtered(checks, text):
    """A comprehension whose filter can exclude every element."""
    passed = all(c.run(text) for c in checks if c.enabled)
    return passed


def verdict_from_empty_only(text):
    """Only ever assigned empty. Degenerate, but it should be caught."""
    findings = []
    allowed = all(findings)
    return allowed


def aggregate_into_attribute(self, checks, text):
    """Assigned to a verdict-shaped attribute rather than a local."""
    outcomes = []
    for c in checks:
        outcomes.append(c.ok(text))
    self.is_authorized = all(outcomes)
