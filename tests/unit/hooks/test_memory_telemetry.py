"""Tests for the memory-hook event log (``_memory_telemetry``).

Covers the helper's contract (JSONL shape, env gates, never-raises)
and the integration points: a session_recall emission, a jit_recall
fire, a lesson_recall fire, and a session_stash run each append one
measurable event to ``<ATTUNE_HOME>/telemetry/memory_events.jsonl``.

The hooks are standalone scripts; they're loaded via importlib (the
``test_session_memory_hooks.py`` pattern).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
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
        del sys.modules[name]  # fresh load so module-level state is clean
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def telem_mod():
    return _load_module("_memory_telemetry")


def _events(tmp_path: Path) -> list[dict]:
    """Parse the events file written under the test's ATTUNE_HOME."""
    path = tmp_path / ".attune" / "telemetry" / "memory_events.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# ==========================================================================
# Helper contract
# ==========================================================================


def test_log_writes_one_json_line_with_schema_fields(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    telem_mod.log_memory_event("jit_recall", session_id="sess-1", tool="Bash", injected_chars=400)
    events = _events(tmp_path)
    assert len(events) == 1
    e = events[0]
    assert e["v"] == "1.0"
    assert e["event"] == "jit_recall"
    assert e["session_id"] == "sess-1"
    assert e["tool"] == "Bash"
    assert e["injected_chars"] == 400
    assert e["est_tokens"] == 100  # 4 chars/token
    assert e["ts"].endswith("Z")


def test_log_reserved_keys_cannot_be_clobbered(telem_mod, tmp_path, monkeypatch):
    """Regression: library review checkpoint-1 R2 hit — **fields must not
    overwrite the reserved v/ts/event/session_id schema keys."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    telem_mod.log_memory_event(
        "jit_recall", session_id="real", v="FORGED", ts="1970-01-01T00:00:00Z", tool="Bash"
    )
    (e,) = _events(tmp_path)
    assert e["v"] == "1.0"
    assert e["ts"] != "1970-01-01T00:00:00Z"
    assert e["event"] == "jit_recall"
    assert e["session_id"] == "real"
    assert e["tool"] == "Bash"


def test_log_appends_multiple_events(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    telem_mod.log_memory_event("session_recall", entries=3)
    telem_mod.log_memory_event("session_stash", written=2)
    assert [e["event"] for e in _events(tmp_path)] == ["session_recall", "session_stash"]


def test_log_disabled_via_env(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "0")
    telem_mod.log_memory_event("jit_recall")
    assert _events(tmp_path) == []


def test_log_honors_do_not_track(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    telem_mod.log_memory_event("jit_recall")
    assert _events(tmp_path) == []


def test_log_falsey_do_not_track_still_records(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("DO_NOT_TRACK", "0")
    telem_mod.log_memory_event("jit_recall")
    assert len(_events(tmp_path)) == 1


def test_log_never_raises_on_unwritable_dir(telem_mod, tmp_path, monkeypatch):
    blocker = tmp_path / "blocked"
    blocker.write_text("a file where the dir should be", encoding="utf-8")
    monkeypatch.setenv("ATTUNE_HOME", str(blocker))  # mkdir under a file fails
    telem_mod.log_memory_event("jit_recall")  # must not raise


def test_log_serializes_non_json_values_via_default_str(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    telem_mod.log_memory_event("session_stash", where=Path("/x"))
    # str(Path("/x")) is "\\x" on Windows — compare via the same conversion.
    assert _events(tmp_path)[0]["where"] == str(Path("/x"))


def test_log_truncates_long_session_ids(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    telem_mod.log_memory_event("jit_recall", session_id="x" * 200)
    assert len(_events(tmp_path)[0]["session_id"]) == 64


def test_rotate_if_huge_moves_live_file_aside(telem_mod, tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setattr(telem_mod, "_MAX_BYTES", 10)
    telem_mod.log_memory_event("jit_recall", tool="Bash")  # >10 bytes
    telem_mod.log_memory_event("jit_recall", tool="Edit")  # triggers rotation
    tdir = tmp_path / ".attune" / "telemetry"
    rotated = list(tdir.glob("memory_events.*.jsonl"))
    assert len(rotated) == 1
    live = _events(tmp_path)
    assert len(live) == 1 and live[0]["tool"] == "Edit"


# ==========================================================================
# Hook integration — each hook appends a measurable event
# ==========================================================================


def _run(mod, monkeypatch, payload: dict) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return mod.main()


def test_session_recall_emission_logs_event(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    mod = _load_module("session_recall")
    entries = [{"id": "f-1", "text": "decided the widget uses tables", "topics": ["type:decision"]}]

    import attune.memory.session_stash as stash_pkg

    monkeypatch.setattr(stash_pkg, "recent_entries", lambda top_k, cwd: entries)
    monkeypatch.setattr(stash_pkg, "backend_status", lambda: {})
    rc = _run(mod, monkeypatch, {"source": "startup", "session_id": "sess-r", "cwd": str(tmp_path)})
    assert rc == 0
    out = capsys.readouterr().out
    assert "Recalled memories" in out

    events = _events(tmp_path)
    assert len(events) == 1
    e = events[0]
    assert e["event"] == "session_recall"
    assert e["session_id"] == "sess-r"
    assert e["entries"] == 1
    assert e["finding_ids"] == ["f-1"]
    assert isinstance(e["surfacing_id"], str) and len(e["surfacing_id"]) == 12
    assert e["injected_chars"] > 0 and e["est_tokens"] > 0


def test_jit_recall_fire_logs_tool_and_rules(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    _load_module("_state")
    mod = _load_module("jit_recall")
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "AskUserQuestion",
        "session_id": "sess-j",
        "tool_input": {"questions": []},
    }
    rc = _run(mod, monkeypatch, payload)
    assert rc == 0
    assert "additionalContext" in capsys.readouterr().out

    events = _events(tmp_path)
    assert len(events) == 1
    e = events[0]
    assert e["event"] == "jit_recall"
    assert e["session_id"] == "sess-j"
    assert e["tool"] == "AskUserQuestion"
    assert e["rules"] and all(isinstance(r, str) for r in e["rules"])
    # triggers is parallel to rules: which gate fired each rule.
    assert len(e["triggers"]) == len(e["rules"])
    assert all(t in {"tool", "substring", "regex", "substring+regex"} for t in e["triggers"])
    assert isinstance(e["surfacing_id"], str) and len(e["surfacing_id"]) == 12
    assert e["injected_chars"] > 0


def test_jit_recall_no_match_logs_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    _load_module("_state")
    mod = _load_module("jit_recall")
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "NoSuchTool",
        "session_id": "sess-j2",
        "tool_input": {},
    }
    assert _run(mod, monkeypatch, payload) == 0
    assert _events(tmp_path) == []


def test_lesson_recall_fire_logs_lessons_and_scores(tmp_path, monkeypatch, capsys):
    """Prompt-time recall must leave a surfacing record — before
    2026-07-14 it logged NOTHING (the memory-recall-eval gap: no
    record, no noise denominator)."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    lessons = tmp_path / "lessons.md"
    lessons.write_text(
        "## Lessons Learned\n\n"
        "- **Squash merge tagging requires the merge SHA**: after a\n"
        "  squash merge always tag the squash merge commit SHA, never\n"
        "  the feature branch tip.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ATTUNE_LESSONS_FILE", str(lessons))
    _load_module("_state")
    mod = _load_module("lesson_recall")
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "how do I tag the release after the squash merge lands",
        "session_id": "sess-l",
        "cwd": str(tmp_path),
    }
    rc = _run(mod, monkeypatch, payload)
    assert rc == 0
    assert "additionalContext" in capsys.readouterr().out

    events = _events(tmp_path)
    assert len(events) == 1
    e = events[0]
    assert e["event"] == "lesson_recall"
    assert e["session_id"] == "sess-l"
    assert e["lessons"] and all(isinstance(x, str) for x in e["lessons"])
    # scores is parallel to lessons, every score at/above the floor.
    assert len(e["scores"]) == len(e["lessons"])
    assert all(s >= 8.0 for s in e["scores"])
    assert isinstance(e["surfacing_id"], str) and len(e["surfacing_id"]) == 12
    assert e["injected_chars"] > 0 and e["est_tokens"] > 0


