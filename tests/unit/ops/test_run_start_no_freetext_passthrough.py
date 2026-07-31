"""Guard: the ops run-start endpoint accepts no free-text passthrough.

outcome-first-fix D7. The ops run-record writer persists every run's
command line, so any endpoint that let a caller inject arbitrary
subprocess arguments would put user prose (a Fix goal, a prompt) on
disk under ``~/.attune/ops/runs/``. Today it cannot: the endpoint reads
exactly ``path`` and ``trigger`` from the body and passes only those to
``RunnerService.start``.

That is the property worth guarding — NOT the writer's behavior. The
writer storing what it is given is correct; the exposure would arrive
the day this endpoint grows an ``--input`` / ``extra_args`` passthrough.
This test fails on that day.
"""

from __future__ import annotations

import sys

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import RunnerService  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

#: Free text that must never reach a subprocess argv or a run record.
PROSE = "zqx-d7-sentinel-make-the-boundary-order-bulk"


def _echo_cmd(workflow: str) -> tuple[str, ...]:
    script = f"import sys; print('start {workflow}'); sys.exit(0)"
    return (sys.executable, "-c", script)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        allow_run=True,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=_echo_cmd)
    return create_app(config, runner=runner), runner


def test_free_text_body_fields_never_reach_the_subprocess(tmp_path, monkeypatch):
    """Extra body keys are ignored, not forwarded as arguments."""
    app, runner = _app(tmp_path, monkeypatch)

    with TestClient(app) as client:
        resp = client.post(
            "/workflows/code-review/run",
            json={
                "trigger": "manual",
                # Every shape a caller might try to smuggle prose through:
                "input": f'{{"goal": "{PROSE}"}}',
                "extra_args": ["--input", f'{{"goal": "{PROSE}"}}'],
                "goal": PROSE,
                "args": [PROSE],
            },
        )

    assert resp.status_code == 201, resp.text
    run = runner.get(resp.json()["run_id"])
    assert run is not None
    assert run.extra_args is None, "endpoint forwarded caller-supplied arguments"
    assert PROSE not in " ".join(run.command or []), "prose reached the subprocess argv"


def test_free_text_body_fields_never_reach_the_persisted_record(tmp_path, monkeypatch):
    """The record is the thing on disk — assert over its real content."""
    app, runner = _app(tmp_path, monkeypatch)

    with TestClient(app) as client:
        resp = client.post(
            "/workflows/code-review/run",
            json={"trigger": "manual", "goal": PROSE, "input": PROSE},
        )
        run_id = resp.json()["run_id"]

    run = runner.get(run_id)
    assert run is not None
    record = run.to_record()
    assert PROSE not in str(record), "prose reached the run record"


def test_only_path_and_trigger_are_read_from_the_body(tmp_path, monkeypatch):
    """Pin the parser's surface: widening it is what creates the risk.

    A body field that IS honored must be added here deliberately, with
    the D7 consequence considered — that is the point of the guard.
    """
    from attune.ops.routes import runner as runner_routes

    source = runner_routes._read_run_body.__doc__ or ""
    assert "path" in source and "trigger" in source

    import inspect

    body = inspect.getsource(runner_routes._read_run_body)
    honored = {line for line in body.splitlines() if "raw.get(" in line}
    assert len(honored) == 2, f"run body now reads more than path+trigger: {honored}"
