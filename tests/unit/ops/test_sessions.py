"""Tests for the /sessions page data layer (S2 of ops-sessions-page).

S2 reads ``~/.claude/projects/<encoded-project-root>/*.jsonl``,
filters to mtime within the last 3 days, and renders one row per
session with a heuristic starter prompt. S3 will replace the
heuristic with Haiku-summarized prompts; these tests cover only
the deterministic disk-read + heuristic side.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops import data  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

# ---------------------------------------------------------------------------
# claude_sessions_dir / _encoded_project_path
# ---------------------------------------------------------------------------


def test_encoded_project_path_matches_claude_code_convention(tmp_path):
    """The encoding is ``str(resolved_path).replace('/', '-')``. We assert
    on the basename only since ``resolve()`` adds the absolute prefix."""
    encoded = data._encoded_project_path(tmp_path)
    assert encoded.endswith(str(tmp_path).replace("/", "-"))
    assert "/" not in encoded


def test_claude_sessions_dir_is_under_user_home(tmp_path):
    """The dir is rooted at ``~/.claude/projects/<encoded>/``."""
    sessions_dir = data.claude_sessions_dir(tmp_path)
    assert sessions_dir.parent.parent.name == ".claude"
    assert sessions_dir.parent.name == "projects"


# ---------------------------------------------------------------------------
# _heuristic_starter_prompt — truncation + whitespace handling
# ---------------------------------------------------------------------------


def test_heuristic_starter_prompt_passes_short_text_through():
    assert data._heuristic_starter_prompt("Hello world") == "Hello world"


def test_heuristic_starter_prompt_collapses_whitespace():
    assert data._heuristic_starter_prompt("  multi\n\n  line\t text  ") == ("multi line text")


def test_heuristic_starter_prompt_truncates_at_word_boundary():
    text = "word " * 60  # 300 chars
    result = data._heuristic_starter_prompt(text, char_limit=50)
    assert result.endswith("…")
    assert len(result) <= 50
    # Word boundary respected: the result shouldn't end with a partial word
    assert not result.removesuffix("…").endswith(" word w")


def test_heuristic_starter_prompt_handles_empty():
    assert data._heuristic_starter_prompt("") == ""
    assert data._heuristic_starter_prompt(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# list_recent_sessions — disk reading + filtering
# ---------------------------------------------------------------------------


def _write_session_jsonl(
    sessions_dir: Path,
    session_id: str,
    *,
    events: list[dict],
    mtime: float | None = None,
) -> Path:
    """Write a JSONL session log with an explicit list of events."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session_id}.jsonl"
    path.write_text(
        "\n".join(json.dumps(ev) for ev in events) + "\n",
        encoding="utf-8",
    )
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_list_recent_sessions_returns_empty_when_dir_missing(tmp_path, monkeypatch):
    """No ``~/.claude/projects/<encoded>/`` dir → empty list, not error.

    A fresh install or a project the user has never launched Claude
    Code from looks like this. The dashboard must render the empty
    state, not crash.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert data.list_recent_sessions(tmp_path / "project") == []


def test_list_recent_sessions_reads_jsonl(tmp_path, monkeypatch):
    """A JSONL with one user prompt → one Session record with that
    prompt as the heuristic starter."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    sessions_dir = data.claude_sessions_dir(tmp_path / "project")
    _write_session_jsonl(
        sessions_dir,
        "abc12345-c539-4057-ba26-24ce3dffec27",
        events=[
            {
                "type": "queue-operation",
                "operation": "enqueue",
                "timestamp": "2026-05-14T10:00:00.000Z",
                "sessionId": "abc12345",
                "content": "Help me debug the test_runner test failure on Windows Py 3.11.",
            },
            {
                "type": "queue-operation",
                "operation": "dequeue",
                "timestamp": "2026-05-14T10:00:00.500Z",
                "sessionId": "abc12345",
            },
            {
                "type": "queue-operation",
                "operation": "enqueue",
                "timestamp": "2026-05-14T10:05:00.000Z",
                "sessionId": "abc12345",
                "content": "Now what's the simplest fix?",
            },
        ],
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(tmp_path / "project", now=now)

    assert len(result) == 1
    session = result[0]
    assert session.id == "abc12345-c539-4057-ba26-24ce3dffec27"
    assert session.started_at == "2026-05-14T10:00:00.000Z"
    assert session.last_activity == "2026-05-14T10:05:00.000Z"
    assert session.duration_seconds == pytest.approx(300.0)  # 5 minutes
    assert session.message_count == 2  # two enqueue events with content
    assert session.starter_prompt.startswith("Help me debug")
    assert session.source == "heuristic"


def test_list_recent_sessions_filters_by_mtime(tmp_path, monkeypatch):
    """Files older than ``days`` are excluded by mtime."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    sessions_dir = data.claude_sessions_dir(tmp_path / "project")

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    fresh = (now - timedelta(days=1)).timestamp()
    stale = (now - timedelta(days=5)).timestamp()

    _write_session_jsonl(
        sessions_dir,
        "fresh-session",
        events=[{"timestamp": "2026-05-13T12:00:00Z", "content": "recent prompt"}],
        mtime=fresh,
    )
    _write_session_jsonl(
        sessions_dir,
        "stale-session",
        events=[{"timestamp": "2026-05-09T12:00:00Z", "content": "old prompt"}],
        mtime=stale,
    )

    result = data.list_recent_sessions(tmp_path / "project", days=3, now=now)
    ids = [s.id for s in result]
    assert "fresh-session" in ids
    assert "stale-session" not in ids


def test_list_recent_sessions_sorts_most_recent_first(tmp_path, monkeypatch):
    """Sessions sort by ``last_activity`` desc."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    sessions_dir = data.claude_sessions_dir(tmp_path / "project")

    _write_session_jsonl(
        sessions_dir,
        "older-session",
        events=[{"timestamp": "2026-05-14T10:00:00Z", "content": "old"}],
    )
    time.sleep(0.01)
    _write_session_jsonl(
        sessions_dir,
        "newer-session",
        events=[{"timestamp": "2026-05-14T11:00:00Z", "content": "new"}],
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(tmp_path / "project", now=now)
    assert [s.id for s in result] == ["newer-session", "older-session"]


def test_list_recent_sessions_skips_malformed_lines(tmp_path, monkeypatch):
    """A JSONL with one bad line + one good line still yields the
    Session record built from the good line; the parse error is
    per-line, not fatal."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    sessions_dir = data.claude_sessions_dir(tmp_path / "project")
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "mixed.jsonl").write_text(
        "{not valid json\n"
        '{"timestamp": "2026-05-14T10:00:00Z", "content": "good prompt"}\n'
        "another bad line\n",
        encoding="utf-8",
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(tmp_path / "project", now=now)
    assert len(result) == 1
    assert result[0].starter_prompt == "good prompt"
    assert result[0].message_count == 1


def test_list_recent_sessions_handles_no_content_events(tmp_path, monkeypatch):
    """A session with no events that have ``content`` (e.g. dequeue-only,
    attachment-only) yields a record with placeholder starter prompt."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    sessions_dir = data.claude_sessions_dir(tmp_path / "project")
    _write_session_jsonl(
        sessions_dir,
        "no-prompts",
        events=[
            {"type": "attachment", "timestamp": "2026-05-14T10:00:00Z"},
            {
                "type": "queue-operation",
                "operation": "dequeue",
                "timestamp": "2026-05-14T10:00:01Z",
            },
        ],
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(tmp_path / "project", now=now)
    assert len(result) == 1
    assert result[0].message_count == 0
    assert result[0].starter_prompt == "(no prompt recorded)"


# ---------------------------------------------------------------------------
# Sessions page rendering — empty-state vs populated
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    config = build_config(
        project_root=tmp_path / "project",
        trusted_hosts=("testserver", "test"),
    )
    return create_app(config)


def test_sessions_page_renders_session_rows_when_data_present(tmp_path, monkeypatch):
    """A populated sessions dir → the page renders the table, not the
    empty state."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    sessions_dir = (
        Path(tmp_path) / "home" / ".claude" / "projects" / data._encoded_project_path(project_root)
    )
    _write_session_jsonl(
        sessions_dir,
        "abcd1234-c539-4057-ba26-24ce3dffec27",
        events=[
            {"timestamp": "2026-05-14T10:00:00Z", "content": "Test prompt for session listing."}
        ],
    )

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/sessions")
    assert resp.status_code == 200
    body = resp.text
    # Table should render, empty-state should NOT.
    assert "sessions-table" in body
    assert "abcd1234" in body  # short id appears
    assert "Test prompt" in body
    assert "heuristic" in body
    assert "No sessions in the last 3 days" not in body


def test_sessions_page_renders_empty_state_when_no_sessions(tmp_path, monkeypatch):
    """No sessions dir for this project → empty state."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/sessions")
    assert resp.status_code == 200
    body = resp.text
    assert "No sessions in the last 3 days" in body
    assert "sessions-table" not in body
