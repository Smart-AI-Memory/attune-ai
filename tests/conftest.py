"""Pytest configuration for Attune AI tests."""

import faulthandler
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# =============================================================================
# Coverage Import Guard - pre-import pydantic.root_model
# =============================================================================
# Under the pytest-cov plugin (``pytest --cov=...``), importing any module
# whose chain transitively builds a pydantic ``RootModel[...]`` generic
# (e.g. ``attune.workflows`` -> ``claude_agent_sdk`` -> ``mcp.types``) raises
# ``KeyError: 'pydantic.root_model'`` deep in
# ``pydantic._internal._generics.create_generic_submodel`` — it does
# ``sys.modules[created_model.__module__]`` (the module is ``pydantic.root_model``)
# and the submodule isn't registered yet under pytest-cov's startup ordering.
# Plain ``pytest`` and ``coverage run -m pytest`` are unaffected; only the
# pytest-cov plugin trips it, which walls LOCAL ``--cov`` measurement of
# workflows / meta_workflows / orchestration (anything importing the SDK).
# Warming ``pydantic.root_model`` into sys.modules first is the minimal,
# deterministic fix (verified: importing ``pydantic._internal._generics``
# alone is NOT sufficient). Harmless everywhere else — it's a core dep
# already imported transitively.
import pydantic.root_model  # noqa: F401  (import for side effect: sys.modules warm-up)
import pytest

# =============================================================================
# CI hang watchdog (ci-runner-hang spec, Phase 1)
# =============================================================================
# The Ubuntu coverage/test lanes intermittently wedge *inside* the pytest
# step; the per-test `--timeout=60 --timeout-method=thread` does NOT fire,
# so the wedge is at the xdist worker/controller level (a thread blocked in
# an uninterruptible C call holding the GIL, or a controller<->worker
# deadlock) — invisible to a per-test thread timeout.
#
# Arm a process-level faulthandler watchdog so the NEXT hang dumps every
# thread's stack BEFORE the job `timeout-minutes` kills it — turning an
# opaque stall into a named frame. Because this runs at conftest import
# time, it arms in the xdist controller AND every worker subprocess, and
# covers collection-time hangs too.
#
# Phase 2 fix (the watchdog GAP): the dump MUST go to a per-process FILE,
# not stderr. Under pytest-xdist the timer that matters fires inside the
# wedged WORKER (e.g. gw0); execnet does NOT forward a worker's raw fd-2
# dump to the controller's stdout on a HANG (worker output is surfaced via
# its own channel, typically flushed only at a test boundary), so a
# stderr dump is written to the worker's local stderr and LOST when the
# job is killed at `timeout-minutes`. Forensic capture 2026-06-14 (run
# 27488685349, coverage job): gw0 went silent first, the dump fired
# ~05:01 but never reached the CI log. Writing to hang-dumps/hang-<worker>
# .txt (workspace-relative, so a CI `if: always()` step can cat + upload
# it as an artifact) makes the worker dump survive the kill. faulthandler
# writes via the raw fd (async-signal-safe), so the bytes hit the OS
# immediately — no Python-buffer flush needed; repeat=False writes once.
#
# Gated on the auto-set CI env var so local runs are unaffected. Threshold
# is OS-tuned (Linux lanes are fast, ~4-8 min normal; Windows/macOS ~13-15)
# and sits below the job timeout. Overridable via PYTEST_HANG_DUMP_SECONDS
# for local smoke-testing (set CI=1 too, since the watchdog is CI-gated).
_HANG_DUMP_FILE = None  # module-level ref keeps the fd alive for faulthandler
if os.environ.get("CI"):
    _hang_default = 600.0 if os.environ.get("RUNNER_OS") == "Linux" else 1200.0
    _hang_secs = float(os.environ.get("PYTEST_HANG_DUMP_SECONDS", _hang_default))
    # Key the dump file by xdist worker (controller sees no worker env var).
    # PYTEST_XDIST_WORKER is set in each worker subprocess's environment
    # before its Python starts, so it is already present at conftest import.
    _hang_worker = os.environ.get("PYTEST_XDIST_WORKER", "controller")
    _hang_dir = Path(__file__).resolve().parent.parent / "hang-dumps"
    try:
        _hang_dir.mkdir(exist_ok=True)
        # Line-buffered (buffering=1) is belt-and-suspenders; faulthandler
        # writes via the fd directly regardless. Keep the ref in a module
        # global so the file (and its fd) is not GC'd out from under the
        # armed timer.
        _HANG_DUMP_FILE = open(  # noqa: SIM115 (kept open for the watchdog's lifetime)
            _hang_dir / f"hang-{_hang_worker}.txt", "w", buffering=1
        )
        # dump_traceback_later always dumps ALL threads (no all_threads
        # kwarg — that exists only on register()/dump_traceback()).
        faulthandler.dump_traceback_later(_hang_secs, repeat=False, file=_HANG_DUMP_FILE)
        print(
            f"[hang-watchdog] armed: {_hang_secs:.0f}s -> {_hang_dir.name}/"
            f"hang-{_hang_worker}.txt",
            file=sys.stderr,
        )
    except OSError:
        # Never let an un-writable workspace break conftest import (which
        # would fail collection on EVERY test). Fall back to the Phase 1
        # stderr behavior — degraded (worker dumps still lost on a hang)
        # but safe.
        faulthandler.dump_traceback_later(_hang_secs, repeat=False)

