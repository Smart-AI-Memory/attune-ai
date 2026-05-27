"""Tests for HelpRegenRunner — async subprocess manager for
attune-author regen jobs.

Uses a fake binary (a tiny shell script) so tests don't depend
on attune-author being installed in the venv. The script echoes
its arguments and exits with whatever code we want — enough to
exercise every code path in the runner.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from attune.ops.config import Config
from attune.ops.help_regen import (
    _ANSI_RE,
    HelpRegenBusyError,
    HelpRegenJob,
    HelpRegenRunner,
)
from attune.ops.server import create_app

# The fake-binary fixtures below write POSIX shell scripts with
# `#!/bin/sh` shebangs and chmod 0o755 — neither resolves on Windows.
# Tests that actually invoke the binary fail there (subprocess startup
# errors); tests that only exercise validation logic before invocation
# still pass. Apply this mark to the affected tests only.
_skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="fake-binary fixture is a POSIX shell script; production "
    "runner itself is OS-agnostic",
)


@pytest.fixture
def fake_binary(tmp_path: Path) -> Path:
    """Tiny shell script that mimics attune-author CLI shape.

    Echoes "started action=<action>", a numbered line, and exits 0
    unless ATTUNE_FAKE_EXIT_CODE is set.
    """
    script = tmp_path / "fake-attune-author"
    script.write_text(
        "#!/bin/sh\n"
        'echo "started action=$1"\n'
        'for i in 1 2 3; do echo "line $i"; done\n'
        'exit "${ATTUNE_FAKE_EXIT_CODE:-0}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


@pytest.fixture
def slow_binary(tmp_path: Path) -> Path:
    """Fake binary that sleeps briefly — used for concurrency tests."""
    script = tmp_path / "slow-attune-author"
    script.write_text("#!/bin/sh\nsleep 0.3\necho 'done'\n", encoding="utf-8")
    script.chmod(0o755)
    return script


@pytest.fixture
def ansi_binary(tmp_path: Path) -> Path:
    """Fake binary that emits ANSI color codes."""
    script = tmp_path / "ansi-attune-author"
    # Real ANSI bytes — match what attune-author + structlog emit
    script.write_text(
        "#!/bin/sh\nprintf '\\033[36mcolor line\\033[0m\\n'\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _await(coro):
    """Run a coroutine to completion with full asyncio cleanup.

    Uses ``asyncio.run()`` rather than a hand-managed loop because
    subprocess transports queue close-time cleanup callbacks; with a
    raw ``new_event_loop().run_until_complete()`` those callbacks fire
    after the loop is closed and raise ``RuntimeError("Event loop is
    closed")``. ``asyncio.run()`` shuts down async gens before closing
    so the cleanup lands cleanly.
    """
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Basic execution paths
# ---------------------------------------------------------------------------


class TestGenerate:
    @_skip_on_windows
    def test_generate_runs_subprocess(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))

        async def run() -> HelpRegenJob:
            job = await runner.start("generate", feature="example-feat")
            # Wait for it to finish.
            for _ in range(50):
                if job.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            return job

        job = _await(run())
        assert job.status == "completed"
        assert job.exit_code == 0
        assert any("started action=generate" in line for line in job.lines)

    def test_generate_requires_feature(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))
        with pytest.raises(ValueError, match="feature required"):
            _await(runner.start("generate"))

    def test_invalid_feature_slug_rejected(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))
        with pytest.raises(ValueError, match="invalid feature slug"):
            _await(runner.start("generate", feature="../etc"))

    def test_uppercase_feature_rejected(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))
        with pytest.raises(ValueError, match="invalid feature slug"):
            _await(runner.start("generate", feature="Bad-Slug"))


class TestRegenerate:
    @_skip_on_windows
    def test_regenerate_runs(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))

        async def run() -> HelpRegenJob:
            job = await runner.start("regenerate")
            for _ in range(50):
                if job.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            return job

        job = _await(run())
        assert job.status == "completed"
        assert any("started action=regenerate" in line for line in job.lines)

    def test_dry_run_flag_added(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))

        async def run() -> HelpRegenJob:
            job = await runner.start("regenerate", dry_run=True)
            # Wait for the subprocess to complete so its transport
            # cleanup doesn't race with the event-loop close — same
            # pattern as the other tests in this file. Without it,
            # xdist workers crash on Ubuntu CI (Python 3.11/3.12).
            for _ in range(50):
                if job.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            return job

        job = _await(run())
        assert "--dry-run" in job.command


class TestFailingSubprocess:
    @_skip_on_windows
    def test_nonzero_exit_marks_failed(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))

        async def run() -> HelpRegenJob:
            os.environ["ATTUNE_FAKE_EXIT_CODE"] = "1"
            try:
                job = await runner.start("regenerate")
                for _ in range(50):
                    if job.status in ("completed", "failed"):
                        break
                    await asyncio.sleep(0.05)
                return job
            finally:
                os.environ.pop("ATTUNE_FAKE_EXIT_CODE", None)

        job = _await(run())
        assert job.status == "failed"
        assert job.exit_code == 1


class TestBusy:
    def test_second_start_while_running_raises(self, slow_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(slow_binary))

        async def run() -> None:
            await runner.start("regenerate")
            # Second call while first is running — should raise.
            with pytest.raises(HelpRegenBusyError):
                await runner.start("regenerate")
            # Wait for first to finish so we don't leak the subprocess.
            for _ in range(100):
                cur = runner.current
                if cur is None:
                    break
                await asyncio.sleep(0.05)

        _await(run())


class TestMissingBinary:
    def test_no_binary_raises_filenotfound(self, tmp_path: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(tmp_path / "nonexistent-binary"))
        # The runner accepts the path at construction; the binary
        # absence is detected when subprocess startup fails. We use
        # the resolve-check to pre-empt this.
        # Path that doesn't resolve via shutil.which → fall through
        runner._attune_author_path = ""
        runner._resolve_command = lambda: None  # type: ignore[method-assign]
        with pytest.raises(FileNotFoundError, match="attune-author not found"):
            _await(runner.start("regenerate"))


class TestAnsiStripping:
    @_skip_on_windows
    def test_ansi_codes_stripped_from_log(self, ansi_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(ansi_binary))

        async def run() -> HelpRegenJob:
            job = await runner.start("regenerate")
            for _ in range(50):
                if job.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            return job

        job = _await(run())
        assert job.status == "completed"
        for line in job.lines:
            assert "\x1b[" not in line, f"unstripped ANSI in {line!r}"
        # Color word still present even with codes removed
        assert any("color line" in line for line in job.lines)


class TestAnsiRegex:
    def test_strips_color(self) -> None:
        assert _ANSI_RE.sub("", "\x1b[36mhello\x1b[0m") == "hello"

    def test_strips_complex(self) -> None:
        text = "\x1b[2m2026-05-26\x1b[0m \x1b[32m\x1b[1minfo\x1b[0m rag.run"
        assert _ANSI_RE.sub("", text) == "2026-05-26 info rag.run"

    def test_passes_through_plain_text(self) -> None:
        assert _ANSI_RE.sub("", "no color here") == "no color here"


# ---------------------------------------------------------------------------
# Output cap + history
# ---------------------------------------------------------------------------


class TestOutputCap:
    @_skip_on_windows
    def test_oversized_output_truncated(self, tmp_path: Path) -> None:
        # Build a script that floods stdout
        flooder = tmp_path / "flood"
        flooder.write_text(
            "#!/bin/sh\nfor i in $(seq 1 50000); do echo "
            "'flood line with some bulk text for size estimate'; done\n",
            encoding="utf-8",
        )
        flooder.chmod(0o755)
        runner = HelpRegenRunner(attune_author_path=str(flooder))

        async def run() -> HelpRegenJob:
            job = await runner.start("regenerate")
            for _ in range(200):
                if job.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            return job

        job = _await(run())
        # The cap kicks in and adds a truncation marker; total bytes
        # captured should stay under the cap.
        assert any("[output truncated" in line for line in job.lines)


class TestHistory:
    def test_recent_returns_jobs(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary), history_limit=3)

        async def run() -> None:
            for _ in range(2):
                job = await runner.start("regenerate")
                # Wait for completion before starting next (single-concurrent).
                for _ in range(50):
                    if job.status in ("completed", "failed"):
                        break
                    await asyncio.sleep(0.05)

        _await(run())
        recent = runner.recent(limit=5)
        assert len(recent) == 2
        # Newest first.
        assert recent[0].started_at >= recent[1].started_at

    def test_history_limit_evicts_oldest(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary), history_limit=2)

        async def run() -> None:
            for _ in range(4):
                job = await runner.start("regenerate")
                for _ in range(50):
                    if job.status in ("completed", "failed"):
                        break
                    await asyncio.sleep(0.05)

        _await(run())
        # Only the 2 most recent jobs retained.
        assert len(runner.recent(limit=10)) == 2


class TestJobToDict:
    def test_to_dict_has_required_fields(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))

        async def run() -> HelpRegenJob:
            job = await runner.start("regenerate")
            for _ in range(50):
                if job.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            return job

        job = _await(run())
        d = job.to_dict()
        for field in (
            "id",
            "action",
            "feature",
            "command",
            "status",
            "exit_code",
            "started_at",
            "completed_at",
            "lines",
            "line_count",
        ):
            assert field in d
        assert d["line_count"] == len(d["lines"])


# ---------------------------------------------------------------------------
# Resolve command path
# ---------------------------------------------------------------------------


class TestResolveCommand:
    def test_explicit_path_used(self, fake_binary: Path) -> None:
        runner = HelpRegenRunner(attune_author_path=str(fake_binary))
        assert runner._resolve_command() == str(fake_binary)

    def test_no_explicit_path_uses_which(self) -> None:
        runner = HelpRegenRunner()
        # Whatever shutil.which returns is OK — the test just confirms
        # the function returns either a string or None without raising.
        result = runner._resolve_command()
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# Regen route integration — uses TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def regen_client(tmp_path: Path, fake_binary: Path) -> TestClient:
    cfg = Config(
        project_root=tmp_path,
        attune_home=tmp_path / "ah",
        allow_run=False,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(cfg)
    # Replace the default regen runner with one pointed at the fake binary.
    app.state.help_regen = HelpRegenRunner(attune_author_path=str(fake_binary))
    return TestClient(app)


class TestRegenRoute:
    def test_post_starts_job(self, regen_client: TestClient) -> None:
        resp = regen_client.post("/api/help/regen", json={"action": "regenerate"})
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] in ("pending", "running")
        assert data["action"] == "regenerate"

    def test_post_invalid_action_400(self, regen_client: TestClient) -> None:
        resp = regen_client.post("/api/help/regen", json={"action": "nope"})
        assert resp.status_code == 400

    def test_post_generate_without_feature_400(self, regen_client: TestClient) -> None:
        resp = regen_client.post("/api/help/regen", json={"action": "generate"})
        assert resp.status_code == 400

    def test_post_generate_invalid_slug_400(self, regen_client: TestClient) -> None:
        resp = regen_client.post(
            "/api/help/regen",
            json={"action": "generate", "feature": "../etc"},
        )
        assert resp.status_code == 400

    def test_get_status_404_for_unknown(self, regen_client: TestClient) -> None:
        resp = regen_client.get("/api/help/regen/0123456789ab")
        assert resp.status_code == 404

    def test_get_invalid_job_id_400(self, regen_client: TestClient) -> None:
        resp = regen_client.get("/api/help/regen/has-dashes")
        assert resp.status_code == 400

    @_skip_on_windows
    def test_get_status_returns_job(self, regen_client: TestClient) -> None:
        """POST creates a job, GET returns its current state.

        Note: TestClient is sync, so the runner's asyncio.create_task
        doesn't get to drive the subprocess to completion between
        request cycles. We assert on wiring (200 + JSON shape),
        not on terminal completion. Subprocess execution is
        exercised by the non-route tests with asyncio.run().
        """
        post = regen_client.post("/api/help/regen", json={"action": "regenerate"})
        job_id = post.json()["id"]
        resp = regen_client.get(f"/api/help/regen/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == job_id
        assert body["status"] in ("pending", "running", "completed")
        assert body["action"] == "regenerate"

    def test_recent_list(self, regen_client: TestClient) -> None:
        regen_client.post("/api/help/regen", json={"action": "regenerate"})
        resp = regen_client.get("/api/help/regen")
        assert resp.status_code == 200
        assert "jobs" in resp.json()
