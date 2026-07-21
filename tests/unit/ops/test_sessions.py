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


from attune.ops import data  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

# ---------------------------------------------------------------------------
# claude_sessions_dir / _encoded_project_path
# ---------------------------------------------------------------------------


def test_encoded_project_path_matches_claude_code_convention(tmp_path):
    """The encoding is ``str(resolved_path).replace('/', '-')``. We assert
    on the basename only since ``resolve()`` adds the absolute prefix.

    Also asserts no backslashes survive — Windows ``Path.resolve()``
    produces backslash separators, and any backslash left in the
    encoded segment causes the subsequent ``Path / encoded`` to be
    treated as an absolute path (silently discarding the prefix).
    """
    encoded = data._encoded_project_path(tmp_path)
    expected_suffix = str(tmp_path).replace("/", "-").replace("\\", "-").replace(":", "-")
    assert encoded.endswith(expected_suffix)
    assert "/" not in encoded
    assert "\\" not in encoded
    assert ":" not in encoded


def test_encoded_project_path_strips_windows_separators_and_colon():
    """Regression test for the two Windows CI failures observed
    2026-05-15: (1) PR #382 round, backslashes survived ``str
    .replace("/", "-")`` and pathlib treated the resulting ``D:\\``
    prefix as absolute; (2) post-#382 round, the backslash fix
    revealed the next layer — drive-letter colons survived and
    pathlib treated the resulting ``D:-...`` segment as a drive
    specifier on Windows.

    Passes a string with both Windows separators AND a colon. On
    POSIX the encoder still has to scrub all three so the regression
    is catchable without a Windows runner.
    """
    encoded = data._encoded_project_path("C:\\Users\\Test\\project")
    assert "\\" not in encoded, f"backslash survived encoding: {encoded!r}"
    assert "/" not in encoded, f"forward slash survived encoding: {encoded!r}"
    assert ":" not in encoded, f"colon survived encoding: {encoded!r}"


def test_claude_sessions_dir_is_under_user_home(tmp_path):
    """The dir is rooted at ``~/.claude/projects/<encoded>/``."""
    sessions_dir = data.claude_sessions_dir(tmp_path)
    assert sessions_dir.parent.parent.name == ".claude"
    assert sessions_dir.parent.name == "projects"


def test_claude_sessions_dir_under_user_home_with_windows_style_input():
    """Cross-platform regression: even when project_root looks like
    a Windows absolute path (drive letter + backslashes), the
    resulting sessions dir must still nest under
    ``~/.claude/projects/``.

    Before the colon fix, ``str(Path("C:\\Users\\X\\p").resolve())``
    on Windows produced ``C:\\Users\\X\\p``; the backslashes mapped
    to ``-`` but the leading ``C:`` survived. The encoded segment
    ``C:-Users-X-p`` is treated as a drive specifier when
    concatenated as a path part, so the result rooted at ``C:``
    instead of under ``.claude/projects/``.
    """
    sessions_dir = data.claude_sessions_dir("C:\\Users\\Test\\project")
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


def _patch_home(monkeypatch, home_path) -> None:
    """Patch ``Path.home()`` to return ``home_path`` on every platform.

    Python's ``pathlib.Path.home()`` consults different env vars per OS:

    - POSIX: ``HOME``
    - Windows: ``USERPROFILE`` (falls back to ``HOMEDRIVE``+``HOMEPATH``)

    A test that patches only ``HOME`` will work on POSIX runners but
    silently no-op on Windows — ``Path.home()`` will still return the
    real user-profile directory, and any code under test that writes
    sessions to a monkeypatched home location won't be found.

    Setting both env vars covers the cross-platform case with one call.
    """
    home_str = str(home_path)
    monkeypatch.setenv("HOME", home_str)
    monkeypatch.setenv("USERPROFILE", home_str)


def test_list_recent_sessions_returns_empty_when_dir_missing(tmp_path, monkeypatch):
    """No ``~/.claude/projects/<encoded>/`` dir → empty list, not error.

    A fresh install or a project the user has never launched Claude
    Code from looks like this. The dashboard must render the empty
    state, not crash.
    """
    _patch_home(monkeypatch, tmp_path / "home")
    assert data.list_recent_sessions(tmp_path / "project") == []


