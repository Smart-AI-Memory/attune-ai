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
import threading

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
    # `testserver` is TestClient's default base_url host; `test` is the
    # AsyncClient(base_url="http://test") host. Add both to the
    # allowlist so the security middleware (PR #253-impl) doesn't 400
    # every test request.
    config = build_config(
        project_root=tmp_path,
        allow_run=allow_run,
        trusted_hosts=("testserver", "test"),
    )
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
    """Second POST while a run is in flight returns 409.

    The first run's executor blocks on a release event the test only
    sets AFTER the 409 assertions, so the busy window provably spans
    the second POST — no timer race (a 0.5s sleep flaked on the
    Windows 3.13 lane when the run finished before the probe landed).
    ``threading.Event`` (not ``asyncio.Event``) because the test
    thread sets it while the executor polls it from TestClient's
    event loop.
    """
    release = threading.Event()

    async def gated_executor(run):
        from datetime import datetime, timezone

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        while not release.is_set():
            await asyncio.sleep(0.01)
        run.mark_done(0)

    app, _ = _make_app(
        tmp_path,
        monkeypatch,
        allow_run=True,
        command_builder=lambda _: ("noop",),
        executor=gated_executor,
    )
    with TestClient(app) as client:
        try:
            first = client.post("/workflows/x/run")
            assert first.status_code == 201
            second = client.post("/workflows/x/run")
            assert second.status_code == 409
            detail = second.json()["detail"]
            assert detail["current_run_id"] == first.json()["run_id"]
        finally:
            # Release before lifespan shutdown so the gated run can't
            # outlive the client, even when an assertion fails.
            release.set()


def test_run_relative_scope_resolves_against_project_root_not_cwd(tmp_path, monkeypatch):
    """Regression — relative scopes must anchor to ``--project-root``.

    Bug: ``_validate_file_path`` calls ``Path(scope).resolve()``, which
    resolves a relative scope against ``Path.cwd()``. When the
    dashboard process is launched from a directory other than its
    ``--project-root`` (common in worktree setups), every relative
    scope is rejected as "outside allowed directory" — manifests as
    "all workflows producing errors" in the UI.

    Fix: anchor relative scopes to ``cfg.project_root`` before the
    validator sees them. Absolute paths still flow through unchanged.

    Repro:
      - project_root = tmp_path/proj  (with a file inside it)
      - cwd          = tmp_path/elsewhere  (no such file)
      - POST {"path": "src/foo.txt"} to /workflows/code-review/run
      - Pre-fix: 400 "outside allowed directory"
      - Post-fix: 201 (run starts)
    """
    proj_root = tmp_path / "proj"
    (proj_root / "src").mkdir(parents=True)
    (proj_root / "src" / "foo.txt").write_text("body")

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=proj_root,
        allow_run=True,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=_echo_cmd)
    app = create_app(config, runner=runner)

    with TestClient(app) as client:
        resp = client.post(
            "/workflows/code-review/run",
            json={"path": "src/foo.txt"},
        )
    assert resp.status_code == 201, resp.text
    assert "run_id" in resp.json()


def test_run_absolute_scope_outside_project_root_still_rejected(tmp_path, monkeypatch):
    """Defense check — the cwd fix must not weaken the security guard.

    Absolute paths outside ``project_root`` were rejected pre-fix and
    must stay rejected post-fix. Lock in the contract so a future
    refactor of ``_absolutize_scope`` can't silently widen the
    allowlist."""
    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    outside = tmp_path / "outside" / "leak.txt"
    outside.parent.mkdir()
    outside.write_text("nope")

    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=proj_root,
        allow_run=True,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService(command_builder=_echo_cmd)
    app = create_app(config, runner=runner)

    with TestClient(app) as client:
        resp = client.post(
            "/workflows/code-review/run",
            json={"path": str(outside)},
        )
    assert resp.status_code == 400
    assert "outside allowed" in resp.json()["detail"]


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


# --- run-view page tests ---


def test_run_view_page_renders_for_existing_run(tmp_path, monkeypatch):
    """`/runs/{run_id}/view` renders the full-page log viewer for a real run."""
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    client = TestClient(app)
    started = client.post("/workflows/code-review/run").json()
    run_id = started["run_id"]

    r = client.get(f"/runs/{run_id}/view")
    assert r.status_code == 200
    # Page chrome — confirms the template rendered, not raw JSON
    assert "Back to workflows" in r.text
    # Stream URL is embedded for the page's EventSource to consume
    assert f"/runs/{run_id}/stream" in r.text
    # Workflow name shows in the heading
    assert "code-review" in r.text