# =============================================================================
# Import Guard - Ensure workflows package is properly initialized
# =============================================================================
# This prevents import errors when tests import from workflows package
# in different orders. The lazy loading mechanism in workflows/__init__.py
# can cause "not a package" errors if submodules are imported before the
# package is fully initialized.
#
# We force eager initialization of ALL workflows by:
# 1. Calling discover_workflows() to trigger lazy loading of registered workflows
# 2. Explicitly importing non-registered workflow modules used by tests
try:
    import attune.workflows

    # Force all lazy workflows to load by discovering them
    attune.workflows.discover_workflows()

    # Import additional workflow modules not in lazy registry
    import attune.workflows.batch_processing
    import attune.workflows.history
    import attune.workflows.manage_docs
    import attune.workflows.progressive.core
    import attune.workflows.progressive.orchestrator
    import attune.workflows.security_audit_phase3
except ImportError:
    pass  # Package might not be available in minimal test environments

# Load test environment variables from .env.test
try:
    from dotenv import load_dotenv

    # Load .env.test if it exists (for local testing with mock API keys)
    test_env_path = Path(__file__).parent.parent / ".env.test"
    if test_env_path.exists():
        load_dotenv(test_env_path, override=True)
except ImportError:
    pass  # python-dotenv not installed

# =============================================================================
# Workflow tier_map reset - prevent cross-test pollution
# tier_map is a mutable class-level dict shared across instances.
# Tests calling should_skip_stage() mutate it, affecting later tests.
# =============================================================================

# Snapshot original tier_maps at import time (before any test mutates them)
_ORIGINAL_TIER_MAPS: dict[type, dict] = {}
try:
    from attune.workflows.base import BaseWorkflow

    for _cls in BaseWorkflow.__subclasses__():
        if hasattr(_cls, "tier_map") and isinstance(getattr(_cls, "tier_map", None), dict):
            _ORIGINAL_TIER_MAPS[_cls] = _cls.tier_map.copy()
except Exception:  # noqa: BLE001
    pass


@pytest.fixture(autouse=True)
def _reset_workflow_tier_maps():
    """Restore all workflow tier_maps after each test."""
    yield
    for cls, original in _ORIGINAL_TIER_MAPS.items():
        cls.tier_map.update(original)


