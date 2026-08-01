"""Coverage-gap tests for ``attune.ops.routes.runs_history``.

The broader Phase 3 surface (round trips, persistence, pruning,
combined listings, 404 handling for missing runs, path-traversal
rejection) is already exercised in ``test_persistence_and_history.py``.
This file targets the four lines that survived that suite:

  * ``list_runs`` skipping an in-memory run that belongs to a
    *different* workflow (the ``continue`` branch).
  * ``get_run_record`` rejecting an invalid ``workflow`` path segment.
  * ``get_run_record`` rejecting an invalid ``run_id`` path segment.
  * ``get_run_record`` returning a record that exists on disk but has
    no in-memory counterpart (the disk-only success path).
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")
pytest.importorskip("yaml")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import Run, RunnerService  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _echo_cmd(workflow: str) -> tuple[str, ...]:
    import sys

    return (sys.executable, "-c", "print(1)", workflow)


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


def _write_disk_record(runs_dir, workflow: str, run_id: str, **fields) -> None:
    workflow_dir = runs_dir / workflow
    workflow_dir.mkdir(parents=True, exist_ok=True)
    record = {"id": run_id, "workflow": workflow, "status": "completed", **fields}
    (workflow_dir / f"{run_id}.json").write_text(json.dumps(record), encoding="utf-8")


# ---------------------------------------------------------------------------
# list_runs — in-memory run from a DIFFERENT workflow is skipped (line 64)
# ---------------------------------------------------------------------------


def test_list_runs_skips_in_memory_run_from_other_workflow(tmp_path, monkeypatch):
    app, runner, _config = _make_app(tmp_path, monkeypatch)
    # Two in-memory runs for two different workflows, planted directly
    # (no subprocess needed — recent() just reads the dict).
    other = Run(id="other0000001", workflow="code-review", status="completed")
    target = Run(id="target000001", workflow="security-audit", status="completed")
    runner._runs[other.id] = other
    runner._runs[target.id] = target

    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit")

    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()["runs"]}
    assert target.id in ids
    assert other.id not in ids


# ---------------------------------------------------------------------------
# get_run_record — invalid workflow name on the detail endpoint (line 91)
# ---------------------------------------------------------------------------


def test_get_run_record_rejects_bad_workflow_name(tmp_path, monkeypatch):
    app, _runner, _config = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.get("/api/runs/BAD_NAME/aaaaaaaaaaaa")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid workflow name"


# ---------------------------------------------------------------------------
# get_run_record — invalid run id shape on the detail endpoint (line 93)
# ---------------------------------------------------------------------------


def test_get_run_record_rejects_bad_run_id_shape(tmp_path, monkeypatch):
    app, _runner, _config = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        # Valid workflow name, but the run id has uppercase letters —
        # fails ``_RUN_ID_RE`` (``^[a-f0-9]{1,64}$``) without tripping
        # any routing-level ambiguity (no slashes to URL-decode).
        resp = client.get("/api/runs/security-audit/NOTVALIDHEX")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid run id"


# ---------------------------------------------------------------------------
# get_run_record — disk-only record (no in-memory counterpart) returns
# successfully through the JSON-response fallback path (line 106).
# ---------------------------------------------------------------------------


def test_get_run_record_returns_disk_only_record(tmp_path, monkeypatch):
    app, _runner, config = _make_app(tmp_path, monkeypatch)
    _write_disk_record(
        config.runs_dir,
        "security-audit",
        "d15c0e000001",
        exit_code=0,
        lines=["from disk"],
    )

    with TestClient(app) as client:
        resp = client.get("/api/runs/security-audit/d15c0e000001")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "d15c0e000001"
    assert body["workflow"] == "security-audit"
    assert body["lines"] == ["from disk"]