def test_run_view_page_unknown_run_returns_404(tmp_path, monkeypatch):
    """Unknown run_id → 404. The server's custom 404 handler renders
    404.html so we check status code only; the body is page chrome."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    client = TestClient(app)
    # Use a UUID-shape that passes the validation regex but doesn't exist.
    r = client.get("/runs/abcdef1234567890/view")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "bad_id",
    ["../escape", "%2F..%2Fetc", "weird/slash", "back\\slash", "with space", "a" * 100],
)
def test_run_view_page_rejects_invalid_run_id(tmp_path, monkeypatch, bad_id):
    """Path-traversal or overlong run_ids return 400 (or 404 if FastAPI
    rejects the route match before our handler runs)."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    client = TestClient(app)
    r = client.get(f"/runs/{bad_id}/view")
    assert r.status_code in (
        400,
        404,
    ), f"bad_id={bad_id!r} got {r.status_code}: {r.text}"


def test_workflows_page_no_longer_starts_inline_streaming(tmp_path, monkeypatch):
    """The runner.js change: clicking Run navigates to the run-view page
    instead of streaming inline. The Workflows template should still
    render run buttons (so the page works) — visual smoke is by-eye in
    the browser; here we just confirm the JS file we ship references
    `window.location.assign`."""
    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    # Fetch the actual JS asset the page loads; assert it has the
    # navigation call instead of the old `appendLine + EventSource` path.
    client = TestClient(app)
    r = client.get("/static/js/runner.js")
    assert r.status_code == 200
    assert "window.location.assign" in r.text
    assert "/runs/" in r.text
    assert "/view" in r.text


# --- security-hardening tests (#253 spec) ---


async def test_run_view_replays_full_output_after_completion(tmp_path, monkeypatch):
    """End-to-end "output survives refresh" — start a run, complete it,
    request the /view URL, then attach to the streamed-out stream URL and
    confirm full replay arrives.

    This is the regression guard for the headline behavior of PR #251:
    refreshing the run-view page after a run is done should still show
    the full log because the runner replays buffered events to new
    subscribers.
    """
    import json

    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Start a run + wait for terminal so the buffer has all events.
        started = (await client.post("/workflows/code-review/run")).json()
        run_id = started["run_id"]
        await _wait_terminal(runner, run_id)

        # 2. Request the /view page (simulates the user navigating).
        view = await client.get(f"/runs/{run_id}/view")
        assert view.status_code == 200
        # Page should embed the stream URL for the EventSource to consume.
        assert f"/runs/{run_id}/stream" in view.text

        # 3. Attach to the stream URL AFTER the run completed. The
        # runner's `subscribe()` replays the buffered events for new
        # subscribers — that's the mechanism that makes refresh work.
        async with client.stream("GET", f"/runs/{run_id}/stream") as resp:
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

    # Full replay should include both stdout lines AND the terminal `done`.
    kinds = [k for k, _ in events]
    assert "line" in kinds, f"no replayed lines: {events}"
    assert kinds[-1] == "done", f"missing terminal done: {kinds}"
    line_payloads = [json.loads(d) for k, d in events if k == "line"]
    assert any("start code-review" in s for s in line_payloads if isinstance(s, str))
    done = json.loads(events[-1][1])
    assert done["status"] == "completed"
    assert done["exit_code"] == 0


def test_run_view_logs_404(tmp_path, monkeypatch, caplog):
    """run_view 404 path emits an INFO log with the run_id."""
    import logging

    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="attune.ops.routes.dashboard"):
        r = client.get("/runs/nonexistent12345/view")
    assert r.status_code == 404
    assert any(
        "nonexistent12345" in record.message and record.levelno == logging.INFO
        for record in caplog.records
    )


def test_run_view_logs_invalid_input(tmp_path, monkeypatch, caplog):
    """run_view 400 path emits a WARN log with the (truncated) bad input."""
    import logging

    app, _ = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_echo_cmd)
    client = TestClient(app)
    with caplog.at_level(logging.WARNING, logger="attune.ops.routes.dashboard"):
        r = client.get("/runs/with%20space/view")
    assert r.status_code == 400
    assert any(record.levelno == logging.WARNING for record in caplog.records)


async def test_subscriber_queue_drops_slow_subscriber(tmp_path, monkeypatch):
    """A subscriber that never consumes its queue gets dropped when the
    bound (1000 events) is exceeded. Before this fix, the unbounded queue
    grew indefinitely and the `except QueueFull` block was dead code."""
    import asyncio

    from attune.ops.runner import Run

    run = Run(id="test-overflow", workflow="echo")
    # Create a slow subscriber by manually adding a queue that we never
    # consume from. Use a small maxsize for the test to keep it fast.
    slow_queue: asyncio.Queue = asyncio.Queue(maxsize=5)
    run.subscribers.add(slow_queue)

    # Broadcast more events than the queue can hold.
    for i in range(10):
        run._broadcast(("line", f"event-{i}"))

    # The slow subscriber should have been dropped from `run.subscribers`
    # (the except QueueFull block calls subscribers.discard).
    assert (
        slow_queue not in run.subscribers
    ), "slow subscriber should have been dropped after queue filled up"


