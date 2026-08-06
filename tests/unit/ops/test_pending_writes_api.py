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


@pytest.fixture(autouse=True)
def _disable_tmp_path_prefix_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests in this module use pytest ``tmp_path`` as the project_root,
    which is itself under one of the production tmp-path prefixes
    (``/private/var/folders/.../pytest-of-...`` on macOS,
    ``/tmp/pytest-of-...`` on Linux). The prod prefix filter would
    reject those entries and break every test in the module.

    Disable the prefix filter at the source-list level. Tests that
    specifically verify prefix-filter behavior re-enable it via
    their own monkeypatch or by setting specific prefix values.
    """
    from attune.ops.routes import pending_writes as pw_routes

    monkeypatch.setattr(pw_routes, "_TMP_PATH_PREFIXES", ())


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


def test_entries_with_nonexistent_project_root_are_filtered_out(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
) -> None:
    """Stale entries (project_root no longer on disk) drop out at read.

    Most common cause: pytest tmp_path is garbage-collected after a
    test, leaving journal entries pointing at non-existent dirs. Same
    for projects the user has since deleted or moved.

    Module's autouse fixture disables the prefix filter, so this test
    isolates the existence-check behavior. Prefix-filter behavior is
    verified separately in the next test.

    See ``_is_real_entry`` in routes/pending_writes.py.
    """
    real = tmp_project / "real.md"
    real.write_text("real\n", encoding="utf-8")

    journal_path = tmp_path / "journal.jsonl"
    _write_journal(
        journal_path,
        [
            # Real: tmp_project exists
            _make_journal_dict(
                project_root=tmp_project,
                file_path="real.md",
                after_sha256=pending_writes.compute_file_sha256(real),
            ),
            # Stale: dir was never created
            _make_journal_dict(
                project_root=tmp_path / "deleted-dir-never-created",
                file_path="some.md",
                after_sha256="aaa",
            ),
        ],
    )

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()
    assert len(body["pending"]) == 1
    assert body["pending"][0]["file_path"] == "real.md"
    assert body["summary"]["total_entries"] == 1


def test_entries_under_tmp_path_prefixes_are_filtered_out(
    tmp_path: Path,
    client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entries whose project_root is under a known transient-dir prefix
    drop out at read, even when the dir still exists on disk.

    pytest tmp_path is itself under one of those prefixes
    (``/private/var/folders/.../pytest-of-...`` on macOS), so we can
    use tmp_path directly as a project_root that DOES exist but should
    still be filtered as test-fixture pollution.

    Re-enables the prefix list that the module's autouse fixture
    cleared.

    See ``_TMP_PATH_PREFIXES`` in routes/pending_writes.py.
    """
    import tempfile

    from attune.ops.routes import pending_writes as pw_routes

    # Use the actual platform tempdir as the prefix so the test
    # works on macOS, Linux, and Windows. Include both the raw
    # ``gettempdir()`` form (``/var/folders/...``) AND the resolved
    # form (``/private/var/folders/...``) because macOS's
    # ``/var`` ↔ ``/private/var`` symlink means tmp_path may show
    # up under either depending on whether it was resolved (see
    # CLAUDE.md "macOS /var → /private/var symlink" lesson). Keep
    # ``/tmp/`` for the second (non-existent) entry below.
    raw_tmp = tempfile.gettempdir().rstrip(os.sep) + os.sep
    resolved_tmp = str(Path(tempfile.gettempdir()).resolve()).rstrip(os.sep) + os.sep
    monkeypatch.setattr(
        pw_routes,
        "_TMP_PATH_PREFIXES",
        (raw_tmp, resolved_tmp, "/tmp/"),
    )
    # tmp_path exists on disk and is under one of the tmp prefixes.
    # The entry's other fields don't matter for this assertion — the
    # filter rejects it on prefix alone, before existence check.
    journal_path = tmp_path / "journal.jsonl"
    _write_journal(
        journal_path,
        [
            _make_journal_dict(
                project_root=tmp_path,  # under /private/var/folders/.../pytest-of-...
                file_path="anything.md",
                after_sha256="aaa",
            ),
            # Also include a /tmp/ entry for the second prefix
            _make_journal_dict(
                project_root=Path("/tmp/test-fixture-never-created"),
                file_path="other.md",
                after_sha256="bbb",
            ),
        ],
    )

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()
    # Both should be filtered — first by prefix match (tmp_path under
    # pytest-of-), second by both prefix (/tmp/) AND nonexistence.
    assert len(body["pending"]) == 0
    assert body["summary"]["total_entries"] == 0


def test_system_tmp_prefix_returns_path_with_trailing_separator() -> None:
    """``_system_tmp_prefix()`` returns the platform tempdir with a
    trailing ``os.sep``. The trailing separator matters: without it,
    ``"/tmp/foo".startswith("/tmp")`` would match ``"/tmp"`` AND
    ``"/tmpfoo"`` — only the separator-terminated form is safe.

    The function is invoked at module-import time to populate the
    first entry of ``_TMP_PATH_PREFIXES``. This test exercises it
    directly so codecov sees the call.
    """
    import tempfile

    from attune.ops.routes import pending_writes as pw_routes

    result = pw_routes._system_tmp_prefix()
    assert result.endswith(os.sep)
    assert result.rstrip(os.sep) == tempfile.gettempdir().rstrip(os.sep)


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


def test_git_status_runs_once_per_project_root(
    tmp_project: Path,
    client_factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: N entries under one root spawn ONE git status.

    The pre-batch implementation ran `git status -- <file>` per entry
    (N+1 subprocess spawns on the event loop — the code-review High
    perf finding). Enrichment must batch to one call per distinct
    project root.
    """
    from attune.ops.routes import pending_writes as pw_routes

    names = ["a.md", "b.md", "c.md"]
    entries = []
    for name in names:
        target = tmp_project / name
        target.write_text("x\n", encoding="utf-8")
        entries.append(
            _make_journal_dict(
                project_root=tmp_project,
                file_path=name,
                after_sha256=pending_writes.compute_file_sha256(target),
            )
        )
    journal_path = tmp_path / "journal.jsonl"
    _write_journal(journal_path, entries)

    git_status_calls: list[list[str]] = []
    real_run = subprocess.run

    def counting_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and "status" in cmd:
            git_status_calls.append(cmd)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(pw_routes.subprocess, "run", counting_run)

    client = client_factory(journal_path=journal_path)
    body = client.get("/api/pending-writes").json()

    assert len(body["pending"]) == len(names)
    # All three files are untracked -> uncommitted.
    assert body["summary"]["uncommitted_count"] == len(names)
    assert len(git_status_calls) == 1
