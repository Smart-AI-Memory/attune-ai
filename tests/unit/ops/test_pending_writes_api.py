"""HTTP-level tests for GET /api/pending-writes.

Phase 1 of docs/specs/dashboard-pending-writes-journal/.

Covers:

- Empty journal returns ``{pending: [], summary: {...}}``
- Single entry: returns enriched with all computed fields
- Entry whose file is now committed: ``is_committed=true``
- Entry whose file was manually reverted: ``matches_journal=false``
- Entry whose dashboard PID is dead: ``dashboard_still_running=false``
- Summary counts (total, uncommitted, stale-dashboard, drifted)
- Integration: PUT /api/specs/{slug}/{phase}/status appends to journal

Tests run against a real FastAPI TestClient + real create_app.
Journal path is overridden via ``app.state.pending_writes_journal_path``.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops import pending_writes  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

# --- fixtures ----------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A tmp project root, initialized as a git repo so is_committed checks work."""
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=project,
        check=True,
    )
    return project


@pytest.fixture
def client_factory(tmp_project: Path, tmp_path: Path):
    """Factory: build a TestClient with a custom journal path on app.state."""

    def _make(journal_path: Path | None = None) -> TestClient:
        config = build_config(
            project_root=tmp_project,
            allow_run=True,
            trusted_hosts=("testserver", "test"),
        )
        app = create_app(config)
        if journal_path is None:
            journal_path = tmp_path / "journal.jsonl"
        app.state.pending_writes_journal_path = journal_path
        return TestClient(app)

    return _make


def _write_journal(journal_path: Path, entries: list[dict]) -> None:
    """Write a sequence of journal entry dicts to a JSONL file."""
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _make_journal_dict(
    *,
    project_root: Path,
    file_path: str,
    after_sha256: str,
    before_sha256: str | None = None,
    dashboard_pid: int | None = None,
    ts: str = "2026-05-25T15:00:00+00:00",
) -> dict:
    """Build a journal entry dict matching the on-disk schema."""
    if dashboard_pid is None:
        dashboard_pid = os.getpid()
    return {
        "ts": ts,
        "session_id": "test-session",
        "dashboard_pid": dashboard_pid,
        "endpoint": "PUT /api/specs/{slug}/{phase}/status",
        "action": "set_spec_status",
        "file_path": file_path,
        "project_root": str(project_root),
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
    }


# --- GET /api/pending-writes -------------------------------------


def test_empty_journal_returns_empty_pending_and_zero_summary(
    client_factory,
) -> None:
    client = client_factory()
    response = client.get("/api/pending-writes")
    assert response.status_code == 200
    body = response.json()
    assert body["pending"] == []
    assert body["summary"] == {
        "total_entries": 0,
        "uncommitted_count": 0,
        "stale_dashboard_count": 0,
        "drifted_count": 0,
    }


