"""Tests for the UserPromptSubmit lesson-recall hook.

Mirrors ``test_jit_recall.py``'s suite shape (the spec's T3
requirement): injection payload, noise gates (length, slash command,
score floor), surface-once sentinel, fail-safe control flow, and the
hooks.json registration drift guard.

Spec: docs/specs/lessons-corpus-rag/ (design D5 surface 2).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import time
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugin" / "hooks"


def _load_module(name: str):
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    if name in sys.modules:
        del sys.modules[name]  # fresh load so nothing cached leaks in
    spec = importlib.util.spec_from_file_location(name, _HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LESSONS = """\
## Lessons Learned

- **Squash merge tagging requires the merge SHA**: after a squash
  merge always tag the squash merge commit SHA, never the feature
  branch tip. Tagging before the squash points at a pre-squash hash.

- **Rebase replays commits unsigned**: a rebase drops GPG signatures;
  amend with -S before pushing rebased commits.
"""


@pytest.fixture
def hook_mod(tmp_path, monkeypatch):
    """Load the hook with sentinel dir + lessons file isolated to tmp_path."""
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "sentinels"))
    lessons = tmp_path / "lessons.md"
    lessons.write_text(LESSONS, encoding="utf-8")
    monkeypatch.setenv("ATTUNE_LESSONS_FILE", str(lessons))
    monkeypatch.delenv("ATTUNE_LESSON_RECALL", raising=False)
    monkeypatch.delenv("ATTUNE_LESSON_RECALL_FLOOR", raising=False)
    _load_module("_state")
    return _load_module("lesson_recall")


def _run(hook_mod, monkeypatch, capsys, payload: dict) -> tuple[int, str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = hook_mod.main()
    return rc, capsys.readouterr().out


def _payload(prompt: str, session: str = "sess-1") -> dict:
    return {
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
        "session_id": session,
        "cwd": "/tmp",
    }


MATCHING_PROMPT = "how do I tag the release after the squash merge lands"


# ==========================================================================
# Injection payload
# ==========================================================================


def test_matching_prompt_surfaces_lesson(hook_mod, monkeypatch, capsys):
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    assert rc == 0
    envelope = json.loads(out)
    ctx = envelope["hookSpecificOutput"]
    assert ctx["hookEventName"] == "UserPromptSubmit"
    assert "Squash merge tagging requires the merge SHA" in ctx["additionalContext"]
    assert "Lessons that may apply" in ctx["additionalContext"]


def test_unrelated_prompt_is_silent(hook_mod, monkeypatch, capsys):
    rc, out = _run(
        hook_mod,
        monkeypatch,
        capsys,
        _payload("please recolor the dashboard purple with sparkles"),
    )
    assert rc == 0
    assert out == ""


def test_body_excerpt_is_truncated(hook_mod, monkeypatch, capsys, tmp_path):
    long_body = "tag the squash merge commit " * 60
    (tmp_path / "lessons.md").write_text(
        f"## Lessons Learned\n\n- **Squash tag lesson**: {long_body}\n",
        encoding="utf-8",
    )
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "…" in ctx
    assert len(ctx) < hook_mod._BODY_EXCERPT_CHARS + 300


# ==========================================================================
# Noise gates
# ==========================================================================


def test_short_prompt_is_silent(hook_mod, monkeypatch, capsys):
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload("squash merge"))
    assert rc == 0
    assert out == ""


def test_slash_command_prompt_is_silent(hook_mod, monkeypatch, capsys):
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload("/recall squash merge tagging rules"))
    assert rc == 0
    assert out == ""


def test_score_floor_filters_weak_matches(hook_mod, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_LESSON_RECALL_FLOOR", "9999")
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    assert rc == 0
    assert out == ""


def test_bad_floor_value_falls_back(hook_mod, monkeypatch):
    monkeypatch.setenv("ATTUNE_LESSON_RECALL_FLOOR", "not-a-number")
    assert hook_mod._floor() == 8.0


# ==========================================================================
# Surface-once gate
# ==========================================================================


def test_second_fire_same_session_is_silent(hook_mod, monkeypatch, capsys):
    rc1, out1 = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    rc2, out2 = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    assert (rc1, rc2) == (0, 0)
    assert out1 != ""
    assert out2 == ""


def test_new_session_surfaces_again(hook_mod, monkeypatch, capsys):
    _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT, session="sess-1"))
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT, session="sess-2"))
    assert rc == 0
    assert out != ""


def test_sentinel_written_after_emit(hook_mod, monkeypatch, capsys, tmp_path):
    _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    sentinels = list((tmp_path / "sentinels").iterdir())
    assert sentinels
    assert all(s.name.startswith(".lesson-recalled-sess-1-") for s in sentinels)


def test_no_identity_fails_open_and_writes_no_sentinel(hook_mod, monkeypatch, capsys, tmp_path):
    """No session_id and no transcript_path: surface every time, write
    NOTHING — never a shared 'unknown' bucket (the 2026-07-13
    headless-collapse regression guard)."""
    payload = _payload(MATCHING_PROMPT)
    del payload["session_id"]
    _, out1 = _run(hook_mod, monkeypatch, capsys, payload)
    _, out2 = _run(hook_mod, monkeypatch, capsys, payload)
    assert out1 != "" and out2 != ""  # fail-open: fires both times
    base = tmp_path / "sentinels"
    leftover = [p.name for p in base.iterdir()] if base.is_dir() else []
    assert leftover == []


def test_child_hit_sentinels_on_parent_lesson(hook_mod, monkeypatch, capsys, tmp_path):
    """A child-doc hit must gate on the PARENT lesson id, so the same
    mega-lesson isn't re-surfaced via a different child."""
    (tmp_path / "lessons.md").write_text(
        "## Lessons Learned\n\n"
        "- **Mega tagging lesson**:\n"
        "  - **Squash merge tagging** — tag the squash merge commit SHA.\n"
        "  - **Tag protection** — protected tags cannot be force pushed.\n",
        encoding="utf-8",
    )
    _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    sentinels = [s.name for s in (tmp_path / "sentinels").iterdir()]
    assert any("mega-tagging-lesson" in s for s in sentinels)


