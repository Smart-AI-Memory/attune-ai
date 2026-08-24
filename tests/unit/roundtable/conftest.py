"""Hermetic session-spend-ledger environment for roundtable tests.

``default_invoke_seat`` / ``run_routine`` now consult the
cross-launcher session spend ledger (docs/specs/session-spend-ledger/),
which defaults to ``~/.attune/telemetry/session_spend.jsonl``. Unit
tests must never read the developer's real ledger (a locally
at-cap ledger would fail unrelated tests) nor write test entries
into it — every test in this directory gets a throwaway ledger path
and a clean cap environment.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _hermetic_session_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_SESSION_LEDGER_PATH", str(tmp_path / "session_spend.jsonl"))
    monkeypatch.delenv("ATTUNE_SESSION_SPEND_CAP_USD", raising=False)
    monkeypatch.delenv("ATTUNE_SESSION_LEDGER", raising=False)
    monkeypatch.delenv("ATTUNE_SEAT_SPEND_ESTIMATE_USD", raising=False)
