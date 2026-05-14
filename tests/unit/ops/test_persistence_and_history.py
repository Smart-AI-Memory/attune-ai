"""Tests for ops-runner-tier2 Phase 3 (persistence + history API) and
Phase 4 (clickable workflow-name pills on the run-view page).

Phase 3 surfaces:
  * ``Run.to_record`` / ``Run.from_record`` round-trip.
  * Disk persistence: file written on completion, log truncation at the
    200 KB budget, atomic-rename safety, malformed-name rejection.
  * Pruning of run files older than the retention window.
  * ``/api/runs/{workflow}`` listing (combines in-memory + on-disk).
  * ``/api/runs/{workflow}/{run_id}`` detail endpoint.
  * Read-only mode disables persistence entirely.

Phase 4 surfaces:
  * ``run_view.js`` exists and is referenced from ``run_view.html``.
  * Run-view template injects the JSON config block.
  * ``run_view.html`` includes the ``.chained-from`` slot + recent-runs strip.
  * ``run_view.js`` exports the pill-click + chained-from helpers.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")
pytest.importorskip("yaml")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import (  # noqa: E402
    Run,
    RunnerService,
    _list_persisted_runs,
    _load_run_record,
    _persist_run,
    _truncate_lines_for_persist,
    prune_old_runs,
)
from attune.ops.server import create_app  # noqa: E402

# ---------------------------------------------------------------------------
# Run.to_record / from_record round-trip
# ---------------------------------------------------------------------------


def test_run_to_record_round_trip():
    original = Run(
        id="abc12345",
        workflow="security-audit",
        status="completed",
        exit_code=0,
        path="/tmp/scope",
        command=["py", "-m", "attune", "workflow", "run", "security-audit"],
        lines=["line one", "line two", "line three"],
    )
    record = original.to_record()
    restored = Run.from_record(record)
    assert restored.id == original.id
    assert restored.workflow == original.workflow
    assert restored.status == original.status
    assert restored.exit_code == original.exit_code
    assert restored.path == original.path
    assert restored.command == original.command
    assert restored.lines == original.lines


def test_from_record_tolerates_missing_fields():
    """A minimal record (id + workflow) still produces a usable Run."""
    restored = Run.from_record({"id": "x", "workflow": "code-review"})
    assert restored.id == "x"
    assert restored.workflow == "code-review"
    # Defaults fire for everything not in the record
    assert restored.exit_code is None
    assert restored.path is None
    assert restored.command is None
    assert restored.lines == []


def test_from_record_bad_status_defaults_to_completed():
    """An unknown status string falls back to 'completed' rather than crashing."""
    restored = Run.from_record({"id": "y", "workflow": "code-review", "status": "exploded"})
    assert restored.status == "completed"


# ---------------------------------------------------------------------------
# Log truncation
# ---------------------------------------------------------------------------


def test_truncate_short_log_is_passthrough():
    lines = ["one", "two", "three"]
    assert _truncate_lines_for_persist(lines) == lines


def test_truncate_long_log_appends_marker(monkeypatch):
    # Build a payload that comfortably exceeds the 200 KB cap.
    big_line = "x" * 1_000  # 1 KB per line; 250 lines → ~250 KB
    lines = [big_line] * 250
    out = _truncate_lines_for_persist(lines)
    assert len(out) < len(lines)
    assert out[-1].startswith("<TRUNCATED — ")
    assert out[-1].endswith(" bytes more>")


# ---------------------------------------------------------------------------
# _persist_run write path
# ---------------------------------------------------------------------------


def test_persist_run_writes_json(tmp_path):
    runs_dir = tmp_path / "runs"
    run = Run(
        id="aaaaaaaaaaaa",
        workflow="security-audit",
        status="completed",
        exit_code=0,
        path="/scope",
        command=["py", "-c", "print(1)"],
        lines=["preamble", "stdout line"],
    )
    dest = _persist_run(run, runs_dir)
    assert dest is not None
    assert dest.is_file()
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["id"] == run.id
    assert data["workflow"] == run.workflow
    assert data["path"] == "/scope"
    assert data["lines"] == ["preamble", "stdout line"]
    # ``persisted_at`` is added by the writer
    assert "persisted_at" in data


def test_persist_run_rejects_bad_workflow_name(tmp_path):
    run = Run(id="abc123", workflow="bad..name", status="completed")
    dest = _persist_run(run, tmp_path / "runs")
    assert dest is None
    assert not (tmp_path / "runs").exists()


def test_persist_run_rejects_bad_run_id(tmp_path):
    run = Run(id="../etc/passwd", workflow="security-audit", status="completed")
    dest = _persist_run(run, tmp_path / "runs")
    assert dest is None


def test_persist_run_truncates_long_log(tmp_path):
    runs_dir = tmp_path / "runs"
    big = "x" * 1_500  # 1.5 KB per line
    lines = [big] * 200  # ~300 KB
    run = Run(
        id="bbbbbbbbbbbb",
        workflow="security-audit",
        status="completed",
        lines=lines,
    )
    dest = _persist_run(run, runs_dir)
    assert dest is not None
    data = json.loads(dest.read_text(encoding="utf-8"))
    # The truncation marker is the last line
    assert any(line.startswith("<TRUNCATED — ") for line in data["lines"])
    assert len(data["lines"]) < len(lines)


# ---------------------------------------------------------------------------
# RunnerService end-to-end persistence (uses real subprocess via echo cmd)
# ---------------------------------------------------------------------------


def _echo_cmd(workflow: str) -> tuple[str, ...]:
    script = "import sys; print('start ' + sys.argv[1]); print('end ' + sys.argv[1]); sys.exit(0)"
    return (sys.executable, "-c", script, workflow)


async def _wait_terminal(runner, run_id, *, timeout=5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        run = runner.get(run_id)
        assert run is not None
        if run.is_terminal:
            return run
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail(f"run {run_id} did not finish in {timeout}s")
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_runner_writes_record_on_completion(tmp_path):
    runs_dir = tmp_path / "runs"
    svc = RunnerService(command_builder=_echo_cmd, persistence_dir=runs_dir)
    run = await svc.start("security-audit", path="/scope/dir")
    await _wait_terminal(svc, run.id)

    json_path = runs_dir / "security-audit" / f"{run.id}.json"
    assert json_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["path"] == "/scope/dir"
    assert data["command"][-2:] == ["--path", "/scope/dir"]


@pytest.mark.asyncio
async def test_runner_skips_persistence_when_dir_is_none(tmp_path):
    """No persistence_dir → no disk writes (read-only mode)."""
    runs_dir = tmp_path / "runs"
    svc = RunnerService(command_builder=_echo_cmd, persistence_dir=None)
    run = await svc.start("security-audit")
    await _wait_terminal(svc, run.id)
    assert not runs_dir.exists()


# ---------------------------------------------------------------------------
# prune_old_runs
# ---------------------------------------------------------------------------


def test_prune_old_runs_deletes_files_past_cutoff(tmp_path):
    runs_dir = tmp_path / "runs"
    workflow_dir = runs_dir / "security-audit"
    workflow_dir.mkdir(parents=True)
    fresh = workflow_dir / "fresh111111.json"
    stale = workflow_dir / "stale222222.json"
    fresh.write_text('{"id": "fresh"}', encoding="utf-8")
    stale.write_text('{"id": "stale"}', encoding="utf-8")
    # Backdate stale to 60 days ago
    past = time.time() - 60 * 86_400
    os.utime(stale, (past, past))

    deleted = prune_old_runs(runs_dir, days=30)
    assert deleted == 1
    assert fresh.is_file()
    assert not stale.exists()


def test_prune_old_runs_zero_days_disables_sweep(tmp_path):
    workflow_dir = tmp_path / "runs" / "x"
    workflow_dir.mkdir(parents=True)
    old = workflow_dir / "abc123.json"
    old.write_text("{}", encoding="utf-8")
    os.utime(old, (0, 0))  # epoch
    assert prune_old_runs(tmp_path / "runs", days=0) == 0
    assert old.is_file()


def test_prune_old_runs_missing_dir_is_noop(tmp_path):
    assert prune_old_runs(tmp_path / "does-not-exist", days=30) == 0


# ---------------------------------------------------------------------------
# _list_persisted_runs ordering
# ---------------------------------------------------------------------------


def test_list_persisted_runs_returns_newest_first(tmp_path):
    runs_dir = tmp_path / "runs"
    wf_dir = runs_dir / "security-audit"
    wf_dir.mkdir(parents=True)
    # Write 3 records and set mtimes
    for ix, run_id in enumerate(["aaaaaa", "bbbbbb", "cccccc"]):
        record = {
            "id": run_id,
            "workflow": "security-audit",
            "status": "completed",
            "lines": [],
        }
        path = wf_dir / f"{run_id}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        mtime = time.time() - (3 - ix) * 100  # cccccc newest
        os.utime(path, (mtime, mtime))

    records = _list_persisted_runs(runs_dir, "security-audit", limit=20)
    ids = [r["id"] for r in records]
    assert ids == ["cccccc", "bbbbbb", "aaaaaa"]


def test_list_persisted_runs_rejects_bad_workflow(tmp_path):
    assert _list_persisted_runs(tmp_path, "BAD_NAME") == []


def test_load_run_record_rejects_bad_run_id(tmp_path):
    runs_dir = tmp_path / "runs"
    (runs_dir / "x").mkdir(parents=True)
    (runs_dir / "x" / "abc.json").write_text("{}", encoding="utf-8")
    assert _load_run_record(runs_dir, "x", "../etc/passwd") is None


# ---------------------------------------------------------------------------
# /api/runs/{workflow} endpoints
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch, *, allow_run=True):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        allow_run=allow_run,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(
        command_builder=_echo_cmd,
        persistence_dir=config.runs_dir if allow_run else None,
    )
    app = create_app(config, runner=runner)
    return app, runner, config


def test_list_runs_rejects_bad_workflow_name(tmp_path, monkeypatch):
    app, _, _ = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/runs/BAD..name")
    assert resp.status_code == 400


def test_list_runs_empty_when_no_history(tmp_path, monkeypatch):
    app, _, _ = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit")
    assert resp.status_code == 200
    assert resp.json() == {"workflow": "security-audit", "runs": []}


@pytest.mark.asyncio
async def test_list_runs_combines_in_memory_and_disk(tmp_path, monkeypatch):
    app, runner, config = _make_app(tmp_path, monkeypatch)
    # One run via the runner (writes to disk, also in memory)
    run = await runner.start("security-audit", path="/scope")
    await _wait_terminal(runner, run.id)

    # Plant a second disk-only record with a fixed older id
    wf_dir = config.runs_dir / "security-audit"
    wf_dir.mkdir(parents=True, exist_ok=True)
    plant_id = "ddeeff112233"
    record = {
        "id": plant_id,
        "workflow": "security-audit",
        "status": "completed",
        "exit_code": 0,
        "started_at": "2026-05-13T12:00:00+00:00",
        "completed_at": "2026-05-13T12:00:05+00:00",
        "lines": ["older"],
    }
    (wf_dir / f"{plant_id}.json").write_text(json.dumps(record), encoding="utf-8")

    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit")
    assert resp.status_code == 200
    body = resp.json()
    ids = {r["id"] for r in body["runs"]}
    assert run.id in ids
    assert plant_id in ids
    # List responses don't include the full log buffer
    for r in body["runs"]:
        assert "lines" not in r


def test_get_run_record_rejects_path_traversal(tmp_path, monkeypatch):
    app, _, _ = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit/..%2Fetc%2Fpasswd")
    # Either 400 from the regex check, or 404 from the path miss — both
    # are acceptable as long as the response is non-200 and doesn't
    # leak the file.
    assert resp.status_code in (400, 404)


def test_get_run_record_returns_404_for_missing(tmp_path, monkeypatch):
    app, _, _ = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit/aaaaaaaaaaaa")
    assert resp.status_code == 404
    # API path → JSON body, not HTML
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["detail"] == "run not found"


@pytest.mark.asyncio
async def test_get_run_record_returns_full_log(tmp_path, monkeypatch):
    app, runner, _ = _make_app(tmp_path, monkeypatch)
    run = await runner.start("security-audit")
    await _wait_terminal(runner, run.id)
    with TestClient(app) as client:
        resp = client.get(f"/api/runs/security-audit/{run.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == run.id
    assert "lines" in body
    assert len(body["lines"]) >= 2  # preamble + stdout


def test_read_only_mode_disables_persistence(tmp_path, monkeypatch):
    """`--read-only` (allow_run=False) → no persistence_dir → no writes
    + the runs API works on empty data (no crash on missing runs_dir)."""
    app, _, config = _make_app(tmp_path, monkeypatch, allow_run=False)
    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit")
    assert resp.status_code == 200
    assert resp.json()["runs"] == []
    # Even the runs_dir itself shouldn't have been created
    assert not config.runs_dir.exists()


# ---------------------------------------------------------------------------
# Template + JS surface for Phase 3 / Phase 4
# ---------------------------------------------------------------------------


def test_workflows_page_includes_recent_runs_strip(tmp_path, monkeypatch):
    app, _, _ = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    assert "data-recent-runs" in resp.text


def test_workflows_page_loads_runner_js_in_read_only_too(tmp_path, monkeypatch):
    """recent-runs strip needs runner.js loaded even in read-only mode."""
    app, _, _ = _make_app(tmp_path, monkeypatch, allow_run=False)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    assert "/static/js/runner.js" in resp.text


@pytest.mark.asyncio
async def test_run_view_page_loads_both_js_files(tmp_path, monkeypatch):
    """run_view.html references runner.js + run_view.js + injects JSON config."""
    app, runner, _ = _make_app(tmp_path, monkeypatch)
    run = await runner.start("security-audit", path="/scope")
    await _wait_terminal(runner, run.id)
    with TestClient(app) as client:
        resp = client.get(f"/runs/{run.id}/view")
    assert resp.status_code == 200
    body = resp.text
    assert "/static/js/runner.js" in body
    assert "/static/js/run_view.js" in body
    assert 'id="run-view-data"' in body
    assert "chained-from" in body
    assert "data-recent-runs" in body


def test_runner_js_exports_recent_runs_helpers():
    js_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "attune"
        / "ops"
        / "static"
        / "js"
        / "runner.js"
    )
    text = js_path.read_text(encoding="utf-8")
    assert "function setupRecentRuns(" in text
    assert "function renderRecentRunsInto(" in text
    assert "setupRecentRuns: setupRecentRuns" in text
    assert "recent-run-chip" in text


def test_run_view_js_exists_and_exposes_helpers():
    """Phase 4.1: extracted file is reachable + exports pill + badge helpers."""
    js_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "attune"
        / "ops"
        / "static"
        / "js"
        / "run_view.js"
    )
    assert js_path.is_file()
    text = js_path.read_text(encoding="utf-8")
    assert "function handlePillClick(" in text
    assert "function renderChainedFromBadge(" in text
    assert "function pillTargetFromEvent(" in text
    assert "window.__attuneRunView" in text
    # Phase 4.4: read-only fall-through goes through showInlineError
    assert "Read-only mode" in text
    # Phase 4.2: 409 surfaces inline, doesn't navigate
    assert "current_run_id" in text


def test_run_view_js_validates_from_param():
    """``?from=`` must match the workflow-name regex; junk is dropped."""
    js_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "attune"
        / "ops"
        / "static"
        / "js"
        / "run_view.js"
    )
    text = js_path.read_text(encoding="utf-8")
    # The regex literal lives in renderChainedFromBadge
    assert "/^[a-z][a-z0-9-]+$/" in text


@pytest.mark.asyncio
async def test_run_view_data_block_contains_allow_run_and_path(tmp_path, monkeypatch):
    app, runner, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    run = await runner.start("security-audit", path="/scope/value")
    await _wait_terminal(runner, run.id)
    with TestClient(app) as client:
        resp = client.get(f"/runs/{run.id}/view")
    body = resp.text
    # Extract the JSON block content
    start = body.index('id="run-view-data"')
    block_open = body.index(">", start) + 1
    block_close = body.index("</script>", block_open)
    block = body[block_open:block_close].strip()
    parsed = json.loads(block)
    assert parsed["allow_run"] is True
    assert parsed["path"] == "/scope/value"
    assert parsed["workflow"] == "security-audit"


@pytest.mark.asyncio
async def test_run_view_data_block_allow_run_false_in_read_only(tmp_path, monkeypatch):
    app, runner, _ = _make_app(tmp_path, monkeypatch, allow_run=False)
    run = await runner.start("security-audit")
    await _wait_terminal(runner, run.id)
    with TestClient(app) as client:
        resp = client.get(f"/runs/{run.id}/view")
    body = resp.text
    start = body.index('id="run-view-data"')
    block_open = body.index(">", start) + 1
    block_close = body.index("</script>", block_open)
    block = body[block_open:block_close].strip()
    parsed = json.loads(block)
    assert parsed["allow_run"] is False
