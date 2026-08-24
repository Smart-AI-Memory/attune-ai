"""Hermetic session-spend-ledger environment for script tests.

The workflow probe runner's ``_run_selected`` consults the
cross-launcher session spend ledger (docs/specs/session-spend-ledger/),
which defaults to ``~/.attune/telemetry/session_spend.jsonl``. Tests
here must never read or write the developer's real ledger.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _hermetic_session_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_SESSION_LEDGER_PATH", str(tmp_path / "session_spend.jsonl"))
    monkeypatch.delenv("ATTUNE_SESSION_SPEND_CAP_USD", raising=False)
    monkeypatch.delenv("ATTUNE_SESSION_LEDGER", raising=False)
    monkeypatch.delenv("ATTUNE_SEAT_SPEND_ESTIMATE_USD", raising=False)
