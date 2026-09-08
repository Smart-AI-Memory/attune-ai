"""The MCP version check runs at most once per process and never in tests.

Regression for CI run 34173042218 (2026-09-08): every ``AttuneMCPServer``
construction started its own ``check_for_updates`` thread; a per-test
server fixture under xdist ran several concurrently, two raced inside
``ssl.load_default_certs`` and the worker segfaulted.
"""

from __future__ import annotations

import os
import threading

import pytest

from attune.mcp import version_check as vc


@pytest.fixture
def fresh_single_flight(monkeypatch):
    """Reset the process-wide started flag and stub the network call."""
    monkeypatch.setattr(vc, "_started", False)
    calls: list[str] = []
    done = threading.Event()

    def fake_check():
        calls.append(threading.current_thread().name)
        done.set()
        return None

    monkeypatch.setattr(vc, "check_for_updates", fake_check)
    return calls, done


def test_suite_opts_out_of_the_version_check():
    """The conftest pin every worker inherits (suite-managed, not scrubbed)."""
    assert os.environ.get("ATTUNE_VERSION_CHECK") == "0"
    assert vc.background_check_enabled() is False


@pytest.mark.parametrize("value", ["0", "false", "NO", " off "])
def test_opt_out_values_start_nothing(monkeypatch, fresh_single_flight, value):
    calls, _ = fresh_single_flight
    monkeypatch.setenv("ATTUNE_VERSION_CHECK", value)
    assert vc.start_background_check() is None
    assert calls == []
    assert vc._started is False


def test_single_flight_starts_one_thread_per_process(monkeypatch, fresh_single_flight):
    calls, done = fresh_single_flight
    monkeypatch.delenv("ATTUNE_VERSION_CHECK", raising=False)
    first = vc.start_background_check()
    assert isinstance(first, threading.Thread)
    assert first.daemon is True
    assert vc.start_background_check() is None
    assert vc.start_background_check() is None
    assert done.wait(5), "the single check thread never ran"
    first.join(5)
    assert calls == ["attune-version-check"]


def test_two_servers_share_one_check_thread(monkeypatch, fresh_single_flight, tmp_path):
    calls, done = fresh_single_flight
    monkeypatch.delenv("ATTUNE_VERSION_CHECK", raising=False)
    from attune.mcp.server import AttuneMCPServer

    AttuneMCPServer(workspace_root=str(tmp_path))
    AttuneMCPServer(workspace_root=str(tmp_path))
    assert done.wait(5)
    for t in threading.enumerate():
        if t.name == "attune-version-check":
            t.join(5)
    assert calls == ["attune-version-check"]


def test_server_under_suite_default_never_calls_pypi(fresh_single_flight, tmp_path):
    calls, _ = fresh_single_flight
    from attune.mcp.server import AttuneMCPServer

    AttuneMCPServer(workspace_root=str(tmp_path))
    assert calls == []
    assert vc._started is False


def test_stub_is_resolved_at_start_time(monkeypatch, fresh_single_flight):
    """Existing tests patch ``version_check.check_for_updates``; honor that."""
    calls, done = fresh_single_flight
    monkeypatch.delenv("ATTUNE_VERSION_CHECK", raising=False)
    thread = vc.start_background_check()
    assert thread is not None
    thread.join(5)
    assert done.is_set() and calls