@pytest.fixture(autouse=True)
def _restore_event_loop_policy():
    """Restore the global asyncio event loop policy after each test.

    ``asyncio.set_event_loop_policy`` mutates process-wide state. Under
    xdist that leak crosses test *files* on the same worker: a test that
    sets (e.g.) the Selector policy would leave it set for an unrelated
    subprocess/pipe test that lands afterward, which then fails with
    ``NotImplementedError`` on Windows (this poisoned the help-regen
    tests on Windows CI). Snapshot before, restore after, so policy
    mutation can never cross a test boundary.
    """
    import asyncio

    original = asyncio.get_event_loop_policy()
    yield
    asyncio.set_event_loop_policy(original)


# =============================================================================
# File Test Tracking - Automatic per-file test result recording
# Supports both single-process and xdist parallel execution
# =============================================================================

# Global collector for test results per test file
_test_results_by_file: dict = defaultdict(
    lambda: {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "duration": 0.0,
        "failed_tests": [],
    },
)


def _map_test_to_source(test_file: str) -> str | None:
    """Map a test file path to its corresponding source file.

    Examples:
        tests/test_config.py -> src/attune/config.py
        tests/unit/models/test_registry.py -> src/attune/models/registry.py
        tests/unit/cli/test_cli_commands.py -> src/attune/cli.py

    """
    test_path = Path(test_file)

    # Extract the test filename
    filename = test_path.stem  # e.g., "test_config" or "test_registry"
    if not filename.startswith("test_"):
        return None

    # Remove "test_" prefix to get source filename
    source_name = filename[5:]  # "config" or "registry" or "cli_commands"

    # Determine the module path from test location
    parts = test_path.parts

    # Handle tests/unit/<module>/test_*.py pattern
    if "unit" in parts:
        unit_idx = parts.index("unit")
        module_parts = parts[unit_idx + 1 : -1]  # Get parts between unit/ and filename

        if module_parts:
            # Try 1: Direct file in module (e.g., models/registry.py)
            source_path = Path("src/attune") / "/".join(module_parts) / f"{source_name}.py"
            if source_path.exists():
                return str(source_path)

            # Try 2: Module package itself (e.g., cli.py for test_cli_commands.py)
            # Handle patterns like test_cli_commands -> cli/__init__.py or cli.py
            module_name = module_parts[0]  # e.g., "cli"
            if source_name.startswith(f"{module_name}_"):
                # test_cli_commands -> try cli.py first
                source_path = Path("src/attune") / f"{module_name}.py"
                if source_path.exists():
                    return str(source_path)
                # Then try cli/__init__.py
                source_path = Path("src/attune") / module_name / "__init__.py"
                if source_path.exists():
                    return str(source_path)

    # Handle tests/test_*.py pattern (direct tests)
    if "tests" in parts and parts[-1].startswith("test_"):
        # Try direct mapping to src/attune/
        source_path = Path("src/attune") / f"{source_name}.py"
        if source_path.exists():
            return str(source_path)

    # Fallback: search for the source file
    for candidate in Path("src").rglob(f"{source_name}.py"):
        if "__pycache__" not in str(candidate):
            return str(candidate)

    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Collect test results per test file."""
    outcome = yield
    report = outcome.get_result()

    # Only process the "call" phase (actual test execution)
    if report.when == "call":
        test_file = str(item.fspath)

        if report.passed:
            _test_results_by_file[test_file]["passed"] += 1
        elif report.failed:
            _test_results_by_file[test_file]["failed"] += 1
            # Only store first 10 failures per file to limit memory usage
            if len(_test_results_by_file[test_file]["failed_tests"]) < 10:
                # Truncate error message to prevent memory bloat
                error_msg = str(report.longrepr)[:500] if report.longrepr else "Unknown error"
                _test_results_by_file[test_file]["failed_tests"].append(
                    {
                        "name": item.name,
                        "file": test_file,
                        "error": error_msg,
                    },
                )
        elif report.skipped:
            _test_results_by_file[test_file]["skipped"] += 1

        # Track duration
        if hasattr(report, "duration"):
            _test_results_by_file[test_file]["duration"] += report.duration


# =============================================================================
# xdist Support - File-based result sharing between workers and main node
# =============================================================================

_XDIST_RESULTS_DIR = Path(".pytest_file_tracking")


def _get_worker_results_file(worker_id: str) -> Path:
    """Get the results file path for an xdist worker."""
    return _XDIST_RESULTS_DIR / f"worker_{worker_id}.json"


def _aggregate_xdist_results() -> dict:
    """Aggregate results from all xdist worker files."""
    aggregated = defaultdict(
        lambda: {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration": 0.0,
            "failed_tests": [],
        },
    )

    if not _XDIST_RESULTS_DIR.exists():
        return dict(aggregated)

    for results_file in _XDIST_RESULTS_DIR.glob("worker_*.json"):
        try:
            with open(results_file) as f:
                worker_results = json.load(f)
            for test_file, results in worker_results.items():
                aggregated[test_file]["passed"] += results.get("passed", 0)
                aggregated[test_file]["failed"] += results.get("failed", 0)
                aggregated[test_file]["skipped"] += results.get("skipped", 0)
                aggregated[test_file]["errors"] += results.get("errors", 0)
                aggregated[test_file]["duration"] += results.get("duration", 0.0)
                aggregated[test_file]["failed_tests"].extend(results.get("failed_tests", []))
            # Clean up worker file after reading
            results_file.unlink()
        except (json.JSONDecodeError, OSError):
            pass

    # Clean up directory if empty
    try:
        if _XDIST_RESULTS_DIR.exists() and not any(_XDIST_RESULTS_DIR.iterdir()):
            _XDIST_RESULTS_DIR.rmdir()
    except OSError:
        pass

    return dict(aggregated)


def pytest_sessionfinish(session, exitstatus):
    """Store file test records at end of test session."""
    # ci-runner-hang: deterministically finalize any leaked asyncio subprocess
    # transport NOW, while the worker process is still healthy. A transport left
    # dangling from a per-test ``asyncio.run()`` otherwise finalizes during
    # interpreter shutdown (``BaseSubprocessTransport.__del__`` → "Event loop is
    # closed"); on Linux/py3.12 that wedges the xdist worker, so the controller
    # deadlocks at ~99% waiting on a worker that never exits (the recurring
    # runner-hang). Forcing GC here moves that finalization out of the fragile
    # interpreter-exit phase, where it can no longer block worker teardown.
    # Two passes: the first frees the transport, the second collects any cycle
    # it was part of. Harmless on platforms where this was already benign.
    import gc as _gc

    _gc.collect()
    _gc.collect()

    # Check if this is an xdist worker
    if hasattr(session.config, "workerinput"):
        # This is a worker - write results to file for main node to collect
        if _test_results_by_file:
            worker_id = session.config.workerinput.get("workerid", "unknown")
            _XDIST_RESULTS_DIR.mkdir(exist_ok=True)
            results_file = _get_worker_results_file(worker_id)

            # Convert defaultdict to regular dict for serialization
            serializable_results = {}
            for test_file, results in _test_results_by_file.items():
                serializable_results[test_file] = dict(results)

            with open(results_file, "w") as f:
                json.dump(serializable_results, f)
        return

    # Check if tracking is enabled (can be disabled via env var)
    if os.environ.get("EMPATHY_SKIP_FILE_TRACKING", "").lower() in ("1", "true", "yes"):
        return

    # Determine which results to use:
    # - If xdist worker files exist, aggregate from them
    # - Otherwise, use local results (non-parallel execution)
    xdist_results = _aggregate_xdist_results()

    if xdist_results:
        results_to_store = xdist_results
    elif _test_results_by_file:
        results_to_store = dict(_test_results_by_file)
    else:
        return  # No results to store

    try:
        from attune.models.telemetry import FileTestRecord, get_telemetry_store

        store = get_telemetry_store()
        timestamp = datetime.now(timezone.utc).isoformat()

        for test_file, results in results_to_store.items():
            # Map test file to source file
            source_file = _map_test_to_source(test_file)
            if source_file is None:
                continue  # Skip if we can't map to source

            total = results["passed"] + results["failed"] + results["skipped"] + results["errors"]
            if total == 0:
                continue  # Skip empty results

            # Determine overall result
            if results["failed"] > 0 or results["errors"] > 0:
                last_test_result = "failed"
            elif results["passed"] > 0:
                last_test_result = "passed"
            elif results["skipped"] == total:
                last_test_result = "skipped"
            else:
                last_test_result = "no_tests"

            # Get file modification times
            source_path = Path(source_file)
            test_path = Path(test_file)

            source_modified_at = None
            tests_modified_at = None

            if source_path.exists():
                source_modified_at = datetime.fromtimestamp(
                    source_path.stat().st_mtime, tz=timezone.utc
                ).isoformat()

            if test_path.exists():
                tests_modified_at = datetime.fromtimestamp(
                    test_path.stat().st_mtime, tz=timezone.utc
                ).isoformat()

            # Check staleness
            is_stale = False
            if source_modified_at and tests_modified_at:
                is_stale = source_modified_at > tests_modified_at

            record = FileTestRecord(
                file_path=source_file,
                timestamp=timestamp,
                last_test_result=last_test_result,
                test_count=total,
                passed=results["passed"],
                failed=results["failed"],
                skipped=results["skipped"],
                errors=results["errors"],
                duration_seconds=results["duration"],
                test_file_path=test_file,
                failed_tests=results["failed_tests"],
                source_modified_at=source_modified_at,
                tests_modified_at=tests_modified_at,
                is_stale=is_stale,
            )

            store.log_file_test(record)

    except ImportError:
        # Telemetry module not available, skip tracking
        pass
    except Exception as e:
        # Don't fail tests due to tracking errors
        import sys

        print(f"\nWarning: File test tracking failed: {e}", file=sys.stderr)


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add ini settings dynamically based on markers
    config.addinivalue_line("markers", "unit: Unit tests that import and test modules directly")
    config.addinivalue_line(
        "markers",
        "integration: Integration tests that run via subprocess (no coverage)",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle coverage properly."""
    # If running with coverage, only run unit tests unless explicitly requested
    # Use getattr to safely check for cov_source (only exists if pytest-cov is installed)
    cov_source = getattr(config.option, "cov_source", None)
    markexpr = getattr(config.option, "markexpr", None)
    if cov_source and not markexpr:
        skip_integration = pytest.mark.skip(reason="Integration tests don't provide coverage")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture(autouse=True, scope="function")
