"""Shared fixtures for the ops dashboard tests.

The client-token gate (docs/specs/ops-mutating-endpoint-auth/) 403s
every mutating route whose request lacks an ``X-Attune-Client`` header
matching the per-process token. The route/page tests in this directory
predate the gate and exercise route *logic*, not the gate — so this
autouse fixture nulls the session token, which makes
``require_client_token`` accept the no-header requests they send
(``None == None``).

The gate's own behavior is covered in ``test_mutating_endpoint_auth.py``,
which **overrides** this fixture (same name) to re-establish a real
token so its 403/pass assertions are meaningful.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _bypass_client_token(monkeypatch):
    # require_client_token reads the module global at call time, so
    # nulling it here makes missing-header requests pass the gate.
    monkeypatch.setattr("attune.ops.security._SESSION_TOKEN", None)


@pytest.fixture(autouse=True)
def _no_memory_telemetry_pollution(monkeypatch):
    # The memory hooks' local tracker (plugin/hooks/_memory_telemetry.py)
    # is default-on and writes to the real ~/.attune JSONL. Any ops test
    # that reaches it through a production code path would append fixture
    # events to the user's live file (the documented HelpTracker trap).
    # Setting the module's opt-out env var makes log_memory_event no-op
    # for the duration of every test in this directory.
    monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "0")
