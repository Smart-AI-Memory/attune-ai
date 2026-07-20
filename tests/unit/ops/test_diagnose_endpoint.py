"""On-demand diagnosis endpoint tests (advanced-debugging-plugin T5).

POST /runs/{run_id}/diagnose: validation, idempotency, and the
attune-heal dispatch — plus source-level guards that the run-view
button never auto-starts.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from attune.models import DiagnosisRecord
from attune.models.telemetry.run_context import TRIGGER_ENV
from attune.models.telemetry.storage import TelemetryStore
from attune.ops.config import build_config
from attune.ops.runner import RunnerService, _default_command
from attune.ops.server import create_app

JS_DIR = Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "static" / "js"
TPL_DIR = Path(__file__).resolve().parents[3] / "src" / "attune" / "ops" / "templates"


def _fail_cmd(workflow: str) -> tuple[str, ...]:
    script = f"import sys; print('boom {workflow}'); sys.exit(1)"
    return (sys.executable, "-c", script)


def _echo_dispatch_cmd(workflow: str) -> tuple[str, ...]:
    """Print trigger env + trailing argv so dispatch is observable."""
    script = (
        "import os, sys; "
        f"print('DISPATCH workflow={workflow}'); "
        f"print('DISPATCH trigger=' + os.environ.get('{TRIGGER_ENV}', 'MISSING')); "
        "print('DISPATCH args=' + ' '.join(sys.argv[1:]))"
    )
    return (sys.executable, "-c", script)


def _make_app(tmp_path, monkeypatch, *, command_builder=_fail_cmd):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        allow_run=True,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=command_builder)
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


class TestValidation:
    @pytest.mark.asyncio
    async def test_unknown_run_is_404(self, tmp_path, monkeypatch):
        app, _runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/runs/deadbeef0000/diagnose")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_failed_run_is_400(self, tmp_path, monkeypatch):
        def ok_cmd(workflow):
            return (sys.executable, "-c", "print('fine')")

        app, runner = _make_app(tmp_path, monkeypatch, command_builder=ok_cmd)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            started = (await client.post("/workflows/code-review/run")).json()
            await _wait_terminal(runner, started["run_id"])
            resp = await client.post(f"/runs/{started['run_id']}/diagnose")
        assert resp.status_code == 400
        assert "FAILED" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_attune_heal_source_is_400(self, tmp_path, monkeypatch):
        app, runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            started = (
                await client.post("/workflows/code-review/run", json={"trigger": "attune-heal"})
            ).json()
            await _wait_terminal(runner, started["run_id"])
            resp = await client.post(f"/runs/{started['run_id']}/diagnose")
        assert resp.status_code == 400
        assert "self-record" in resp.json()["detail"]


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_existing_diagnosis_returns_200_not_dispatch(self, tmp_path, monkeypatch):
        app, runner = _make_app(tmp_path, monkeypatch)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            started = (await client.post("/workflows/code-review/run")).json()
            await _wait_terminal(runner, started["run_id"])
            # Pre-existing diagnosis for this run in the isolated store.
            TelemetryStore().log_diagnosis(
                DiagnosisRecord(
                    diagnosis_id="d-existing",
                    source_run_id=started["run_id"],
                    workflow_name="code-review",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            resp = await client.post(f"/runs/{started['run_id']}/diagnose")
        assert resp.status_code == 200
        body = resp.json()
        assert body["existing"] is True
        assert body["diagnosis_id"] == "d-existing"


class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_carries_attune_heal_and_source_id(self, tmp_path, monkeypatch):
        app, runner = _make_app(tmp_path, monkeypatch, command_builder=_echo_dispatch_cmd)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First run "fails" is not possible with echo builder — start
            # a failing run via a per-call builder instead: mark the
            # source failed by hand after it completes.
            started = (await client.post("/workflows/code-review/run")).json()
            source = await _wait_terminal(runner, started["run_id"])
            source.status = "failed"
            source.exit_code = 1

            resp = await client.post(f"/runs/{started['run_id']}/diagnose")
            assert resp.status_code == 201
            diag = await _wait_terminal(runner, resp.json()["run_id"])

        assert diag.workflow == "diagnose"
        assert diag.trigger == "attune-heal"
        joined = "\n".join(diag.lines)
        assert "DISPATCH trigger=attune-heal" in joined
        assert f"DISPATCH args={started['run_id']}" in joined

    def test_default_command_maps_diagnose_to_cli(self):
        argv = _default_command("diagnose")
        assert argv[-2:] == ("attune.cli_minimal", "diagnose")
        argv_wf = _default_command("code-review")
        assert argv_wf[-3:] == ("workflow", "run", "code-review")


class TestNoAutoStart:
    """Source-level guards: diagnosis fires only on an explicit click."""

    def test_button_requires_failed_status_and_click(self):
        text = (JS_DIR / "run_view.js").read_text(encoding="utf-8")
        assert 'if (status !== "failed") return;' in text
        assert 'DATA.trigger === "attune-heal"' in text  # self-diagnosis guard
        # The POST lives inside the button's click listener, not init.
        click_idx = text.index('btn.addEventListener("click"')
        post_idx = text.index('"/diagnose"')
        assert post_idx > click_idx

    def test_template_injects_diagnosis_ids(self):
        text = (TPL_DIR / "run_view.html").read_text(encoding="utf-8")
        assert '"diagnosis_ids"' in text
        assert '"trigger"' in text
