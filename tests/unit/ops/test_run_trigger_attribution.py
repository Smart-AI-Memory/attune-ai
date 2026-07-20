"""Rec-click trigger attribution (run-record-corpus RC-3 follow-up).

The dashboard stamps recommendation-launched runs with
``trigger="attune-rec"``: client rec surfaces send it in the run POST,
the route validates it, ``RunnerService`` threads it onto the ``Run``,
and ``_execute`` exports it as ``ATTUNE_RUN_TRIGGER`` so the workflow
subprocess's own run record carries the attribution. Manual runs send
nothing and keep resolving to ``manual``.
"""

import asyncio
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from attune.models.telemetry.run_context import TRIGGER_ENV
from attune.ops.config import build_config
from attune.ops.runner import Run, RunnerService
from attune.ops.server import create_app

JS_DIR = Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js"


def _echo_trigger_cmd(workflow: str) -> tuple[str, ...]:
    """Subprocess that prints the trigger env var it received."""
    script = (
        "import os; "
        f"print('WORKFLOW={workflow}'); "
        f"print('ENV_TRIGGER=' + os.environ.get('{TRIGGER_ENV}', 'MISSING'))"
    )
    return (sys.executable, "-c", script)


def _make_app(tmp_path, monkeypatch, *, allow_run=True):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        allow_run=allow_run,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=_echo_trigger_cmd)
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


class TestRoute:
    @pytest.mark.asyncio
    async def test_rec_trigger_reaches_subprocess_env(self, tmp_path, monkeypatch):
        """attune-rec threads route → Run → ATTUNE_RUN_TRIGGER in the child."""
        app, runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/workflows/code-review/run", json={"trigger": "attune-rec"})
            assert resp.status_code == 201
            run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.trigger == "attune-rec"
        assert any("ENV_TRIGGER=attune-rec" in ln for ln in run.lines)

    @pytest.mark.asyncio
    async def test_no_trigger_leaves_env_unset(self, tmp_path, monkeypatch):
        """A body-less POST exports nothing — the child resolves manual."""
        app, runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/workflows/code-review/run")
            assert resp.status_code == 201
            run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.trigger is None
        assert any("ENV_TRIGGER=MISSING" in ln for ln in run.lines)

    @pytest.mark.asyncio
    async def test_junk_trigger_is_rejected(self, tmp_path, monkeypatch):
        app, _runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/workflows/code-review/run", json={"trigger": "cron"})
        assert resp.status_code == 400
        assert "trigger" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_attune_heal_reaches_subprocess_env(self, tmp_path, monkeypatch):
        """Diagnostic runs stamp attune-heal end-to-end (adv-debugging RR-2)."""
        app, runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/workflows/code-review/run", json={"trigger": "attune-heal"})
            assert resp.status_code == 201
            run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.trigger == "attune-heal"
        assert any("ENV_TRIGGER=attune-heal" in ln for ln in run.lines)

    @pytest.mark.asyncio
    async def test_explicit_manual_is_accepted(self, tmp_path, monkeypatch):
        app, runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/workflows/code-review/run", json={"trigger": "manual"})
            assert resp.status_code == 201
            run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.trigger == "manual"
        assert any("ENV_TRIGGER=manual" in ln for ln in run.lines)


class TestRunRecordRoundTrip:
    def test_to_dict_carries_trigger(self):
        run = Run(id="abc123def456", workflow="code-review", trigger="attune-rec")
        assert run.to_dict()["trigger"] == "attune-rec"

    def test_from_record_restores_trigger(self):
        run = Run(id="abc123def456", workflow="code-review", trigger="attune-rec")
        record = run.to_record()
        restored = Run.from_record(record)
        assert restored.trigger == "attune-rec"

    def test_from_record_tolerates_pre_rc3_records(self):
        run = Run(id="abc123def456", workflow="code-review")
        record = run.to_record()
        record.pop("trigger", None)  # pre-RC-3 persisted record
        assert Run.from_record(record).trigger is None


class TestClientStamps:
    """Source-level guard: every rec surface sends the stamp; the manual
    Run button does not (matches the repo's JS-content test style)."""

    def test_rec_surfaces_send_attune_rec(self):
        text = (JS_DIR / "run_view.js").read_text(encoding="utf-8")
        assert text.count('trigger: "attune-rec"') == 3

    def test_manual_run_button_sends_no_trigger(self):
        text = (JS_DIR / "runner.js").read_text(encoding="utf-8")
        assert "attune-rec" not in text