def test_list_recent_sessions_reads_jsonl(tmp_path, monkeypatch):
    """A JSONL with one user prompt → one Session record with that
    prompt as the heuristic starter."""
    home = tmp_path / "home"
    _patch_home(monkeypatch, home)
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
    _patch_home(monkeypatch, home)
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
    _patch_home(monkeypatch, home)
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
    _patch_home(monkeypatch, home)
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


# ---------------------------------------------------------------------------
# enumerate_project_encoded_keys — multi-key resolution
# ---------------------------------------------------------------------------


def test_enumerate_project_encoded_keys_returns_empty_when_projects_root_missing(
    tmp_path, monkeypatch
):
    """No ``~/.claude/projects/`` dir → empty list, not error."""
    _patch_home(monkeypatch, tmp_path / "home")
    assert data.enumerate_project_encoded_keys(tmp_path / "project") == []


def test_enumerate_project_encoded_keys_finds_canonical_key(tmp_path, monkeypatch):
    """Canonical encoded-key dir is matched exactly."""
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    canonical = data.claude_sessions_dir(project_root)
    canonical.mkdir(parents=True)

    matches = data.enumerate_project_encoded_keys(project_root)
    assert canonical in matches
    assert len(matches) == 1


def test_enumerate_project_encoded_keys_finds_worktree_keys(tmp_path, monkeypatch):
    """Sibling dirs starting with ``<encoded>-`` are matched as worktree keys.

    Mirrors the empirical attune-ai layout: one canonical key plus
    several ``<encoded>--claude-worktrees-<slug>`` dirs.
    """
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    encoded = data._encoded_project_path(project_root)
    projects_root = tmp_path / "home" / ".claude" / "projects"
    projects_root.mkdir(parents=True)

    canonical = projects_root / encoded
    worktree_a = projects_root / f"{encoded}--claude-worktrees-foo"
    worktree_b = projects_root / f"{encoded}--claude-worktrees-bar"
    canonical.mkdir()
    worktree_a.mkdir()
    worktree_b.mkdir()

    matches = data.enumerate_project_encoded_keys(project_root)
    assert set(matches) == {canonical, worktree_a, worktree_b}


def test_enumerate_project_encoded_keys_rejects_sibling_project_false_match(tmp_path, monkeypatch):
    """A dir whose name starts with ``<encoded>`` but no trailing
    ``-`` separator (e.g. a sibling project ``attune-ai-foo`` vs
    ``attune-ai``) must NOT match.

    The trailing-dash separator is the explicit guard against this
    in the spec (Decision 1).
    """
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    encoded = data._encoded_project_path(project_root)
    projects_root = tmp_path / "home" / ".claude" / "projects"
    projects_root.mkdir(parents=True)

    canonical = projects_root / encoded
    sibling_no_dash = projects_root / f"{encoded}xyz"  # no separator
    canonical.mkdir()
    sibling_no_dash.mkdir()

    matches = data.enumerate_project_encoded_keys(project_root)
    assert canonical in matches
    assert sibling_no_dash not in matches


def test_list_recent_sessions_dedups_across_encoded_keys_newest_wins(tmp_path, monkeypatch):
    """Same session id under canonical AND worktree key → newest mtime wins.

    Rare in practice (suggests a worktree was renamed or recreated)
    but the spec requires WARN log + newest-wins resolution.
    """
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    encoded = data._encoded_project_path(project_root)
    projects_root = tmp_path / "home" / ".claude" / "projects"
    canonical = projects_root / encoded
    worktree = projects_root / f"{encoded}--claude-worktrees-foo"

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    older = (now - timedelta(days=2)).timestamp()
    newer = (now - timedelta(hours=1)).timestamp()

    _write_session_jsonl(
        canonical,
        "shared-id",
        events=[{"timestamp": "2026-05-12T12:00:00Z", "content": "old version"}],
        mtime=older,
    )
    _write_session_jsonl(
        worktree,
        "shared-id",
        events=[{"timestamp": "2026-05-14T11:00:00Z", "content": "new version"}],
        mtime=newer,
    )

    result = data.list_recent_sessions(project_root, now=now)
    assert len(result) == 1
    assert result[0].id == "shared-id"
    # The newer worktree copy should win — its prompt is the one rendered.
    assert result[0].starter_prompt.startswith("new version")


