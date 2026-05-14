"""Tests for the ops dashboard scope picker (ops-runner-tier2 Phase 2).

Covers four surfaces:
  * ``list_features()`` — reads ``.help/features.yaml`` with mtime cache.
  * ``POST /workflows/{name}/run`` with ``{"path": ...}`` body — path
    validation, no-path-workflow rejection, end-to-end subprocess wiring.
  * Template rendering — scope picker / ``n/a`` span both surface.
  * Runner.js — exports ``getScope`` and ``wireScopePickerToggle``.

Companion drift-guard tests live in
``tests/unit/ops/test_path_support_registry.py``.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")
pytest.importorskip("yaml")

from fastapi.testclient import TestClient  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from attune.ops import data  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import RunnerService  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

# ----------------------------------------------------------------------
# list_features() — file-parse + cache behavior
# ----------------------------------------------------------------------


def _write_features_yaml(root: Path, body: str) -> Path:
    help_dir = root / ".help"
    help_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = help_dir / "features.yaml"
    yaml_path.write_text(body, encoding="utf-8")
    return yaml_path


@pytest.fixture(autouse=True)
def _clear_features_cache():
    """Reset the module-level mtime cache between tests."""
    data._FEATURES_CACHE.clear()
    yield
    data._FEATURES_CACHE.clear()


def test_list_features_missing_file_returns_empty(tmp_path):
    """No ``.help/features.yaml`` → empty list, not an exception."""
    assert data.list_features(tmp_path) == []


def test_list_features_well_formed(tmp_path):
    _write_features_yaml(
        tmp_path,
        """