def setup_test_environment(tmp_path, monkeypatch, request):
    """Automatically set up test environment for all tests.

    Creates necessary directories (.empathy, .claude, etc.) in the current directory.
    This prevents tests from failing due to missing directories.

    Args:
        tmp_path: pytest fixture providing a temporary directory
        monkeypatch: pytest fixture for modifying environment
        request: pytest request object

    Yields:
        Path: The current working directory with .empathy structure

    """
    # Save original working directory to restore later
    original_cwd = Path.cwd()

    # Create .empathy directory structure in current directory
    empathy_dir = original_cwd / ".empathy"
    empathy_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories that might be needed
    (empathy_dir / "cost_tracking").mkdir(exist_ok=True)
    (empathy_dir / "telemetry").mkdir(exist_ok=True)
    (empathy_dir / "patterns").mkdir(exist_ok=True)

    # Create .claude directory if needed
    claude_dir = original_cwd / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    yield original_cwd

    # Restore original working directory in case test changed it
    try:
        import os

        os.chdir(original_cwd)
    except (FileNotFoundError, OSError):
        # If original directory was deleted (e.g., by test cleanup), ignore
        pass


@pytest.fixture(autouse=True, scope="function")
def _disable_help_telemetry(monkeypatch):
    """Disable help-query telemetry during tests.

    Prevents tests that exercise `_handle_help_lookup` from writing to
    the user's real `~/.attune/telemetry/help_queries.jsonl`. Tests
    that explicitly want to verify telemetry behavior should enable it
    inside the test via `monkeypatch.delenv("ATTUNE_HELP_TELEMETRY")`.
    """
    monkeypatch.setenv("ATTUNE_HELP_TELEMETRY", "0")