async def test_subscriber_queue_does_not_block_fast_subscribers(tmp_path, monkeypatch):
    # Regression guard: one slow subscriber must not slow down others.
    # _broadcast is synchronous put_nowait per subscriber, so a backed-up
    # queue triggers QueueFull on that subscriber only — the rest still
    # receive the event in the same loop iteration.
    import asyncio

    from attune.ops.runner import Run

    run = Run(id="test-isolation", workflow="echo")
    # Slow subscriber — saturates after 3 events, is then dropped.
    slow_queue: asyncio.Queue = asyncio.Queue(maxsize=3)
    # Fast subscriber — well above the event count we'll send.
    fast_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    run.subscribers.add(slow_queue)
    run.subscribers.add(fast_queue)

    for i in range(10):
        run._broadcast(("line", f"event-{i}"))

    # Slow subscriber gets dropped per its own QueueFull, no impact on fast.
    assert slow_queue not in run.subscribers
    assert fast_queue in run.subscribers
    # Fast subscriber received every event in order.
    assert fast_queue.qsize() == 10
    received = [fast_queue.get_nowait() for _ in range(10)]
    assert received == [("line", f"event-{i}") for i in range(10)]


@pytest.mark.asyncio
async def test_executor_task_is_pinned_while_running_and_popped_on_completion(
    tmp_path, monkeypatch
):
    """Regression: the workflow-executor task must be stored in
    ``RunnerService._executor_tasks`` while in flight (asyncio holds
    only weak references to tasks; a discarded ``create_task`` return
    value can be GC'd mid-flight and the workflow silently dies). On
    completion the entry must be popped by the done-callback so the
    dict stays bounded at ``len(active_runs)``.
    """
    proceed = asyncio.Event()

    async def _slow_executor(run):
        # Hold here until the test releases us, so we can observe the
        # in-flight state of _executor_tasks deterministically.
        await proceed.wait()
        run.mark_done(0)

    app, runner = _make_app(
        tmp_path,
        monkeypatch,
        allow_run=True,
        command_builder=_echo_cmd,
        executor=_slow_executor,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/workflows/code-review/run")
        assert resp.status_code == 201
        run_id = resp.json()["run_id"]

        # Yield so start() returns and the executor task is scheduled.
        await asyncio.sleep(0)

        # While the run is still in flight the executor task must be pinned.
        assert run_id in runner._executor_tasks, (
            "executor task was not stored in _executor_tasks — "
            "could be GC'd mid-flight (cpython weak-ref task issue)"
        )

        # Release the executor and wait for terminal status.
        proceed.set()
        await _wait_terminal(runner, run_id)

        # Give the done-callback one event-loop iteration to fire.
        await asyncio.sleep(0)

        # After completion the entry must be popped so the dict stays
        # bounded — no per-run memory leak.
        assert run_id not in runner._executor_tasks, (
            "executor task entry was not popped on completion — "
            "done_callback wiring is broken (dict will grow unbounded)"
        )


def _long_line_cmd(workflow: str) -> tuple[str, ...]:
    """One >64 KiB single line then exit 0 — exceeds asyncio's default
    StreamReader limit, which readline() answers with ValueError."""
    script = (
        f"import sys; print('start {workflow}'); "
        "print('L' * 200_000); "
        "print('end-long'); sys.exit(0)"
    )
    return (sys.executable, "-c", script)


@pytest.mark.asyncio
async def test_line_over_64k_does_not_fail_run(tmp_path, monkeypatch):
    """Regression (bug-predict 2026-08-02, run b67fca241221): the read
    side of the run-meta channel — asyncio's default 64 KiB limit makes
    readline() raise on a long report_b64 line and the runner's except
    stamped a SUCCEEDED run failed. The subprocess limit is raised to
    _STDOUT_LINE_LIMIT."""
    app, runner = _make_app(tmp_path, monkeypatch, allow_run=True, command_builder=_long_line_cmd)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/workflows/code-review/run")
        assert resp.status_code == 201
        run = await _wait_terminal(runner, resp.json()["run_id"])
        assert run.status == "completed"
        assert run.exit_code == 0
        assert not any("[runner error]" in ln for ln in run.lines)
        assert any(len(ln) >= 200_000 for ln in run.lines)
        assert any("end-long" in ln for ln in run.lines)