def test_lesson_recall_no_match_logs_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    lessons = tmp_path / "lessons.md"
    lessons.write_text(
        "## Lessons Learned\n\n- **Squash merge tagging**: tag the merge SHA.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ATTUNE_LESSONS_FILE", str(lessons))
    _load_module("_state")
    mod = _load_module("lesson_recall")
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "please recolor the dashboard purple with sparkles",
        "session_id": "sess-l2",
        "cwd": str(tmp_path),
    }
    assert _run(mod, monkeypatch, payload) == 0
    assert capsys.readouterr().out == ""
    assert _events(tmp_path) == []


def test_session_stash_logs_counts_and_extractor(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / ".attune"))
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    _load_module("_state")
    mod = _load_module("session_stash")

    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "message": {
                    "role": "assistant",
                    "content": "we decided to use the file backend for the stash layer",
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "estimate_utilization", lambda _p: 0.9)
    monkeypatch.setattr(mod, "_extract_via_ollama", lambda _t: None)  # heuristic path
    monkeypatch.setattr(mod, "_stash_findings", lambda findings, **k: len(findings))
    payload = {
        "session_id": "sess-s",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
    }
    assert _run(mod, monkeypatch, payload) == 0

    events = _events(tmp_path)
    assert len(events) == 1
    e = events[0]
    assert e["event"] == "session_stash"
    assert e["session_id"] == "sess-s"
    assert e["extractor"] == "heuristic"
    assert e["findings"] >= 1
    assert e["written"] == e["findings"]
    assert e["injected_chars"] > 0  # additionalContext summary was emitted
