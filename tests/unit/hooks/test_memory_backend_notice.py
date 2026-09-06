"""Tests for memory_backend_notice.py SessionStart hook (redis-config-truth D5).

Mirrors the usage-consent notice tests:
- Emits the notice when no preference is recorded and the hook is enabled
- No-op once a preference exists (config or ATTUNE_MEMORY_BACKEND)
- No-op when disabled via ATTUNE_MEMORY_NOTICE=0
- No-op on the post-compact SessionStart source
- Anti-nag cap: stops after _MAX_SHOWS and bumps the count each emit
- Unreadable config counts as "no choice yet"
- Hook never raises (script-level catch-all)
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hook(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.delenv("ATTUNE_MEMORY_NOTICE", raising=False)
    monkeypatch.delenv("ATTUNE_MEMORY_BACKEND", raising=False)
    return _load_module("memory_backend_notice")


def _run(hook, monkeypatch, capsys, payload: dict | None = None) -> str:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload or {"source": "startup"})))
    assert hook.main() == 0
    return capsys.readouterr().out


def _record(tmp_path: Path, backend: str) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"memory": {"backend": backend}}))


def test_emits_notice_with_the_choice_and_the_action_for_claude(
    hook, monkeypatch, capsys, tmp_path
) -> None:
    out = _run(hook, monkeypatch, capsys)
    assert "Memory backend (one-time choice)" in out
    assert "enhanced memory features using Redis's open-source options" in out
    assert "attune memory use" in out and "ACTION FOR CLAUDE" in out
    assert (tmp_path / "telemetry" / ".memory_notice_count").read_text() == "1"


def test_silent_once_a_preference_is_recorded(hook, monkeypatch, capsys, tmp_path) -> None:
    _record(tmp_path, "file")
    assert _run(hook, monkeypatch, capsys) == ""


def test_env_override_counts_as_a_choice(hook, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ATTUNE_MEMORY_BACKEND", "redis")
    assert _run(hook, monkeypatch, capsys) == ""


def test_disabled_by_env(hook, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ATTUNE_MEMORY_NOTICE", "0")
    assert _run(hook, monkeypatch, capsys) == ""


def test_silent_on_post_compact_source(hook, monkeypatch, capsys) -> None:
    assert _run(hook, monkeypatch, capsys, {"source": "compact"}) == ""


def test_anti_nag_cap_stops_after_max_shows(hook, monkeypatch, capsys) -> None:
    for _ in range(hook._MAX_SHOWS):
        assert "Memory backend" in _run(hook, monkeypatch, capsys)
    assert _run(hook, monkeypatch, capsys) == ""


def test_unreadable_config_means_no_choice_yet(hook, monkeypatch, capsys, tmp_path) -> None:
    (tmp_path / "config.json").write_text("{not json")
    assert "Memory backend" in _run(hook, monkeypatch, capsys)


def test_non_json_stdin_is_treated_as_startup(hook, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert hook.main() == 0
    assert "Memory backend" in capsys.readouterr().out


def test_hook_never_raises(hook, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        hook, "_preference_recorded", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert hook.main() == 0
    assert "boom" in capsys.readouterr().err