def test_single_entry_enriches_all_computed_fields(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    # Create a real file with known content, then journal it.
    target = tmp_project / "spec.md"
    target.write_text("hello\n", encoding="utf-8")
    after_sha = pending_writes.compute_file_sha256(target)

    journal_path = tmp_path / "journal.jsonl"
    _write_journal(
        journal_path,
        [
            _make_journal_dict(
                project_root=tmp_project,
                file_path="spec.md",
                after_sha256=after_sha,
            )
        ],
    )

    client = client_factory(journal_path=journal_path)
    response = client.get("/api/pending-writes")
    assert response.status_code == 200
    body = response.json()
    assert len(body["pending"]) == 1
    entry = body["pending"][0]
    # All enriched fields present
    assert "dashboard_still_running" in entry
    assert "current_disk_sha256" in entry
    assert "matches_journal" in entry
    assert "is_committed" in entry
    assert "age_seconds" in entry
    # current disk matches journal (no manual revert)
    assert entry["matches_journal"] is True
    # file is uncommitted (untracked in git)
    assert entry["is_committed"] is False
    # dashboard pid is THIS process so dashboard_still_running=True
    assert entry["dashboard_still_running"] is True


def test_entry_whose_file_was_committed_shows_is_committed_true(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    target = tmp_project / "spec.md"
    target.write_text("hello\n", encoding="utf-8")
    after_sha = pending_writes.compute_file_sha256(target)
    # Commit the file.
    subprocess.run(["git", "add", "spec.md"], cwd=tmp_project, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "add spec"],
        cwd=tmp_project,
        check=True,
    )

    journal_path = tmp_path / "journal.jsonl"
    _write_journal(
        journal_path,
        [
            _make_journal_dict(
                project_root=tmp_project,
                file_path="spec.md",
                after_sha256=after_sha,
            )
        ],
    )

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()
    entry = body["pending"][0]
    assert entry["is_committed"] is True
    assert body["summary"]["uncommitted_count"] == 0


def test_entry_whose_file_was_manually_reverted_shows_matches_journal_false(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    target = tmp_project / "spec.md"
    target.write_text("original\n", encoding="utf-8")
    journaled_sha = pending_writes.compute_file_sha256(target)
    # User manually edits the file AFTER the journal entry was made.
    target.write_text("user-changed-it\n", encoding="utf-8")

    journal_path = tmp_path / "journal.jsonl"
    _write_journal(
        journal_path,
        [
            _make_journal_dict(
                project_root=tmp_project,
                file_path="spec.md",
                after_sha256=journaled_sha,
            )
        ],
    )

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()
    entry = body["pending"][0]
    assert entry["matches_journal"] is False
    assert body["summary"]["drifted_count"] == 1


def test_entry_whose_dashboard_pid_is_dead_marked_stale(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    target = tmp_project / "spec.md"
    target.write_text("hello\n", encoding="utf-8")
    after_sha = pending_writes.compute_file_sha256(target)

    journal_path = tmp_path / "journal.jsonl"
    # PID 1 (init) won't accept kill(0) from a normal user → "dead" for our purposes.
    # Use a guaranteed-dead PID instead: a high number unlikely to be allocated.
    dead_pid = 2_147_483_646  # max int-32, will not exist
    _write_journal(
        journal_path,
        [
            _make_journal_dict(
                project_root=tmp_project,
                file_path="spec.md",
                after_sha256=after_sha,
                dashboard_pid=dead_pid,
            )
        ],
    )

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()
    entry = body["pending"][0]
    assert entry["dashboard_still_running"] is False
    assert body["summary"]["stale_dashboard_count"] == 1


def test_summary_counts_aggregate_correctly(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    # Three entries: one fresh, one stale-dashboard, one drifted-from-disk.
    fresh = tmp_project / "fresh.md"
    fresh.write_text("a\n", encoding="utf-8")
    stale = tmp_project / "stale.md"
    stale.write_text("b\n", encoding="utf-8")
    drifted = tmp_project / "drifted.md"
    drifted.write_text("c\n", encoding="utf-8")
    journaled_drift_sha = pending_writes.compute_file_sha256(drifted)
    drifted.write_text("changed\n", encoding="utf-8")  # user edited after journal

    journal_path = tmp_path / "journal.jsonl"
    _write_journal(
        journal_path,
        [
            _make_journal_dict(
                project_root=tmp_project,
                file_path="fresh.md",
                after_sha256=pending_writes.compute_file_sha256(fresh),
            ),
            _make_journal_dict(
                project_root=tmp_project,
                file_path="stale.md",
                after_sha256=pending_writes.compute_file_sha256(stale),
                dashboard_pid=2_147_483_646,
            ),
            _make_journal_dict(
                project_root=tmp_project,
                file_path="drifted.md",
                after_sha256=journaled_drift_sha,
            ),
        ],
    )

    client = client_factory(journal_path=journal_path)
    summary = client.get("/api/pending-writes").json()["summary"]
    assert summary["total_entries"] == 3
    # All three uncommitted (none added to git)
    assert summary["uncommitted_count"] == 3
    # One has a dead PID
    assert summary["stale_dashboard_count"] == 1
    # One drifted from disk
    assert summary["drifted_count"] == 1


def test_corrupt_journal_line_is_skipped_not_fatal(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target = tmp_project / "spec.md"
    target.write_text("hello\n", encoding="utf-8")
    valid_entry = _make_journal_dict(
        project_root=tmp_project,
        file_path="spec.md",
        after_sha256=pending_writes.compute_file_sha256(target),
    )
    journal_path = tmp_path / "journal.jsonl"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("w", encoding="utf-8") as fh:
        fh.write("this is not json\n")
        fh.write(json.dumps(valid_entry) + "\n")
        fh.write("{also-broken\n")

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()
    # Only the valid line surfaces.
    assert len(body["pending"]) == 1
    assert any("corrupt journal line" in record.message for record in caplog.records)


# --- integration: PUT spec status appends to journal -------------


def test_put_spec_status_appends_journal_entry(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    # Set up a spec the route can find.
    specs_root = tmp_project / "docs" / "specs" / "demo"
    specs_root.mkdir(parents=True)
    spec_file = specs_root / "decisions.md"
    spec_file.write_text("# demo\n\n**Status:** draft\n\nbody\n", encoding="utf-8")

    journal_path = tmp_path / "journal.jsonl"
    client = client_factory(journal_path=journal_path)

    response = client.put(
        "/api/specs/demo/decisions/status",
        json={"status": "approved"},
    )
    assert response.status_code == 200, response.text

    # Journal entry should exist.
    assert journal_path.is_file()
    lines = journal_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "set_spec_status"
    assert entry["endpoint"] == "PUT /api/specs/{slug}/{phase}/status"
    assert entry["file_path"] == "docs/specs/demo/decisions.md"
    assert entry["project_root"] == str(tmp_project)
    assert entry["before_sha256"] is not None
    assert entry["after_sha256"] is not None
    assert entry["before_sha256"] != entry["after_sha256"]


def test_failed_put_status_does_not_append_journal(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    """Validation failures must NOT leak a journal entry."""
    journal_path = tmp_path / "journal.jsonl"
    client = client_factory(journal_path=journal_path)

    # Invalid status value → 422 from validator before any write.
    response = client.put(
        "/api/specs/demo/decisions/status",
        json={"status": "not-a-real-status"},
    )
    assert response.status_code != 200
    # Journal file should never have been touched.
    assert not journal_path.is_file()


def test_journal_failure_does_not_block_put_status(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D5 contract: journal failures must NOT propagate as 500s.

    Even if ``pending_writes.append_entry`` itself raises (bypassing
    its own internal try/except, e.g. via a future regression or
    direct subclass surprise), the spec-status write endpoint must
    still succeed. The route layer is exception-safe by design.
    """
    specs_root = tmp_project / "docs" / "specs" / "demo"
    specs_root.mkdir(parents=True)
    spec_file = specs_root / "decisions.md"
    spec_file.write_text("# demo\n\n**Status:** draft\n\nbody\n", encoding="utf-8")

    journal_path = tmp_path / "journal.jsonl"
    client = client_factory(journal_path=journal_path)

    # Patch append_entry to raise an arbitrary Exception (simulating
    # a regression where the internal swallow contract is violated).
    # The route's _record_pending_write wrapper MUST catch this so the
    # write endpoint returns 200 and the spec file actually gets
    # updated. Patch path: where the route IMPORTS it from, not where
    # it's defined — see CLAUDE.md "patch the import site" lesson.
    with patch(
        "attune.ops.routes.specs.pending_writes.append_entry",
        side_effect=Exception("simulated journal regression"),
    ):
        response = client.put(
            "/api/specs/demo/decisions/status",
            json={"status": "approved"},
        )

    # Contract: 200 OK even though journal raised.
    assert response.status_code == 200, response.text

    # Spec file actually got updated (write happened despite journal
    # explosion).
    body = spec_file.read_text(encoding="utf-8")
    assert "**Status:** approved" in body
    assert "**Status:** draft" not in body

    # Journal failure was logged for separate investigation.
    assert any("journal append failed" in record.message for record in caplog.records)