features:
  security-audit:
    description: Scan for vulns
    files:
      - src/attune/workflows/security_audit.py
      - src/attune/security/**
    tags: [security, audit]
  perf-audit:
    description: Performance scan
    files:
      - src/attune/workflows/perf_audit.py
    tags: [perf]
""",
    )
    features = data.list_features(tmp_path)
    assert [f.name for f in features] == ["perf-audit", "security-audit"]
    # security-audit prefers the /** glob → directory scope
    sec = next(f for f in features if f.name == "security-audit")
    assert sec.path == "src/attune/security"
    assert sec.description == "Scan for vulns"
    assert sec.tags == ("security", "audit")
    # perf-audit has no directory glob → first file as the scope
    perf = next(f for f in features if f.name == "perf-audit")
    assert perf.path == "src/attune/workflows/perf_audit.py"


def test_list_features_malformed_yaml(tmp_path):
    """Malformed YAML → empty list (fail-soft)."""
    _write_features_yaml(tmp_path, "features:\n  - this is\n    not: a [ mapping")
    assert data.list_features(tmp_path) == []


def test_list_features_features_key_not_mapping(tmp_path):
    """Top-level shape mismatch → empty list."""
    _write_features_yaml(tmp_path, "features:\n  - not_a_mapping\n")
    assert data.list_features(tmp_path) == []


def test_list_features_skips_glob_only_features(tmp_path):
    """A feature with only mid-name globs has no addressable scope (path=None)."""
    _write_features_yaml(
        tmp_path,
        """
features:
  code-quality:
    description: Mixed globs only
    files:
      - src/attune/workflows/code_review_*.py
    tags: [review]
""",
    )
    features = data.list_features(tmp_path)
    assert len(features) == 1
    assert features[0].path is None


def test_list_features_caches_by_mtime(tmp_path, monkeypatch):
    """Repeated calls hit the cache; modifying the file invalidates it."""
    yaml_path = _write_features_yaml(
        tmp_path,
        "features:\n  a:\n    description: A\n    files: [src/a.py]\n",
    )
    first = data.list_features(tmp_path)
    second = data.list_features(tmp_path)
    # Same list returned (cache hit — identity check would be too strict
    # but the content stays equal)
    assert first == second

    # Bump mtime + change content; should re-read.
    yaml_path.write_text(
        "features:\n  b:\n    description: B\n    files: [src/b.py]\n",
        encoding="utf-8",
    )
    # Force mtime change in case the test ran within the same nanosecond
    import os
    import time

    new_mtime = yaml_path.stat().st_mtime + 1
    os.utime(yaml_path, (new_mtime, new_mtime))
    time.sleep(0.001)
    third = data.list_features(tmp_path)
    assert [f.name for f in third] == ["b"]


# ----------------------------------------------------------------------
# POST /workflows/{name}/run — path body, validation, rejection
# ----------------------------------------------------------------------


def _echo_cmd(workflow: str) -> tuple[str, ...]:
    script = (
        "import sys; print('start ' + sys.argv[1]); "
        "[print(a) for a in sys.argv[2:]]; sys.exit(0)"
    )
    return (sys.executable, "-c", script, workflow)


def _make_app(tmp_path, monkeypatch, *, allow_run=True):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        allow_run=allow_run,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=_echo_cmd)
    app = create_app(config, runner=runner)
    return app, runner


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
async def test_run_with_path_threads_into_subprocess(tmp_path, monkeypatch):
    """POST with ``{"path": "..."}`` adds ``--path <path>`` to the cmd."""
    scope_dir = tmp_path / "src" / "feature"
    scope_dir.mkdir(parents=True)
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/workflows/security-audit/run",
            json={"path": str(scope_dir)},
        )
        assert resp.status_code == 201, resp.text
        run = await _wait_terminal(runner, resp.json()["run_id"])
    assert run.status == "completed"
    assert run.path is not None
    # The fixture command echoes its argv. The first line is the
    # shell-style command preamble; later lines come from the script.
    # The validated absolute path appears in the recorded command line.
    cmd_line = run.lines[0]
    assert "--path" in cmd_line
    assert str(scope_dir.resolve()) in cmd_line


@pytest.mark.asyncio
async def test_run_without_body_runs_project_wide(tmp_path, monkeypatch):
    """No body → no ``--path`` flag, no error."""
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/workflows/security-audit/run")
        assert resp.status_code == 201, resp.text
        run = await _wait_terminal(runner, resp.json()["run_id"])
    assert run.path is None
    assert "--path" not in run.lines[0]


def test_run_rejects_invalid_path_traversal(tmp_path, monkeypatch):
    """Path outside project_root → 400."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            json={"path": "/etc/passwd"},
        )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "invalid path" in detail.lower() or "system directory" in detail.lower()


def test_run_rejects_path_outside_project_root(tmp_path, monkeypatch):
    """A real path outside project_root is rejected via allowed_dir check."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    # Pick a sibling dir that definitely exists but is outside project_root
    outsider = tmp_path.parent
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            json={"path": str(outsider)},
        )
    assert resp.status_code == 400


def test_run_rejects_path_for_no_path_workflow(tmp_path, monkeypatch):
    """Workflow not in PATH_ARG_REGISTRY → 400 when path is provided.

    We simulate the no-path case by patching the registry to remove
    ``security-audit`` for the duration of the test. The validation
    happens BEFORE registry lookup of the actual workflow, so the
    runner never gets the call.
    """
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    monkeypatch.delitem(data.PATH_ARG_REGISTRY, "security-audit", raising=False)
    scope_dir = tmp_path / "src"
    scope_dir.mkdir()
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            json={"path": str(scope_dir)},
        )
    assert resp.status_code == 400
    assert "does not accept a path" in resp.json()["detail"]


def test_run_rejects_non_string_path(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            json={"path": 12345},
        )
    assert resp.status_code == 400


def test_run_rejects_non_object_body(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            content=b"[1,2,3]",
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400


def test_run_rejects_malformed_json(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            content=b"not valid json {",
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400


def test_run_treats_empty_path_as_project_wide(tmp_path, monkeypatch):
    """Empty-string path → same as omitted (project-wide). The picker's
    "Project-wide" option submits ``""`` if the JS isn't filtering."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    with TestClient(app) as client:
        resp = client.post(
            "/workflows/security-audit/run",
            json={"path": ""},
        )
    assert resp.status_code == 201


# ----------------------------------------------------------------------
# Template rendering — workflows.html scope picker
# ----------------------------------------------------------------------


def test_workflows_page_renders_scope_picker_for_path_workflow(tmp_path, monkeypatch):
    """A workflow in PATH_ARG_REGISTRY gets a ``<select data-scope-picker>``."""
    _write_features_yaml(
        tmp_path,
        """
features:
  security-audit:
    description: Scan
    files: [src/attune/security/**]
    tags: [security]
""",
    )
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    body = resp.text
    assert "data-scope-picker" in body
    assert "Project-wide" in body
    assert "Custom path…" in body
    assert "data-scope-custom" in body
    # The feature dropdown option appears
    assert ">security-audit<" in body


def test_workflows_page_renders_n_a_for_no_path_workflow(tmp_path, monkeypatch):
    """A workflow absent from PATH_ARG_REGISTRY shows a ``.scope-na`` span."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True)
    # Remove one workflow so it's missing from the registry
    monkeypatch.delitem(data.PATH_ARG_REGISTRY, "security-audit", raising=False)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    # The "n/a" span renders for the missing workflow
    assert "scope-na" in resp.text


def test_workflows_page_no_scope_column_when_read_only(tmp_path, monkeypatch):
    """``--read-only`` mode: no Scope header, no picker markup."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=False)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    assert "data-scope-picker" not in resp.text
    assert ">Scope<" not in resp.text


# ----------------------------------------------------------------------
# runner.js — scope helpers exported
# ----------------------------------------------------------------------


def test_runner_js_exports_get_scope_and_toggle():
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
    # Both helpers exist as functions
    assert "function getScope(" in text
    assert "function wireScopePickerToggle(" in text
    # Both are exposed on the test surface
    assert "getScope: getScope" in text
    assert "wireScopePickerToggle: wireScopePickerToggle" in text
    # The DOMContentLoaded handler wires the toggle
    assert "wireScopePickerToggle" in text
    # POST body construction uses path key
    assert "path: scope" in text or '"path": scope' in text


def test_runner_js_default_post_is_no_body():
    """When no scope is set, the POST should not include a body so
    existing servers (and the test suite's no-body tests) keep working."""
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
    # The code must guard body assignment behind a scope != null check
    assert "scope !== null" in text
