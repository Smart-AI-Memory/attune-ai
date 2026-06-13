"""Behavioral tests for run_api_server (control_panel_api).

PR 2 of the control_panel_api effort. run_api_server binds a socket,
registers process signal handlers, and calls the blocking
serve_forever — so HTTPServer, signal, and the serve loop are mocked.
What's actually exercised: handler class-attribute wiring, rate-limit
enable/disable, API-key auth setup, the SSL cert-present vs cert-missing
branches, and the graceful shutdown handler.
"""

import pytest

import attune.memory.control_panel_api as cpa
from attune.memory.control_panel_api import MemoryAPIHandler, run_api_server


class _FakeServer:
    """Stand-in for HTTPServer that never binds or blocks."""

    instances: list["_FakeServer"] = []

    def __init__(self, address, handler):
        self.address = address
        self.handler = handler
        self.socket = "raw-socket"
        self.served = False
        self.shut = False
        _FakeServer.instances.append(self)

    def serve_forever(self):
        self.served = True

    def shutdown(self):
        self.shut = True


class _FakePanel:
    def __init__(self, stop_ok=True):
        self._stop_ok = stop_ok
        self.stop_called = False

    def stop_redis(self):
        self.stop_called = True
        return self._stop_ok


class _FakeSSLContext:
    def __init__(self, protocol):
        self.protocol = protocol
        self.minimum_version = None
        self.loaded = None

    def load_cert_chain(self, certfile, keyfile):
        self.loaded = (certfile, keyfile)

    def wrap_socket(self, sock, server_side=False):
        return "wrapped-socket"


@pytest.fixture
def captured_signals(monkeypatch):
    """Capture signal handlers instead of registering them on the process."""
    handlers = {}
    monkeypatch.setattr(cpa.signal, "signal", lambda sig, fn: handlers.__setitem__(sig, fn))
    return handlers


@pytest.fixture(autouse=True)
def _reset_server(monkeypatch):
    """Swap in the fake HTTPServer and reset handler class attributes."""
    _FakeServer.instances.clear()
    monkeypatch.setattr(cpa, "HTTPServer", _FakeServer)
    # Avoid leaking handler class attributes across tests.
    monkeypatch.setattr(MemoryAPIHandler, "panel", None, raising=False)
    monkeypatch.setattr(MemoryAPIHandler, "rate_limiter", None, raising=False)
    monkeypatch.setattr(MemoryAPIHandler, "api_auth", None, raising=False)


def test_run_wires_handler_attributes_and_serves(captured_signals):
    panel = _FakePanel()
    run_api_server(panel, host="localhost", port=9999, enable_rate_limit=True)

    assert MemoryAPIHandler.panel is panel
    assert MemoryAPIHandler.rate_limiter is not None  # RateLimiter created
    assert MemoryAPIHandler.api_auth is not None
    server = _FakeServer.instances[-1]
    assert server.address == ("localhost", 9999)
    assert server.served is True  # serve_forever reached


def test_rate_limit_disabled_sets_none(captured_signals):
    run_api_server(_FakePanel(), enable_rate_limit=False)
    assert MemoryAPIHandler.rate_limiter is None


def test_api_key_enables_auth(captured_signals):
    run_api_server(_FakePanel(), api_key="sekret")  # pragma: allowlist secret
    assert MemoryAPIHandler.api_auth.enabled is True


def test_ssl_enabled_when_cert_and_key_exist(captured_signals, monkeypatch, tmp_path):
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    cert.write_text("x")
    key.write_text("y")
    monkeypatch.setattr(cpa.ssl, "SSLContext", _FakeSSLContext)

    run_api_server(
        _FakePanel(),
        ssl_certfile=str(cert),
        ssl_keyfile=str(key),
    )
    server = _FakeServer.instances[-1]
    assert server.socket == "wrapped-socket"  # TLS wrap applied


def test_ssl_missing_files_logs_warning_and_stays_http(captured_signals, monkeypatch):
    warned = {}
    monkeypatch.setattr(
        cpa.logger, "warning", lambda event, **kw: warned.update({"event": event, **kw})
    )
    run_api_server(
        _FakePanel(),
        ssl_certfile="/no/such/cert.pem",
        ssl_keyfile="/no/such/key.pem",
    )
    server = _FakeServer.instances[-1]
    assert server.socket == "raw-socket"  # not wrapped
    assert warned["event"] == "ssl_cert_not_found"


def test_shutdown_handler_stops_server_and_exits(captured_signals):
    import signal as _signal

    panel = _FakePanel()
    run_api_server(panel, enable_rate_limit=False)

    handler = captured_signals[_signal.SIGINT]
    with pytest.raises(SystemExit):
        handler(_signal.SIGINT, None)

    server = _FakeServer.instances[-1]
    assert server.shut is True
    assert panel.stop_called is True