@pytest.fixture(autouse=True, scope="function")
def _stop_leaked_heartbeat_threads():
    """Stop any CrossSessionCoordinator heartbeat thread a test leaks.

    ``CrossSessionCoordinator(auto_announce=True)`` — the default — spawns
    a daemon ``heartbeat-<agent_id>`` thread on construction. A test that
    builds one without ``auto_announce=False`` and never calls ``close()``
    /``stop_heartbeat()`` leaks that thread into the (xdist) worker
    process, where it lingers for the rest of the session. Leaked daemon
    threads are a confounding variable in the xdist end-of-session
    finalize deadlock under investigation, so this teardown stops and
    joins any survivor — keeping each worker (and any captured hang-dump)
    clean. See docs/specs/ci-runner-hang/.
    """
    yield

    import logging
    import threading

    leaked = [
        thread
        for thread in threading.enumerate()
        if thread.is_alive() and thread.name.startswith("heartbeat-")
    ]
    for thread in leaked:
        # The thread target is the coordinator's bound ``_heartbeat_loop``;
        # signalling its stop event wakes the loop out of its interval wait
        # so the join returns promptly.
        coordinator = getattr(getattr(thread, "_target", None), "__self__", None)
        stop_event = getattr(coordinator, "_heartbeat_stop", None)
        if stop_event is not None:
            stop_event.set()
        thread.join(timeout=5)

    if leaked:
        logging.getLogger(__name__).warning(
            "stopped %d leaked heartbeat thread(s): %s — a "
            "CrossSessionCoordinator was constructed without "
            "auto_announce=False and never closed",
            len(leaked),
            [thread.name for thread in leaked],
        )