def test_list_recent_sessions_aggregates_across_encoded_keys(tmp_path, monkeypatch):
    """Sessions from multiple encoded keys are aggregated into one list."""
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    encoded = data._encoded_project_path(project_root)
    projects_root = tmp_path / "home" / ".claude" / "projects"
    canonical = projects_root / encoded
    worktree_a = projects_root / f"{encoded}--claude-worktrees-aaa"
    worktree_b = projects_root / f"{encoded}--claude-worktrees-bbb"

    _write_session_jsonl(
        canonical,
        "from-canonical",
        events=[{"timestamp": "2026-05-14T10:00:00Z", "content": "canonical session"}],
    )
    _write_session_jsonl(
        worktree_a,
        "from-worktree-a",
        events=[{"timestamp": "2026-05-14T10:30:00Z", "content": "worktree-a session"}],
    )
    _write_session_jsonl(
        worktree_b,
        "from-worktree-b",
        events=[{"timestamp": "2026-05-14T11:00:00Z", "content": "worktree-b session"}],
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(project_root, now=now)
    ids = {s.id for s in result}
    assert ids == {"from-canonical", "from-worktree-a", "from-worktree-b"}


def test_list_recent_sessions_caps_at_default_limit(tmp_path, monkeypatch):
    """The list cap (DEFAULT_SESSION_LIST_CAP) bounds the result size.

    Decision 5 (decisions.md): cap at 20 most-recent sessions for
    budget-cap math (~$0.02 worst case at $0.001/session).
    """
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    sessions_dir = data.claude_sessions_dir(project_root)

    # Write 25 sessions, each with a slightly different mtime so the
    # sort is deterministic.
    base_ts = datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    for i in range(25):
        _write_session_jsonl(
            sessions_dir,
            f"session-{i:02d}",
            events=[
                {
                    "timestamp": f"2026-05-14T10:{i:02d}:00Z",
                    "content": f"prompt {i}",
                }
            ],
            mtime=base_ts + i * 60,
        )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(project_root, now=now)
    assert len(result) == data.DEFAULT_SESSION_LIST_CAP == 20
    # Newest-first sort + cap → the 20 highest indexes survive.
    surviving_ids = {s.id for s in result}
    assert "session-24" in surviving_ids
    assert "session-05" in surviving_ids
    assert "session-04" not in surviving_ids


def test_list_recent_sessions_limit_none_returns_all(tmp_path, monkeypatch):
    """``limit=None`` disables the cap (test hook)."""
    _patch_home(monkeypatch, tmp_path / "home")
    project_root = tmp_path / "project"
    sessions_dir = data.claude_sessions_dir(project_root)

    base_ts = datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    for i in range(25):
        _write_session_jsonl(
            sessions_dir,
            f"session-{i:02d}",
            events=[{"timestamp": "2026-05-14T10:00:00Z", "content": f"prompt {i}"}],
            mtime=base_ts + i * 60,
        )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    result = data.list_recent_sessions(project_root, limit=None, now=now)
    assert len(result) == 25


def test_list_recent_sessions_handles_no_content_events(tmp_path, monkeypatch):
    """A session with no events that have ``content`` (e.g. dequeue-only,
    attachment-only) yields a record with placeholder starter prompt."""
    home = tmp_path / "home"
    _patch_home(monkeypatch, home)
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
    """Build a TestClient-ready app with the heuristic-only data layer.

    Default-disables the Haiku summarizer so a developer with
    ``ANTHROPIC_API_KEY`` exported in their shell doesn't silently
    trigger real LLM calls on test runs — manifests as the route
    REPLACING heuristic ``starter_prompt`` strings with the
    real-Haiku summary, breaking any assertion that checks for
    fixture content in the rendered output. The CI matrix has no
    key set so the failure only surfaces locally for keys-exported
    devs, which makes it doubly easy to miss.

    Tests in this file all target the deterministic heuristic
    path (see file docstring). Tests that EXERCISE the LLM live
    in ``test_sessions_route_s3b.py`` and install their own fake
    ``anthropic`` module via ``_install_fake_anthropic`` (and use
    their own ``_make_app`` in that file).
    """
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ATTUNE_OPS_SESSIONS_LLM", "0")
    _patch_home(monkeypatch, tmp_path / "home")
    config = build_config(
        project_root=tmp_path / "project",
        trusted_hosts=("testserver", "test"),
    )
    return create_app(config)
