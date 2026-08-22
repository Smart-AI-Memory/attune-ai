"""Pytest fixtures for telemetry CLI tests.

Ensures Rich Console has adequate width during tests to prevent truncation.
"""

from typing import Any

import pytest


def serve_mget_from_get(client: Any) -> Any:
    """Let a ``Mock`` Redis client answer MGET from its per-key ``get``.

    The scan-then-fetch listings read their records with one MGET instead
    of a get() per key. These suites assert on the RECORDS, not on the
    transport, so replaying the same per-key values through mget keeps
    them focused; the round-trip count is pinned separately in
    ``test_redis_batch_access.py``.
    """
    client.mget.side_effect = lambda keys: [client.get(key) for key in keys]
    return client


@pytest.fixture(autouse=True)
def rich_console_width(monkeypatch):
    """Ensure Rich Console uses a fixed width during tests.

    Without this, Console() uses terminal width which can be very narrow
    during test runs, causing table content to be completely truncated.

    Rich respects the COLUMNS environment variable for terminal width.
    """
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setenv("LINES", "50")
