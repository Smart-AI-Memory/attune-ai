"""Pytest fixtures for telemetry CLI tests.

Ensures Rich Console has adequate width during tests to prevent truncation.
"""

import pytest


@pytest.fixture(autouse=True)
def rich_console_width(monkeypatch):
    """Ensure Rich Console uses a fixed width during tests.

    Without this, Console() uses terminal width which can be very narrow
    during test runs, causing table content to be completely truncated.

    Rich respects the COLUMNS environment variable for terminal width.
    """
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setenv("LINES", "50")
