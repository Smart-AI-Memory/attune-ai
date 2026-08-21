"""Regression: the default long-term storage dir is home-anchored, not CWD.

A CWD-relative default (``./memdocs_storage``) silently splits long-term
memory across whatever directory the process was launched from, so patterns
stored from one project look *gone* when the same install is started from
another. These tests pin the home-anchored default and the backward-compat
fallback that keeps using an existing ``./memdocs_storage`` if one is present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.memory.storage_backend import MemDocsStorage, default_storage_dir
from attune.memory.unified import MemoryConfig


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Isolate HOME/CWD and clear any storage-dir env override."""
    home = tmp_path / "home"
    home.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Path.home() on Windows
    for var in ("ATTUNE_STORAGE_DIR", "EMPATHY_STORAGE_DIR", "STORAGE_DIR"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(work)
    return home, work


def test_default_is_home_anchored_when_no_legacy_dir(clean_env):
    home, _work = clean_env
    expected = (home / ".attune" / "memdocs_storage").resolve()
    assert Path(default_storage_dir()).resolve() == expected


def test_default_prefers_existing_cwd_legacy_dir(clean_env):
    _home, work = clean_env
    legacy = work / "memdocs_storage"
    legacy.mkdir()
    # An existing CWD store is kept (as an absolute path) so data is not stranded.
    got = Path(default_storage_dir())
    assert got.is_absolute()
    assert got.resolve() == legacy.resolve()


def test_default_is_always_absolute(clean_env):
    assert Path(default_storage_dir()).is_absolute()


def test_backend_none_resolves_and_creates_dir(clean_env):
    home, _work = clean_env
    storage = MemDocsStorage()  # storage_dir=None -> default
    assert storage.storage_dir.is_absolute()
    assert storage.storage_dir.exists()
    assert storage.storage_dir.resolve() == (home / ".attune" / "memdocs_storage").resolve()


def test_config_from_environment_is_home_anchored(clean_env):
    home, _work = clean_env
    config = MemoryConfig.from_environment()
    assert Path(config.storage_dir).is_absolute()
    assert Path(config.storage_dir).resolve() == (home / ".attune" / "memdocs_storage").resolve()


def test_env_override_wins(clean_env, monkeypatch, tmp_path):
    override = tmp_path / "explicit-store"
    monkeypatch.setenv("ATTUNE_STORAGE_DIR", str(override))
    config = MemoryConfig.from_environment()
    assert config.storage_dir == str(override)