def test_prune_removes_only_stale_own_sentinels(hook_mod, tmp_path):
    base = tmp_path / "sentinels"
    base.mkdir(parents=True, exist_ok=True)
    stale = base / ".lesson-recalled-old-x"
    fresh = base / ".lesson-recalled-new-x"
    other = base / ".jit-recalled-y"
    for p in (stale, fresh, other):
        p.write_text("", encoding="utf-8")
    old = time.time() - hook_mod._SENTINEL_TTL_SECONDS - 60
    import os

    os.utime(stale, (old, old))
    os.utime(other, (old, old))
    hook_mod._prune_stale()
    assert not stale.exists()
    assert fresh.exists()
    assert other.exists(), "must not touch other hooks' sentinels"


# ==========================================================================
# Fail-safety + off-switch
# ==========================================================================


def test_malformed_stdin_exits_zero(hook_mod, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert hook_mod.main() == 0
    assert capsys.readouterr().out == ""


def test_missing_lessons_file_exits_zero(hook_mod, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_LESSONS_FILE", "/nonexistent/lessons.md")
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    assert rc == 0
    assert out == ""


def test_env_off_switch_disables(hook_mod, monkeypatch, capsys):
    monkeypatch.setenv("ATTUNE_LESSON_RECALL", "0")
    rc, out = _run(hook_mod, monkeypatch, capsys, _payload(MATCHING_PROMPT))
    assert rc == 0
    assert out == ""


def test_missing_sentinel_dir_still_surfaces(monkeypatch, capsys, tmp_path):
    """Without a sentinel dir helper the hook surfaces (no gate) and exits 0."""
    monkeypatch.setenv("ATTUNE_AI_SENTINEL_DIR", str(tmp_path / "s"))
    lessons = tmp_path / "lessons.md"
    lessons.write_text(LESSONS, encoding="utf-8")
    monkeypatch.setenv("ATTUNE_LESSONS_FILE", str(lessons))
    mod = _load_module("lesson_recall")
    monkeypatch.setattr(mod, "_sentinel_dir", None)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_payload(MATCHING_PROMPT))))
    assert mod.main() == 0
    assert "additionalContext" in capsys.readouterr().out


# ==========================================================================
# Registration drift guard
# ==========================================================================


def test_hook_registered_for_user_prompt_submit(hook_mod):
    hooks = json.loads((_HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    groups = hooks["hooks"].get("UserPromptSubmit") or []
    assert any(
        "lesson_recall.py" in h["command"] for g in groups for h in g["hooks"]
    ), "lesson_recall.py not registered for UserPromptSubmit"
