"""Behavioral tests for ShortTermMemoryMixin.

The mixin expects a host class to supply user_id, short_term_memory,
credentials, collaboration_state, current_empathy_level, logger, and
_session_id. A minimal _Host provides those, and a fake backend records
calls so the mixin's staging, signalling, and state-persistence logic can
be exercised in isolation. Every public method has a "configured" path
that delegates to the backend and a "not configured" path that raises (or
returns None), and both are covered here.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from attune.core_modules.short_term_memory import ShortTermMemoryMixin


class _FakeBackend:
    """Records delegated calls and returns canned values."""

    def __init__(self, *, retrieve_value=None):
        self.calls: list = []
        self._retrieve_value = retrieve_value

    def stage_pattern(self, pattern, credentials):
        self.calls.append(("stage_pattern", pattern, credentials))
        return True

    def list_staged_patterns(self, credentials):
        self.calls.append(("list_staged_patterns", credentials))
        return ["pat_1", "pat_2"]

    def send_signal(self, *, signal_type, data, credentials, target_agent):
        self.calls.append(("send_signal", signal_type, data, target_agent))
        return True

    def receive_signals(self, credentials, signal_type=None):
        self.calls.append(("receive_signals", signal_type))
        return [{"sender": "a", "type": signal_type, "data": {}}]

    def stash(self, key, value, credentials):
        self.calls.append(("stash", key, value))
        return True

    def retrieve(self, key, credentials):
        self.calls.append(("retrieve", key))
        return self._retrieve_value

    def get_stats(self):
        self.calls.append(("get_stats",))
        return {"keys": 3, "mode": "redis"}


def _make_collab_state():
    return SimpleNamespace(
        trust_level=0.7,
        successful_interventions=3,
        failed_interventions=1,
        total_interactions=4,
        session_start=datetime(2026, 1, 1, 12, 0, 0),
        trust_trajectory=[0.5, 0.6, 0.7],
    )


class _Host(ShortTermMemoryMixin):
    """Minimal host satisfying the mixin's expected attributes."""

    def __init__(self, backend=None):
        self.user_id = "dev_123"
        self.short_term_memory = backend
        self.credentials = SimpleNamespace(agent_id="dev_123")
        self.collaboration_state = _make_collab_state()
        self.current_empathy_level = 2
        self.logger = MagicMock()
        self._session_id = None


# ---------------------------------------------------------------------------
# has_short_term_memory / session_id
# ---------------------------------------------------------------------------


class TestPresenceAndSession:
    def test_has_short_term_memory_true_when_configured(self):
        assert _Host(_FakeBackend()).has_short_term_memory() is True

    def test_has_short_term_memory_false_when_none(self):
        assert _Host(None).has_short_term_memory() is False

    def test_session_id_generated_and_prefixed_with_user(self):
        host = _Host(_FakeBackend())
        sid = host.session_id
        assert sid.startswith("dev_123_")
        assert len(sid.split("_")[-1]) == 8

    def test_session_id_is_stable_across_calls(self):
        host = _Host(_FakeBackend())
        assert host.session_id == host.session_id

    def test_session_id_uses_preset_value(self):
        host = _Host(_FakeBackend())
        host._session_id = "preset_abc"
        assert host.session_id == "preset_abc"


# ---------------------------------------------------------------------------
# stage_pattern / get_staged_patterns
# ---------------------------------------------------------------------------


class TestPatternStaging:
    def test_stage_pattern_delegates_to_backend(self):
        backend = _FakeBackend()
        host = _Host(backend)
        pattern = SimpleNamespace(pattern_id="pat_1")

        assert host.stage_pattern(pattern) is True
        assert backend.calls[0] == ("stage_pattern", pattern, host.credentials)

    def test_stage_pattern_raises_without_backend(self):
        with pytest.raises(RuntimeError, match="No short-term memory configured"):
            _Host(None).stage_pattern(SimpleNamespace())

    def test_get_staged_patterns_returns_backend_list(self):
        host = _Host(_FakeBackend())
        assert host.get_staged_patterns() == ["pat_1", "pat_2"]

    def test_get_staged_patterns_raises_without_backend(self):
        with pytest.raises(RuntimeError, match="No short-term memory configured"):
            _Host(None).get_staged_patterns()


# ---------------------------------------------------------------------------
# send_signal / receive_signals
# ---------------------------------------------------------------------------


