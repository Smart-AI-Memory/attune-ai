"""Consent-surface guard — the privacy promises, pinned as tests.

The repo's consent stance lives in prose today: README/SECURITY.md
promise explicit opt-in for the phone-home ping; ratified decision R2
says defaulting it ON would contradict all three; and the memory-events
producer's docstring promises "the opt-in usage ping reads
``usage*.jsonl`` and never this file" — a claim the ``memory_feedback``
events (which carry ``cwd`` paths) now depend on. Any of these could be
flipped by a one-line diff with nothing going red.

Policy pinned here:

1. **Phone-home defaults OFF** — ``TelemetryConfig.usage_ping`` (and
   ``usage_ping_consented``) default ``False``; ``is_enabled`` on the
   defaults is ``False``. Transmitting requires an explicit opt-in.
2. **DO_NOT_TRACK always wins** — over a config opt-in AND over the
   ``ATTUNE_USAGE_PING`` env override; and BOTH memory-events writers
   (the src copy and the plugin-hook copy) honor it for the local log.
3. **The ping never reads ``memory_events.jsonl``** — its record
   source is the ``usage*.jsonl`` family only, verified functionally
   against a directory containing both.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from attune.config.sections.telemetry import TelemetryConfig
from attune.telemetry import usage_ping
from attune.telemetry.memory_events import log_memory_event as src_log_memory_event

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_hook_module(name: str):
    """Load a plugin/hooks script (standalone, not importable from src)."""
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. Phone-home defaults OFF
# ---------------------------------------------------------------------------


def test_usage_ping_defaults_off():
    """A fresh config must not opt in to the phone-home ping.

    If this fails, a diff flipped the default — that contradicts
    README, SECURITY.md, and decision R2 (explicit consent). Revert the
    default; opting in is the user's move, never the package's.
    """
    cfg = TelemetryConfig()
    assert cfg.usage_ping is False
    assert cfg.usage_ping_consented is False


def test_default_config_resolves_disabled():
    """End to end: defaults + clean env → pinging disabled."""
    assert usage_ping.is_enabled(TelemetryConfig().usage_ping, env={}) is False


# ---------------------------------------------------------------------------
# 2. DO_NOT_TRACK always wins
# ---------------------------------------------------------------------------


def test_do_not_track_beats_config_opt_in():
    assert usage_ping.is_enabled(True, env={"DO_NOT_TRACK": "1"}) is False


def test_do_not_track_beats_env_override():
    """DNT outranks even an explicit ATTUNE_USAGE_PING=1 — the opt-out
    is the highest-precedence signal on the whole surface."""
    env = {"DO_NOT_TRACK": "1", "ATTUNE_USAGE_PING": "1"}
    assert usage_ping.is_enabled(True, env=env) is False


def _memory_writers():
    """Both copies of the memory-events writer (src + plugin hook)."""
    hook_mod = _load_hook_module("_memory_telemetry")
    return [
        pytest.param(src_log_memory_event, id="src-copy"),
        pytest.param(hook_mod.log_memory_event, id="hook-copy"),
    ]


@pytest.mark.parametrize("writer", _memory_writers())
def test_memory_writers_honor_do_not_track(writer, tmp_path, monkeypatch):
    """DO_NOT_TRACK silences even the LOCAL memory-events log, in both
    writer copies — including when ATTUNE_MEMORY_TELEMETRY=1 tries to
    force it on."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "1")
    monkeypatch.setenv("DO_NOT_TRACK", "1")

    writer("memory_feedback", verdict="rejected", count=1)

    events_file = tmp_path / "telemetry" / "memory_events.jsonl"
    assert not events_file.exists(), (
        "a memory-events writer recorded despite DO_NOT_TRACK=1 — the "
        "opt-out must silence the local log too (both copies share the "
        "consent gate; divergence in a privacy opt-out is a bug class)."
    )


# ---------------------------------------------------------------------------
# 3. The ping never reads memory_events.jsonl
# ---------------------------------------------------------------------------


def test_ping_record_source_excludes_memory_events(tmp_path):
    """The promise #1279/#1292 stand on: memory events (which carry cwd
    paths and session findings context) never enter the phone-home
    payload source. Verified functionally — a telemetry dir holding
    usage, rotated-usage, and memory-events files yields ONLY the usage
    family from ``records_since``.
    """
    (tmp_path / "usage.jsonl").write_text(
        json.dumps({"ts": "2026-07-08T01:00:00Z", "workflow": "w1"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "usage.2026-01-01.jsonl").write_text(
        json.dumps({"ts": "2026-07-08T02:00:00Z", "workflow": "w2"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "memory_events.jsonl").write_text(
        json.dumps(
            {
                "ts": "2026-07-08T03:00:00Z",
                "event": "memory_feedback",
                "cwd": "/SHOULD-NEVER-TRANSMIT",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = usage_ping.records_since(tmp_path, cursor_ts="")

    assert len(records) == 2, (
        f"expected only the 2 usage-family records, got {len(records)} — "
        f"the ping's record source widened beyond usage*.jsonl."
    )
    blob = json.dumps(records)
    assert "SHOULD-NEVER-TRANSMIT" not in blob and "memory_feedback" not in blob, (
        "memory_events.jsonl content reached the ping's record source — "
        "this breaks the local-only promise the memory telemetry stream "
        "(#1279/#1292) is built on."
    )
