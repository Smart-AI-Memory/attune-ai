"""Planted-defect fixture for the security-audit probe.

DO NOT FIX the defects below — the defects ARE the fixture (see
tests/fixtures/workflow_probes/README.md). The security-audit
workflow must flag both, or the probe fails.

Not collected by pytest (filename avoids test_* / *_test patterns).
"""

# SEEDED BUG: hardcoded credential (CWE-798). The value is fake and
# deliberately marked as such; the workflow must still flag it.
ANTHROPIC_API_KEY = "sk-ant-api03-FAKE-workflow-probe-fixture-000000"  # pragma: allowlist secret


def calculate(expression: str) -> float:
    """Evaluate a user-supplied arithmetic expression.

    SEEDED BUG: dynamic evaluation of untrusted input (CWE-95).
    """
    return eval(expression)  # noqa: S307 — the planted defect


def fetch_report(name: str) -> str:
    """Read a report by name from the reports directory.

    SEEDED BUG: unvalidated path join — ``name`` can traverse out of
    the reports directory (CWE-22).
    """
    with open("reports/" + name, encoding="utf-8") as handle:
        return handle.read()
