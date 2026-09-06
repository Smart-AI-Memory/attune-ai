"""Non-mocked network-resilience tests for the PyPI version check.

``tests/unit/mcp/test_version_check.py`` mocks ``urlopen`` with canned
objects, so it proves the parsing/compare logic but NOT that the real
network path degrades gracefully on slow/error/garbage responses. These
tests stand up a REAL local HTTP stub and drive ``check_for_updates``
through the REAL ``urllib`` stack (real socket, real 2-second timeout) —
only the destination URL is redirected to the stub, behavior is not mocked.

This is the receipt that "network failures are silently ignored"
(the module's promise) actually holds against real failure modes.

Marked ``network`` so CI's parallel unit lane skips it
(``pytest -n auto --timeout-method=thread -m "not network"``): real
sockets + ``--timeout-method=thread`` turn any scheduling-induced hang
into an ``os._exit`` worker crash, and the work distribution that
triggers it shifts whenever unrelated test files are added or removed.
The mocked sibling ``test_version_check.py`` keeps the parse/compare
logic covered in CI; run these locally with ``-m network``.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from attune.mcp import version_check
from tests._inference_guard import loopback_http_fixture

# All tests here drive a real localhost socket; isolate them from the
# parallel xdist lane (see module docstring).
pytestmark = pytest.mark.network

_REAL_URLOPEN = urllib.request.urlopen


class _StubHandler(BaseHTTPRequestHandler):
    """Routes by path to a happy / error / garbage / slow response."""

    def log_message(self, *args):  # noqa: D102 - silence stub access logs
        pass

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/good":
            body = json.dumps({"info": {"version": "999.0.0"}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/error":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"server error")
        elif self.path == "/garbage":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"not valid json {{{")
        elif self.path == "/slow":
            time.sleep(3)  # exceeds the check's hardcoded 2s timeout
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")
            except OSError:
                # The client already timed out at 2s and closed the
                # socket; writing to it now is expected to fail.
                pass
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture
def stub_server():
    """A real localhost HTTP server; yields its base URL.

    Threaded so a slow in-flight handler can't block ``shutdown()`` in
    teardown (the single-threaded server would wait out the ``/slow``
    sleep, racing the per-test timeout).
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with loopback_http_fixture(server.socket):
            yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()


def _redirect_to(stub_url: str):
    """A urlopen replacement that hits the stub via the REAL urllib stack.

    Not a mock: it constructs a real Request to the local stub and calls the
    real ``urlopen`` (preserving the ``timeout`` kwarg), so the socket, HTTP
    round-trip, and timeout behavior are all genuine.
    """

    def _open(req, *args, **kwargs):  # noqa: ANN001
        new_req = urllib.request.Request(stub_url, headers={"Accept": "application/json"})
        return _REAL_URLOPEN(new_req, *args, **kwargs)

    return _open


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    """The module caches in a global; clear it before each case."""
    monkeypatch.setattr(version_check, "_cached_status", None)


def test_real_http_happy_path_parses_version(stub_server, monkeypatch):
    """A real 200 + valid JSON yields the parsed update status."""
    monkeypatch.setattr(
        version_check.urllib.request, "urlopen", _redirect_to(f"{stub_server}/good")
    )
    result = version_check.check_for_updates()
    assert result is not None
    assert result["latest"] == "999.0.0"
    assert result["update_available"] is True  # 999.0.0 > any real current version


def test_real_http_500_degrades_to_none(stub_server, monkeypatch):
    """A real 5xx response degrades to None, not a crash."""
    monkeypatch.setattr(
        version_check.urllib.request, "urlopen", _redirect_to(f"{stub_server}/error")
    )
    assert version_check.check_for_updates() is None


def test_real_http_garbage_body_degrades_to_none(stub_server, monkeypatch):
    """A real 200 with non-JSON body degrades to None."""
    monkeypatch.setattr(
        version_check.urllib.request, "urlopen", _redirect_to(f"{stub_server}/garbage")
    )
    assert version_check.check_for_updates() is None


@pytest.mark.timeout(10)
def test_real_http_timeout_degrades_to_none(stub_server, monkeypatch):
    """A real slow response trips the hardcoded 2s socket timeout -> None.

    Exercises the genuine timeout path (~2s), the one case a mock can't
    faithfully reproduce.
    """
    monkeypatch.setattr(
        version_check.urllib.request, "urlopen", _redirect_to(f"{stub_server}/slow")
    )
    start = time.monotonic()
    assert version_check.check_for_updates() is None
    assert time.monotonic() - start < 3, "should fail at the 2s timeout, not wait for the 3s body"
