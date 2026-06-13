"""Behavioral tests for PersistenceMixin (file_session_persistence).

Covers the file-backed session persistence mixin: directory creation,
load-or-create lifecycle (fresh / stale / corrupt / missing), explicit
load-by-id (current / archive / not-found), atomic write, and archiving
in both compression modes. No prior dedicated test file (66%).

The mixin expects a host exposing config/user_id/_state/_dirty; a tiny
_Host supplies exactly those, rooted in tmp_path so every path is
isolated and real (no mocked filesystem).
"""

import gzip
import json
import time

import pytest

from attune.memory.file_session_models import FileSessionConfig, SessionState
from attune.memory.file_session_persistence import PersistenceMixin


class _Host(PersistenceMixin):
    """Minimal host satisfying PersistenceMixin's attribute contract."""

    def __init__(self, config: FileSessionConfig, user_id: str):
        self.config = config
        self.user_id = user_id
        self._state = SessionState.new(user_id)
        self._dirty = True


@pytest.fixture
def host(tmp_path):
    """A PersistenceMixin host with directories created under tmp_path."""
    config = FileSessionConfig(base_dir=str(tmp_path))
    h = _Host(config, user_id="alice")
    h._ensure_directories()
    return h


def _write_current(host, state):
    """Write current.json directly (bypassing the timestamp-resetting save)."""
    current = host.config.sessions_dir / "current.json"
    current.write_text(json.dumps(state.to_dict(), default=str), encoding="utf-8")


# ===========================================================================
# _ensure_directories
# ===========================================================================


def test_ensure_directories_creates_all_paths(tmp_path):
    """All five storage directories are created."""
    config = FileSessionConfig(base_dir=str(tmp_path))
    _Host(config, "alice")._ensure_directories()
    assert config.sessions_dir.is_dir()
    assert config.patterns_dir.is_dir()
    assert (config.patterns_dir / "staged").is_dir()
    assert (config.patterns_dir / "promoted").is_dir()
    assert config.archive_dir.is_dir()


def test_ensure_directories_is_idempotent(host):
    """Re-running on existing directories does not raise."""
    host._ensure_directories()  # already created by fixture
    assert host.config.sessions_dir.is_dir()


# ===========================================================================
# _save_current / _atomic_write
# ===========================================================================


def test_save_current_writes_and_clears_dirty(host):
    """_save_current persists state and clears the dirty flag."""
    host._save_current()
    current = host.config.sessions_dir / "current.json"
    assert current.exists()
    assert host._dirty is False
    written = json.loads(current.read_text(encoding="utf-8"))
    assert written["session_id"] == host._state.session_id


def test_save_current_stamps_last_updated(host):
    """_save_current refreshes last_updated to ~now."""
    host._state.last_updated = 0.0
    before = time.time()
    host._save_current()
    assert host._state.last_updated >= before


def test_atomic_write_leaves_no_temp_file(host):
    """The temp file is renamed away — no .tmp residue remains."""
    target = host.config.sessions_dir / "thing.json"
    host._atomic_write(target, {"a": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    assert not target.with_suffix(".tmp").exists()


def test_atomic_write_overwrites_existing(host):
    """A second write replaces prior content (replace() on Windows too)."""
    target = host.config.sessions_dir / "thing.json"
    host._atomic_write(target, {"v": 1})
    host._atomic_write(target, {"v": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 2}


# ===========================================================================
# _load_current_or_create
# ===========================================================================


def test_load_or_create_makes_new_when_absent(host):
    """With no current.json, a fresh session is created and saved."""
    state = host._load_current_or_create()
    assert state.user_id == "alice"
    assert (host.config.sessions_dir / "current.json").exists()


def test_load_or_create_resumes_fresh_session(host):
    """A recent current.json is resumed (same session_id)."""
    host._save_current()
    original_id = host._state.session_id
    resumed = host._load_current_or_create()
    assert resumed.session_id == original_id


def test_load_or_create_archives_stale_and_creates_new(host):
    """A session older than the TTL is archived and replaced."""
    stale = SessionState.new("alice")
    stale.last_updated = time.time() - (host.config.session_ttl_hours + 5) * 3600
    _write_current(host, stale)

    new_state = host._load_current_or_create()
    assert new_state.session_id != stale.session_id
    # Stale session archived (compression on by default -> .gz).
    assert (host.config.archive_dir / f"{stale.session_id}.json.gz").exists()


def test_load_or_create_recovers_from_corrupt_file(host):
    """A corrupt current.json is tolerated; a new session is created."""
    (host.config.sessions_dir / "current.json").write_text("{broken", encoding="utf-8")
    state = host._load_current_or_create()
    assert state.user_id == "alice"


# ===========================================================================
# _load_session
# ===========================================================================


def test_load_session_from_current(host):
    """A session matching current.json is returned."""
    host._save_current()
    loaded = host._load_session(host._state.session_id)
    assert loaded.session_id == host._state.session_id


def test_load_session_from_archive(host):
    """A session present only in the (gz) archive is loaded."""
    state = SessionState.new("alice")
    host._archive_session(state)
    loaded = host._load_session(state.session_id)
    assert loaded.session_id == state.session_id


def test_load_session_not_found_raises(host):
    """An unknown session id raises ValueError."""
    with pytest.raises(ValueError, match="Session not found"):
        host._load_session("session_does_not_exist")


# ===========================================================================
# _archive_session
# ===========================================================================


def test_archive_session_compressed(host):
    """With compression on, a .gz archive is written and round-trips."""
    state = SessionState.new("alice")
    path = host._archive_session(state)
    assert path.suffix == ".gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        assert json.load(f)["session_id"] == state.session_id


def test_archive_session_uncompressed(host):
    """With compression off, a plain .json archive is written."""
    host.config.archive_compression = False
    state = SessionState.new("alice")
    path = host._archive_session(state)
    assert path.suffix == ".json"
    assert json.loads(path.read_text(encoding="utf-8"))["session_id"] == (state.session_id)
