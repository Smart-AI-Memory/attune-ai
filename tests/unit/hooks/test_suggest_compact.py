"""Behavioral tests for suggest_compact.py hook script.

Covers state persistence, the suggestion threshold/interval logic, the
recommendation builder, the ``main`` tracking entry point, the
``reset_on_compaction`` PreCompact entry point, and the ``__main__`` demo
loop.

State lives at ``~/.attune/compaction_state.json``; an autouse fixture
points ``HOME`` at a per-test tmp dir so reads/writes are fully isolated
and the real ``get_compaction_state_file`` path-building runs unmocked.
"""

from __future__ import annotations

import importlib
import json
import runpy
from pathlib import Path

import pytest

# The package __init__ rebinds the name ``suggest_compact`` to the module's
# ``main`` function, so ``from ... import suggest_compact`` (and ``import ...
# as``) would resolve to that function. import_module returns the real module.
hook = importlib.import_module("attune.hooks.scripts.suggest_compact")

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "hooks"
    / "scripts"
    / "suggest_compact.py"
)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point Path.home() at a tmp dir and clear env threshold overrides.

    Patching ``Path.home`` directly (rather than ``setenv("HOME", ...)``)
    is cross-platform: on Windows ``Path.home()`` resolves via
    ``%USERPROFILE%``, not ``$HOME``, so a HOME override there is a no-op
    and the hook would read/write the real shared state file — leaking
    state across tests/xdist workers.
    """
    monkeypatch.setattr(hook.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("COMPACT_THRESHOLD", raising=False)
    monkeypatch.delenv("COMPACT_INTERVAL", raising=False)
    return tmp_path


# --------------------------------------------------------------------------- #
# state file path + persistence
# --------------------------------------------------------------------------- #


def test_state_file_path_under_home(isolated_home):
    path = hook.get_compaction_state_file()

    assert path == isolated_home / ".attune" / "compaction_state.json"


def test_load_returns_default_when_file_missing():
    state = hook.load_compaction_state()

    assert state == {
        "tool_call_count": 0,
        "last_suggestion": None,
        "last_compaction": None,
        "suggestion_count": 0,
    }


def test_load_returns_existing_state(isolated_home):
    state_file = hook.get_compaction_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"tool_call_count": 17}))

    assert hook.load_compaction_state() == {"tool_call_count": 17}


def test_load_corrupt_file_falls_back_to_default(isolated_home):
    state_file = hook.get_compaction_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("{not valid json")

    state = hook.load_compaction_state()

    assert state["tool_call_count"] == 0
    assert state["suggestion_count"] == 0


def test_save_creates_parent_and_writes(isolated_home):
    hook.save_compaction_state({"tool_call_count": 5, "marker": "x"})

    state_file = hook.get_compaction_state_file()
    assert state_file.exists()
    assert json.loads(state_file.read_text()) == {"tool_call_count": 5, "marker": "x"}


def test_save_then_load_roundtrips():
    original = {
        "tool_call_count": 42,
        "last_suggestion": "2026-01-01T00:00:00",
        "last_compaction": None,
        "suggestion_count": 2,
    }
    hook.save_compaction_state(original)

    assert hook.load_compaction_state() == original


# --------------------------------------------------------------------------- #
# should_suggest_compaction
# --------------------------------------------------------------------------- #


def test_suggest_exactly_at_threshold():
    should, reason = hook.should_suggest_compaction({"tool_call_count": 50})

    assert should is True
    assert "50 tool calls" in reason


def test_suggest_periodic_after_threshold():
    # 50 + 25 == 75 hits the reminder interval
    should, reason = hook.should_suggest_compaction({"tool_call_count": 75})

    assert should is True
    assert "75 tool calls" in reason


def test_no_suggest_below_threshold():
    should, reason = hook.should_suggest_compaction({"tool_call_count": 49})

    assert should is False
    assert reason == ""


def test_no_suggest_off_interval():
    # 51 is past threshold but not on a 25-call boundary
    should, reason = hook.should_suggest_compaction({"tool_call_count": 51})

    assert should is False
    assert reason == ""


def test_custom_threshold_and_interval():
    should, reason = hook.should_suggest_compaction(
        {"tool_call_count": 10}, threshold=10, interval=5
    )
    assert should is True

    should2, _ = hook.should_suggest_compaction({"tool_call_count": 15}, threshold=10, interval=5)
    assert should2 is True  # 10 + 5


# --------------------------------------------------------------------------- #
# get_compaction_recommendations
# --------------------------------------------------------------------------- #


def test_recommendations_for_completed_phases():
    recs = hook.get_compaction_recommendations({"completed_phases": ["design", "build"]})

    assert any("design, build" in r for r in recs)


def test_recommendations_for_exploration_and_research():
    recs = hook.get_compaction_recommendations(
        {"exploration_complete": True, "research_complete": True}
    )

    joined = " ".join(recs)
    assert "Exploration context" in joined
    assert "Research context" in joined


def test_recommendations_default_when_no_signals():
    recs = hook.get_compaction_recommendations({})

    assert len(recs) == 3
    assert any("Summarize completed work" in r for r in recs)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def test_main_increments_count_and_no_suggestion_early():
    result = hook.main(current_phase="implementation")

    assert result["tool_call_count"] == 1
    assert result["suggest_compaction"] is False
    assert result["messages"] == []
    # state persisted
    assert hook.load_compaction_state()["tool_call_count"] == 1


def test_main_persists_across_calls():
    hook.main()
    second = hook.main()

    assert second["tool_call_count"] == 2


def test_main_suggests_at_threshold_and_records(monkeypatch):
    # Seed state so the next increment lands exactly on the threshold.
    hook.save_compaction_state({"tool_call_count": 49})

    result = hook.main(completed_phases=["explore"])

    assert result["tool_call_count"] == 50
    assert result["suggest_compaction"] is True
    assert "50 tool calls" in result["reason"]
    assert result["recommendations"]
    # messages include the headline plus one per recommendation
    assert result["messages"][0].startswith("[SuggestCompact]")
    assert len(result["messages"]) == 1 + len(result["recommendations"])

    persisted = hook.load_compaction_state()
    assert persisted["suggestion_count"] == 1
    assert persisted["last_suggestion"] is not None


def test_main_respects_env_threshold(monkeypatch):
    monkeypatch.setenv("COMPACT_THRESHOLD", "1")

    result = hook.main()

    assert result["tool_call_count"] == 1
    assert result["suggest_compaction"] is True


# --------------------------------------------------------------------------- #
# reset_on_compaction
# --------------------------------------------------------------------------- #


def test_reset_on_compaction_zeroes_count():
    hook.save_compaction_state({"tool_call_count": 30, "suggestion_count": 4})

    result = hook.reset_on_compaction()

    assert result["reset"] is True
    assert "timestamp" in result
    persisted = hook.load_compaction_state()
    assert persisted["tool_call_count"] == 0
    assert persisted["last_compaction"] is not None


# --------------------------------------------------------------------------- #
# __main__ demo loop
# --------------------------------------------------------------------------- #


def test_main_block_runs_demo_and_prints_suggestion(capsys):
    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")

    out = capsys.readouterr().out
    # Threshold defaults to 50; 60 simulated calls trip it once.
    assert "SUGGEST COMPACTION" in out
    assert "Reason:" in out