# =============================================================================
# Additional Shared Fixtures for Testing Improvements
# =============================================================================


@pytest.fixture
def mock_llm_response():
    """Mock LLM API response for testing.

    Returns:
        Callable that creates mock LLM responses

    Example:
        >>> response = mock_llm_response(content="test response")
        >>> assert response["content"] == "test response"

    """

    def _mock_response(content: str = "mock response", model: str = "claude-3-5-sonnet"):
        return {
            "content": content,
            "role": "assistant",
            "model": model,
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "stop_reason": "end_turn",
        }

    return _mock_response


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with common structure.

    Args:
        tmp_path: pytest fixture providing a temporary directory

    Returns:
        Path to temporary project directory with src/, tests/, docs/ structure

    Example:
        >>> project = temp_project_dir
        >>> assert (project / "src").exists()
        >>> assert (project / "README.md").exists()

    """
    project = tmp_path / "project"
    project.mkdir()

    # Create standard project structure
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "docs").mkdir()

    # Create sample files
    (project / "src" / "__init__.py").touch()
    (project / "tests" / "__init__.py").touch()
    (project / "README.md").write_text("# Test Project\n\nA test project for testing.")
    (project / "pyproject.toml").write_text(
        """[project]
name = "test-project"
version = "0.1.0"
""",
    )

    return project


@pytest.fixture
def mock_workflow_config():
    """Mock workflow configuration dictionary.

    Returns:
        Dictionary with standard workflow configuration

    Example:
        >>> config = mock_workflow_config
        >>> assert config["tier_routing"] is True

    """
    return {
        "tier_routing": True,
        "max_tokens": 4000,
        "cache_enabled": True,
        "telemetry_enabled": False,
        "user_id": "test-user",
    }
