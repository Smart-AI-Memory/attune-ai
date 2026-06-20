"""Tests for usage_consent_notice.py SessionStart hook.

Covers:

- Emits the notice when no choice recorded and no env opt-out
- No-op when the user has already consented (opt-in OR opt-out)
- No-op when DO_NOT_TRACK / ATTUNE_USAGE_PING is set
- No-op when the hook is disabled via ATTUNE_CONSENT_NOTICE=0
- No-op on the post-compact SessionStart source
- Anti-nag cap: stops after _MAX_SHOWS and bumps the count each emit
- Missing/unreadable config counts as "no choice yet" (eligible)
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
    """Load the hook with config + count paths isolated to tmp_path and a
    clean env (no opt-out/disable signals)."""
    mod = _load_module("usage_consent_notice")
    monkeypatch.setattr(mod, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(mod, "COUNT_PATH", tmp_path / "telemetry" / ".consent_notice_count")
    for var in ("DO_NOT_TRACK", "ATTUNE_USAGE_PING", "ATTUNE_CONSENT_NOTICE"):
        monkeypatch.delenv(var, raising=False)
    return mod


def _write_config(mod, *, consented: bool) -> None:
    mod.CONFIG_PATH.write_text(
        json.dumps({"telemetry": {"usage_ping_consented": consented}}), encoding="utf-8"
    )


def _run(mod, monkeypatch, capsys, payload: dict | None = None) -> tuple[int, str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload or {})))
    rc = mod.main()
    return rc, capsys.readouterr().out


class TestEmits:
    def test_emits_when_no_choice_and_no_optout(self, hook, monkeypatch, capsys):
        # No config file at all = no choice yet.
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert "Anonymous usage sharing" in out
        assert "AskUserQuestion" in out
        assert "attune telemetry enable" in out

    def test_emits_when_consented_false(self, hook, monkeypatch, capsys):
        _write_config(hook, consented=False)
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert "Anonymous usage sharing" in out

    def test_emit_bumps_the_show_count(self, hook, monkeypatch, capsys):
        _run(hook, monkeypatch, capsys)
        assert hook.COUNT_PATH.read_text(encoding="utf-8").strip() == "1"


class TestNoOp:
    def test_silent_when_already_consented(self, hook, monkeypatch, capsys):
        _write_config(hook, consented=True)
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    @pytest.mark.parametrize("value", ["1", "true", "yes"])
    def test_silent_on_do_not_track(self, hook, monkeypatch, capsys, value):
        monkeypatch.setenv("DO_NOT_TRACK", value)
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    def test_silent_when_usage_ping_env_set(self, hook, monkeypatch, capsys):
        # Any explicit value (even "0") is a choice — don't ask over it.
        monkeypatch.setenv("ATTUNE_USAGE_PING", "0")
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    @pytest.mark.parametrize("value", ["0", "false", "no"])
    def test_silent_when_hook_disabled(self, hook, monkeypatch, capsys, value):
        monkeypatch.setenv("ATTUNE_CONSENT_NOTICE", value)
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    def test_silent_on_compact_source(self, hook, monkeypatch, capsys):
        rc, out = _run(hook, monkeypatch, capsys, {"source": "compact"})
        assert rc == 0
        assert out == ""

    def test_do_not_track_falsey_still_asks(self, hook, monkeypatch, capsys):
        # DO_NOT_TRACK="0" is not an opt-out — the notice should still show.
        monkeypatch.setenv("DO_NOT_TRACK", "0")
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert "Anonymous usage sharing" in out


class TestAntiNagCap:
    def test_silent_once_cap_reached(self, hook, monkeypatch, capsys):
        hook.COUNT_PATH.parent.mkdir(parents=True, exist_ok=True)
        hook.COUNT_PATH.write_text(str(hook._MAX_SHOWS), encoding="utf-8")
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    def test_shows_exactly_max_times(self, hook, monkeypatch, capsys):
        shows = 0
        for _ in range(hook._MAX_SHOWS + 2):
            _, out = _run(hook, monkeypatch, capsys)
            if "Anonymous usage sharing" in out:
                shows += 1
        assert shows == hook._MAX_SHOWS


class TestRobustness:
    def test_unreadable_config_is_eligible(self, hook, monkeypatch, capsys):
        hook.CONFIG_PATH.write_text("{ not valid json", encoding="utf-8")
        rc, out = _run(hook, monkeypatch, capsys)
        assert rc == 0
        assert "Anonymous usage sharing" in out

    def test_never_raises_on_bad_stdin(self, hook, monkeypatch, capsys):
        monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
        rc = hook.main()
        assert rc == 0
