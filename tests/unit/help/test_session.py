"""Tests for attune.help.session — progressive help depth session state."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.help import session
from attune.help.session import (
    _defaults,
    _load_session,
    _persist_session,
    get_state,
    reset_session,
    update_state,
)


@pytest.fixture(autouse=True)
def _isolate_session(tmp_path, monkeypatch):
    """Redirect session file to tmp_path and reset state."""
    session_file = tmp_path / "help_session.json"
    monkeypatch.setattr(session, "_SESSION_FILE", session_file)
    monkeypatch.setattr(session, "_session_state", _defaults())
    yield


# ── _defaults ────────────────────────────────────────────


class TestDefaults:
    """Tests for _defaults()."""

    def test_defaults_returns_correct_keys(self):
        """Verify returned dict has last_topic and depth_level."""
        result = _defaults()
        assert "last_topic" in result
        assert "depth_level" in result

    def test_defaults_initial_values(self):
        """Verify last_topic is None and depth_level is 0."""
        result = _defaults()
        assert result["last_topic"] is None
        assert result["depth_level"] == 0

    def test_defaults_returns_new_dict_each_call(self):
        """Each call returns an independent dict."""
        a = _defaults()
        b = _defaults()
        assert a == b
        assert a is not b


# ── get_state ────────────────────────────────────────────


class TestGetState:
    """Tests for get_state()."""

    def test_get_state_returns_defaults(self):
        """Fresh state matches defaults."""
        state = get_state()
        assert state == _defaults()

    def test_get_state_returns_copy(self):
        """Mutating the returned dict must not affect internal state."""
        state = get_state()
        state["depth_level"] = 99
        assert get_state()["depth_level"] == 0

    def test_get_state_reflects_update(self):
        """After update_state, get_state sees the new values."""
        update_state("security")
        state = get_state()
        assert state["last_topic"] == "security"
        assert state["depth_level"] == 0


# ── update_state ─────────────────────────────────────────


class TestUpdateState:
    """Tests for update_state()."""

    def test_update_state_new_topic_sets_depth_zero(self):
        """A new topic resets depth to 0."""
        depth = update_state("testing")
        assert depth == 0
        assert get_state()["last_topic"] == "testing"

    def test_update_state_same_topic_increments(self):
        """Revisiting the same topic increments depth."""
        update_state("testing")
        depth = update_state("testing")
        assert depth == 1

    def test_update_state_same_topic_increments_twice(self):
        """Two repeat visits reach depth 2."""
        update_state("testing")
        update_state("testing")
        depth = update_state("testing")
        assert depth == 2

    def test_update_state_depth_caps_at_two(self):
        """Depth never exceeds 2."""
        update_state("testing")
        update_state("testing")
        update_state("testing")
        depth = update_state("testing")
        assert depth == 2

    def test_update_state_different_topic_resets(self):
        """Switching topics resets depth to 0."""
        update_state("security")
        update_state("security")
        depth = update_state("testing")
        assert depth == 0

    def test_update_state_starting_level_override(self):
        """starting_level sets the initial depth for a new topic."""
        depth = update_state("security", starting_level=1)
        assert depth == 1

    def test_update_state_starting_level_on_topic_switch(self):
        """starting_level applies when switching topics."""
        update_state("testing")
        depth = update_state("security", starting_level=2)
        assert depth == 2

    def test_update_state_starting_level_ignored_same_topic(self):
        """starting_level is ignored when the topic is the same."""
        update_state("testing", starting_level=0)
        depth = update_state("testing", starting_level=0)
        assert depth == 1

    def test_update_state_persists(self, tmp_path):
        """update_state writes the session file."""
        update_state("security")
        session_file = tmp_path / "help_session.json"
        assert session_file.exists()
        data = json.loads(session_file.read_text(encoding="utf-8"))
        assert data["last_topic"] == "security"
        assert data["depth_level"] == 0

    def test_update_state_returns_int(self):
        """Return value is always an int."""
        depth = update_state("testing")
        assert isinstance(depth, int)


# ── reset_session ────────────────────────────────────────


class TestResetSession:
    """Tests for reset_session()."""

    def test_reset_session_clears_topic(self):
        """After reset, last_topic is None."""
        update_state("security")
        reset_session()
        assert get_state()["last_topic"] is None

    def test_reset_session_clears_depth(self):
        """After reset, depth_level is 0."""
        update_state("security")
        update_state("security")
        reset_session()
        assert get_state()["depth_level"] == 0

    def test_reset_session_persists(self, tmp_path):
        """reset_session writes defaults to disk."""
        update_state("security")
        reset_session()
        session_file = tmp_path / "help_session.json"
        assert session_file.exists()
        data = json.loads(session_file.read_text(encoding="utf-8"))
        assert data["last_topic"] is None
        assert data["depth_level"] == 0


# ── _load_session ────────────────────────────────────────


class TestLoadSession:
    """Tests for _load_session()."""

    def test_load_session_missing_file(self):
        """Returns defaults when session file does not exist."""
        result = _load_session()
        assert result == _defaults()

    def test_load_session_corrupt_json(self, tmp_path):
        """Returns defaults when file contains invalid JSON."""
        session_file = tmp_path / "help_session.json"
        session_file.write_text("not valid json {{{", encoding="utf-8")
        result = _load_session()
        assert result == _defaults()

    def test_load_session_expired_ttl(self, tmp_path):
        """Returns defaults when session is older than TTL."""
        session_file = tmp_path / "help_session.json"
        old_timestamp = time.time() - (5 * 3600)  # 5 hours ago
        data = {
            "last_topic": "security",
            "depth_level": 1,
            "timestamp": old_timestamp,
        }
        session_file.write_text(json.dumps(data), encoding="utf-8")
        result = _load_session()
        assert result == _defaults()

    def test_load_session_valid_file(self, tmp_path):
        """Loads state from a valid, non-expired file."""
        session_file = tmp_path / "help_session.json"
        data = {
            "last_topic": "security",
            "depth_level": 2,
            "timestamp": time.time(),
        }
        session_file.write_text(json.dumps(data), encoding="utf-8")
        result = _load_session()
        assert result["last_topic"] == "security"
        assert result["depth_level"] == 2

    def test_load_session_missing_timestamp(self, tmp_path):
        """Returns defaults when timestamp field is absent."""
        session_file = tmp_path / "help_session.json"
        data = {"last_topic": "security", "depth_level": 1}
        session_file.write_text(json.dumps(data), encoding="utf-8")
        result = _load_session()
        # timestamp defaults to 0 via .get("timestamp", 0),
        # so time.time() - 0 > TTL, returning defaults
        assert result == _defaults()

    def test_load_session_empty_file(self, tmp_path):
        """Returns defaults when file is empty."""
        session_file = tmp_path / "help_session.json"
        session_file.write_text("", encoding="utf-8")
        result = _load_session()
        assert result == _defaults()

    def test_load_session_just_inside_ttl(self, tmp_path):
        """Loads state when timestamp is just inside the TTL window."""
        session_file = tmp_path / "help_session.json"
        data = {
            "last_topic": "testing",
            "depth_level": 1,
            "timestamp": time.time() - (3 * 3600),  # 3 hours ago
        }
        session_file.write_text(json.dumps(data), encoding="utf-8")
        result = _load_session()
        assert result["last_topic"] == "testing"
        assert result["depth_level"] == 1


# ── _persist_session ─────────────────────────────────────


class TestPersistSession:
    """Tests for _persist_session()."""

    def test_persist_session_creates_dir(self, tmp_path):
        """Creates parent directory if it does not exist."""
        nested = tmp_path / "sub" / "help_session.json"
        with patch.object(session, "_SESSION_FILE", nested):
            _persist_session({"last_topic": "x", "depth_level": 0})
        assert nested.exists()

    def test_persist_session_writes_valid_json(self, tmp_path):
        """Written file contains valid JSON with expected keys."""
        _persist_session({"last_topic": "testing", "depth_level": 1})
        session_file = tmp_path / "help_session.json"
        data = json.loads(session_file.read_text(encoding="utf-8"))
        assert data["last_topic"] == "testing"
        assert data["depth_level"] == 1
        assert "timestamp" in data
        assert isinstance(data["timestamp"], float)

    def test_persist_session_atomic_write(self, tmp_path):
        """Tmp file should not remain after successful persist."""
        _persist_session({"last_topic": "x", "depth_level": 0})
        tmp_file = tmp_path / "help_session.json.tmp"
        assert not tmp_file.exists()

    def test_persist_session_handles_oserror(self, tmp_path):
        """OSError during write is silently caught."""
        bad_path = Path("/nonexistent_root_x/help_session.json")
        with patch.object(session, "_SESSION_FILE", bad_path):
            # Should not raise
            _persist_session({"last_topic": "x", "depth_level": 0})

    def test_persist_session_overwrites_existing(self, tmp_path):
        """A second persist overwrites the first."""
        _persist_session({"last_topic": "old", "depth_level": 0})
        _persist_session({"last_topic": "new", "depth_level": 2})
        session_file = tmp_path / "help_session.json"
        data = json.loads(session_file.read_text(encoding="utf-8"))
        assert data["last_topic"] == "new"
        assert data["depth_level"] == 2