class TestSignals:
    def test_send_signal_passes_through_arguments(self):
        backend = _FakeBackend()
        host = _Host(backend)

        assert host.send_signal("task_complete", {"n": 1}, target_agent="lead") is True
        assert backend.calls[0] == ("send_signal", "task_complete", {"n": 1}, "lead")

    def test_send_signal_defaults_target_to_none(self):
        backend = _FakeBackend()
        _Host(backend).send_signal("status", {"phase": "x"})
        assert backend.calls[0][-1] is None

    def test_send_signal_raises_without_backend(self):
        with pytest.raises(RuntimeError, match="coordination signals"):
            _Host(None).send_signal("x", {})

    def test_receive_signals_filters_by_type(self):
        backend = _FakeBackend()
        host = _Host(backend)

        result = host.receive_signals("analysis_complete")
        assert result[0]["type"] == "analysis_complete"
        assert backend.calls[0] == ("receive_signals", "analysis_complete")

    def test_receive_signals_default_no_filter(self):
        backend = _FakeBackend()
        _Host(backend).receive_signals()
        assert backend.calls[0] == ("receive_signals", None)

    def test_receive_signals_raises_without_backend(self):
        with pytest.raises(RuntimeError, match="coordination signals"):
            _Host(None).receive_signals()


# ---------------------------------------------------------------------------
# persist / restore collaboration state
# ---------------------------------------------------------------------------


class TestCollaborationStatePersistence:
    def test_persist_serializes_state_and_stashes(self):
        backend = _FakeBackend()
        host = _Host(backend)

        assert host.persist_collaboration_state() is True
        op, key, value = backend.calls[0]
        assert op == "stash"
        assert key == f"collaboration_state_{host.session_id}"
        assert value["trust_level"] == 0.7
        assert value["current_empathy_level"] == 2
        assert value["session_start"] == "2026-01-01T12:00:00"

    def test_persist_caps_trajectory_at_last_100(self):
        backend = _FakeBackend()
        host = _Host(backend)
        host.collaboration_state.trust_trajectory = list(range(250))

        host.persist_collaboration_state()
        stashed_value = backend.calls[0][2]
        assert stashed_value["trust_trajectory"] == list(range(150, 250))

    def test_persist_raises_without_backend(self):
        with pytest.raises(RuntimeError, match="state persistence"):
            _Host(None).persist_collaboration_state()

    def test_restore_populates_state_from_stored_data(self):
        stored = {
            "trust_level": 0.9,
            "successful_interventions": 10,
            "failed_interventions": 2,
            "total_interactions": 12,
            "current_empathy_level": 5,
            "trust_trajectory": [0.8, 0.9],
        }
        host = _Host(_FakeBackend(retrieve_value=stored))

        assert host.restore_collaboration_state("sess_x") is True
        assert host.collaboration_state.trust_level == 0.9
        assert host.collaboration_state.total_interactions == 12
        assert host.current_empathy_level == 5
        assert host.collaboration_state.trust_trajectory == [0.8, 0.9]
        host.logger.info.assert_called_once()

    def test_restore_uses_current_session_when_id_omitted(self):
        backend = _FakeBackend(retrieve_value={})
        host = _Host(backend)

        host.restore_collaboration_state()
        op, key = backend.calls[0]
        assert op == "retrieve"
        assert key == f"collaboration_state_{host.session_id}"

    def test_restore_applies_defaults_for_missing_fields(self):
        host = _Host(_FakeBackend(retrieve_value={}))

        assert host.restore_collaboration_state("s") is True
        assert host.collaboration_state.trust_level == 0.5
        assert host.current_empathy_level == 1
        assert host.collaboration_state.trust_trajectory == []

    def test_restore_returns_false_when_no_state_found(self):
        host = _Host(_FakeBackend(retrieve_value=None))
        assert host.restore_collaboration_state("missing") is False
        host.logger.info.assert_not_called()

    def test_restore_raises_without_backend(self):
        with pytest.raises(RuntimeError, match="state persistence"):
            _Host(None).restore_collaboration_state()


# ---------------------------------------------------------------------------
# get_memory_stats
# ---------------------------------------------------------------------------


class TestMemoryStats:
    def test_get_memory_stats_returns_backend_stats(self):
        host = _Host(_FakeBackend())
        assert host.get_memory_stats() == {"keys": 3, "mode": "redis"}

    def test_get_memory_stats_none_when_not_configured(self):
        assert _Host(None).get_memory_stats() is None
