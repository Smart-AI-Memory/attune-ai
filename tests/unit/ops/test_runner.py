"""Tests for the workflow runner (RunnerService + routes).

These exercise the subprocess pipeline with a portable command (the python
interpreter running a tiny inline script), so they're deterministic on every OS.

The completion-dependent tests run async (with httpx.AsyncClient) because
TestClient tears down the event loop after each request, which would orphan
the subprocess task spawned by RunnerService.
"""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import RunnerService  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _echo_cmd(workflow: str) -> tuple[str, ...]:
    """Two stdout lines, exits 0. Portable across linux/mac/windows."""
    script = f"import sys; print('start {workflow}'); " f"print('end {workflow}'); sys.exit(0)"
    return (sys.executable, "-c", script)


def _fail_cmd(workflow: str) -> tuple[str, ...]:
    script = f"import sys; print('boom {workflow}'); sys.exit(1)"
    return (sys.executable, "-c", script)


def _missing_cmd(_workflow: str) -> tuple[str, ...]:
    return ("/nonexistent/binary/that/should/not/exist",)


def _make_app(tmp_path, monkeypatch, *, allow_run, command_builder, executor=None):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(project_root=tmp_path, allow_run=allow_run)
    runner = RunnerService(command_builder=command_builder, executor=executor)
    app = create_app(config, runner=runner)
    return app, runner


async def _wait_terminal(runner: RunnerService, run_id: str, *, timeout: float = 5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        run = runner.get(run_id)
        assert run is not None
        if run.is_terminal:
            return run
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail(f"run {run_id} did not finish within {timeout}s")
        await asyncio.sleep(0.02)


# --- sync (TestClient) tests: page rendering + 403/409/404 don't need lifecycle


def test_run_disabled_returns_403(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=False, command_builder=_echo_cmd)
    with TestClient(app) as client:
        resp = client.post("/workflows/code-review/run")
    assert resp.status_code == 403
    assert "allow-run" in resp.json()["detail"]


def test_get_run_returns_404_for_unknown(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    with TestClient(app) as client:
        resp = client.get("/runs/nope")
    assert resp.status_code == 404


def test_workflows_page_shows_run_buttons_when_enabled(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    assert "data-run-button" in resp.text


def test_workflows_page_hides_run_buttons_when_disabled(tmp_path, monkeypatch):
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=False, command_builder=_echo_cmd)
    with TestClient(app) as client:
        resp = client.get("/workflows")
    assert resp.status_code == 200
    assert "data-run-button" not in resp.text
    assert "Read-only mode" in resp.text


def test_run_busy_returns_409(tmp_path, monkeypatch):
    """Second POST while a run is in flight returns 409."""

    async def slow_executor(run):
        from datetime import datetime, timezone

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await asyncio.sleep(0.5)
        run.mark_done(0)

    app, _ = _make_app(
        tmp_path,
        monkeypatch,
        allow_run=True,
        command_builder=lambda _: ("noop",),
        executor=slow_executor,
    )
    with TestClient(app) as client:
        first = client.post("/workflows/x/run")
        assert first.status_code == 201
        second = client.post("/workflows/x/run")
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["current_run_id"] == first.json()["run_id"]


# --- async tests: real subprocess lifecycle in a single loop


@pytest.mark.asyncio
async def test_run_happy_path(tmp_path, monkeypatch):
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/workflows/code-review/run")
        assert resp.status_code == 201
        body = resp.json()
        assert body["stream_url"] == f"/runs/{body['run_id']}/stream"

        run = await _wait_terminal(runner, body["run_id"])
        assert run.status == "completed"
        assert run.exit_code == 0
        assert any("start code-review" in ln for ln in run.lines)
        assert any("end code-review" in ln for ln in run.lines)


@pytest.mark.asyncio
async def test_run_failed_status_after_nonzero_exit(tmp_path, monkeypatch):
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_fail_cmd)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/workflows/x/run")
        assert resp.status_code == 201
        run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.status == "failed"
        assert run.exit_code == 1


@pytest.mark.asyncio
async def test_run_missing_binary_marks_failed(tmp_path, monkeypatch):
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_missing_cmd)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/workflows/x/run")
        assert resp.status_code == 201
        run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.status == "failed"
        assert any("runner error" in ln for ln in run.lines)


@pytest.mark.asyncio
async def test_stream_replays_buffered_lines(tmp_path, monkeypatch):
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        started = (await client.post("/workflows/code-review/run")).json()
        await _wait_terminal(runner, started["run_id"])

        # Connect AFTER completion: stream replays buffered lines + done.
        async with client.stream("GET", started["stream_url"]) as resp:
            assert resp.status_code == 200
            events: list[tuple[str, str]] = []
            current_event = None
            async for raw in resp.aiter_lines():
                if not raw:
                    current_event = None
                    continue
                if raw.startswith("event: "):
                    current_event = raw[len("event: ") :]
                elif raw.startswith("data: ") and current_event is not None:
                    events.append((current_event, raw[len("data: ") :]))
                    if current_event == "done":
                        break

    kinds = [k for k, _ in events]
    assert "line" in kinds
    assert kinds[-1] == "done"
    # Every payload must be JSON-decodable so the browser can JSON.parse it
    line_payloads = [json.loads(data) for kind, data in events if kind == "line"]
    assert any("start code-review" in s for s in line_payloads if isinstance(s, str))
    done_payload = json.loads(events[-1][1])
    assert done_payload["status"] == "completed"
    assert done_payload["exit_code"] == 0
