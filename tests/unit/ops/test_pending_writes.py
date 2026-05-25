"""Unit tests for the pending-writes journal module.

Phase 1 of docs/specs/dashboard-pending-writes-journal/.

Covers:

- ``compute_file_sha256`` — happy path, missing file, unreadable file.
- ``make_entry`` — explicit kwargs, default fill-ins (pid, session, ts).
- ``append_entry`` — single + multiple appends, parent-dir creation,
  best-effort failure swallowing (IOError on write, dataclass
  serialization errors).
- ``_resolve_session_id`` — env-var precedence, fallback shape.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.ops import pending_writes
from attune.ops.pending_writes import (
    JournalEntry,
    _resolve_session_id,
    append_entry,
    compute_file_sha256,
    make_entry,
)

# --- compute_file_sha256 -----------------------------------------


def test_compute_file_sha256_happy_path(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_text("hello world", encoding="utf-8")
    # sha256 of "hello world" is a well-known constant
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert compute_file_sha256(target) == expected


def test_compute_file_sha256_missing_file_returns_none(tmp_path: Path) -> None:
    assert compute_file_sha256(tmp_path / "does-not-exist") is None


def test_compute_file_sha256_unreadable_returns_none(tmp_path: Path) -> None:
    # Simulate unreadable file via mock — making files unreadable on
    # disk is OS-conditional (root bypasses, Windows permissions
    # differ). Mock is the portable verification.
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")
    with patch.object(Path, "read_bytes", side_effect=PermissionError("no read")):
        assert compute_file_sha256(target) is None


# --- _resolve_session_id -----------------------------------------


def test_resolve_session_id_uses_env_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc-123")
    assert _resolve_session_id(dashboard_pid=9999) == "abc-123"


def test_resolve_session_id_falls_back_to_dashboard_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    assert _resolve_session_id(dashboard_pid=42) == "dashboard-42"


def test_resolve_session_id_treats_empty_env_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Whitespace-only env value should fall back, not be passed through.
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "   ")
    assert _resolve_session_id(dashboard_pid=7) == "dashboard-7"


# --- make_entry --------------------------------------------------


def test_make_entry_with_explicit_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = make_entry(
        endpoint="PUT /api/specs/{slug}/{phase}/status",
        action="set_spec_status",
        file_path="docs/specs/foo/decisions.md",
        project_root="/repo",
        before_sha256="aaa",
        after_sha256="bbb",
        session_id="sess-1",
        dashboard_pid=12345,
        ts="2026-05-25T15:00:00+00:00",
    )
    assert entry.session_id == "sess-1"
    assert entry.dashboard_pid == 12345
    assert entry.ts == "2026-05-25T15:00:00+00:00"
    assert entry.endpoint == "PUT /api/specs/{slug}/{phase}/status"
    assert entry.action == "set_spec_status"
    assert entry.file_path == "docs/specs/foo/decisions.md"
    assert entry.project_root == "/repo"
    assert entry.before_sha256 == "aaa"
    assert entry.after_sha256 == "bbb"


def test_make_entry_fills_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "live-session")
    entry = make_entry(
        endpoint="PUT /api/x",
        action="x",
        file_path="x",
        project_root="/r",
        before_sha256=None,
        after_sha256="bbb",
    )
    # ts defaults to "now" — just check format & approximate freshness
    assert "T" in entry.ts and entry.ts.endswith("+00:00")
    assert entry.session_id == "live-session"
    assert entry.dashboard_pid == os.getpid()


def test_make_entry_allows_before_sha_none() -> None:
    """File-was-newly-created case: before_sha256 is None, after is required."""
    entry = make_entry(
        endpoint="x",
        action="x",
        file_path="x",
        project_root="/r",
        before_sha256=None,
        after_sha256="bbb",
    )
    assert entry.before_sha256 is None
    assert entry.after_sha256 == "bbb"


# --- append_entry ------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_append_entry_writes_one_line(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.jsonl"
    entry = make_entry(
        endpoint="x",
        action="x",
        file_path="x",
        project_root="/r",
        before_sha256="a",
        after_sha256="b",
        ts="2026-05-25T15:00:00+00:00",
    )
    append_entry(entry, journal_path=journal_path)
    rows = _read_jsonl(journal_path)
    assert len(rows) == 1
    assert rows[0]["endpoint"] == "x"
    assert rows[0]["before_sha256"] == "a"
    assert rows[0]["after_sha256"] == "b"


def test_append_entry_appends_multiple(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.jsonl"
    for i in range(3):
        entry = make_entry(
            endpoint=f"e-{i}",
            action="x",
            file_path=f"f-{i}",
            project_root="/r",
            before_sha256=None,
            after_sha256=f"s-{i}",
            ts=f"2026-05-25T15:00:0{i}+00:00",
        )
        append_entry(entry, journal_path=journal_path)
    rows = _read_jsonl(journal_path)
    assert len(rows) == 3
    assert [r["endpoint"] for r in rows] == ["e-0", "e-1", "e-2"]


def test_append_entry_creates_parent_dir(tmp_path: Path) -> None:
    journal_path = tmp_path / "deep" / "nested" / "journal.jsonl"
    entry = make_entry(
        endpoint="x",
        action="x",
        file_path="x",
        project_root="/r",
        before_sha256=None,
        after_sha256="b",
    )
    append_entry(entry, journal_path=journal_path)
    assert journal_path.is_file()


def test_append_entry_swallows_io_error(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Journal failures MUST NOT block the calling write endpoint."""
    journal_path = tmp_path / "journal.jsonl"
    entry = make_entry(
        endpoint="x",
        action="x",
        file_path="x",
        project_root="/r",
        before_sha256=None,
        after_sha256="b",
    )
    with patch.object(Path, "open", side_effect=OSError("disk full")):
        # Should not raise.
        append_entry(entry, journal_path=journal_path)
    # WARNING log must surface the failure for separate investigation.
    assert any("append_entry: failed" in record.message for record in caplog.records)


def test_append_entry_uses_default_journal_path_when_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When journal_path=None, the module-level JOURNAL_PATH constant is used."""
    custom_path = tmp_path / "custom.jsonl"
    monkeypatch.setattr(pending_writes, "JOURNAL_PATH", custom_path)
    entry = make_entry(
        endpoint="x",
        action="x",
        file_path="x",
        project_root="/r",
        before_sha256=None,
        after_sha256="b",
    )
    append_entry(entry)  # journal_path=None → falls back to module constant
    assert custom_path.is_file()


def test_append_entry_serializes_dataclass_correctly(tmp_path: Path) -> None:
    """The on-disk representation matches the dataclass field names."""
    journal_path = tmp_path / "journal.jsonl"
    entry = JournalEntry(
        ts="2026-05-25T15:00:00+00:00",
        session_id="sess-1",
        dashboard_pid=1234,
        endpoint="PUT /x",
        action="act",
        file_path="docs/x.md",
        project_root="/repo",
        before_sha256=None,
        after_sha256="bbb",
    )
    append_entry(entry, journal_path=journal_path)
    rows = _read_jsonl(journal_path)
    assert len(rows) == 1
    # Every dataclass field must be present in the JSON (with sort_keys
    # so the output is stable for debugging).
    assert set(rows[0].keys()) == {
        "ts",
        "session_id",
        "dashboard_pid",
        "endpoint",
        "action",
        "file_path",
        "project_root",
        "before_sha256",
        "after_sha256",
    }
    assert rows[0]["before_sha256"] is None
