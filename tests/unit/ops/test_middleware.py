"""Tests for `attune.ops.middleware` — Host header allowlist (DNS-rebinding defense).

See `docs/specs/ops-security-hardening/` for the threat model.
"""

from __future__ import annotations

import logging

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.middleware import compute_allowlist  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _client(tmp_path, *, trusted_hosts=(), host="127.0.0.1", port=8765) -> TestClient:
    """Build an ops app with given trusted-hosts config + bind config."""
    config = build_config(
        project_root=tmp_path,
        host=host,
        port=port,
        trusted_hosts=trusted_hosts,
    )
    return TestClient(create_app(config))


# ---------------------------------------------------------------------------
# compute_allowlist — default + extras logic
# ---------------------------------------------------------------------------


def test_compute_allowlist_loopback_aliases():
    """Binding to 127.0.0.1 includes localhost + 127.0.0.1 + 0.0.0.0 if matched."""
    allowed = compute_allowlist("127.0.0.1", 8765)
    assert "127.0.0.1:8765" in allowed
    assert "localhost:8765" in allowed


def test_compute_allowlist_localhost_bind():
    """Binding to localhost still includes 127.0.0.1 alias."""
    allowed = compute_allowlist("localhost", 8765)
    assert "localhost:8765" in allowed
    assert "127.0.0.1:8765" in allowed


def test_compute_allowlist_zero_zero_zero_zero_bind():
    """Binding to 0.0.0.0 (all interfaces) includes loopback aliases."""
    allowed = compute_allowlist("0.0.0.0", 8765)
    assert "0.0.0.0:8765" in allowed
    assert "localhost:8765" in allowed
    assert "127.0.0.1:8765" in allowed


def test_compute_allowlist_extras_without_port_get_both_http_and_https():
    """A --trusted-host without :port adds both :80 and :443."""
    allowed = compute_allowlist("127.0.0.1", 8765, extras=["my.example.com"])
    assert "my.example.com:80" in allowed
    assert "my.example.com:443" in allowed
    assert "my.example.com" in allowed  # also the bare form


def test_compute_allowlist_extras_with_port_stay_exact():
    """A --trusted-host with :port is added as-is, NOT padded with 80/443."""
    allowed = compute_allowlist("127.0.0.1", 8765, extras=["my.example.com:8443"])
    assert "my.example.com:8443" in allowed
    # Should NOT have added 80/443 — user specified a port already
    assert "my.example.com:80" not in allowed
    assert "my.example.com:443" not in allowed


def test_compute_allowlist_non_loopback_bind_does_not_add_loopback_aliases():
    """Binding to a real interface (e.g. 192.168.1.5) doesn't add loopback aliases."""
    allowed = compute_allowlist("192.168.1.5", 8765)
    assert "192.168.1.5:8765" in allowed
    assert "localhost:8765" not in allowed
    assert "127.0.0.1:8765" not in allowed


# ---------------------------------------------------------------------------
# Middleware behavior — accept / reject / log
# ---------------------------------------------------------------------------


def test_middleware_allows_loopback_localhost(tmp_path):
    """Host: localhost:8765 passes through to the route."""
    client = _client(tmp_path)
    r = client.get("/api/info", headers={"host": "localhost:8765"})
    assert r.status_code == 200


def test_middleware_allows_127_0_0_1(tmp_path):
    """Host: 127.0.0.1:8765 passes through."""
    client = _client(tmp_path)
    r = client.get("/api/info", headers={"host": "127.0.0.1:8765"})
    assert r.status_code == 200


def test_middleware_rejects_unknown_host(tmp_path):
    """Host: evil.com:8765 is rejected with 400 and the expected detail."""
    client = _client(tmp_path)
    r = client.get("/api/info", headers={"host": "evil.com:8765"})
    assert r.status_code == 400
    assert r.json() == {"detail": "untrusted Host header"}


def test_middleware_rejects_missing_host_header(tmp_path):
    """Missing Host header is treated as untrusted."""
    client = _client(tmp_path)
    # TestClient/httpx automatically populates Host. Use empty string to
    # exercise the "no host" code path explicitly.
    r = client.get("/api/info", headers={"host": ""})
    assert r.status_code == 400


def test_middleware_is_case_insensitive(tmp_path):
    """Host: LOCALHOST:8765 (uppercase) passes — comparison is case-insensitive."""
    client = _client(tmp_path)
    r = client.get("/api/info", headers={"host": "LOCALHOST:8765"})
    assert r.status_code == 200


def test_middleware_logs_rejection(tmp_path, caplog):
    """Rejected requests log a WARN line with the offending host value."""
    client = _client(tmp_path)
    with caplog.at_level(logging.WARNING, logger="attune.ops.middleware"):
        r = client.get("/api/info", headers={"host": "evil.com:8765"})
    assert r.status_code == 400
    assert any("evil.com:8765" in record.message for record in caplog.records)


def test_middleware_truncates_pathological_host_in_log(tmp_path, caplog):
    """A very long Host header value is truncated to 200 chars in the log."""
    client = _client(tmp_path)
    huge_host = "a" * 500
    with caplog.at_level(logging.WARNING, logger="attune.ops.middleware"):
        r = client.get("/api/info", headers={"host": huge_host})
    assert r.status_code == 400
    # No record should contain more than 200 chars from the huge_host
    for record in caplog.records:
        if "a" * 200 in record.message:
            # 200 chars is fine, but 500 chars would mean no truncation
            assert "a" * 201 not in record.message


def test_trusted_host_flag_widens_allowlist(tmp_path):
    """A --trusted-host value is accepted in the Host header."""
    client = _client(tmp_path, trusted_hosts=("my-tunnel.example.com",))
    # The bare hostname (no port) and the http (80) / https (443) variants
    # all work.
    r1 = client.get("/api/info", headers={"host": "my-tunnel.example.com"})
    assert r1.status_code == 200
    r2 = client.get("/api/info", headers={"host": "my-tunnel.example.com:80"})
    assert r2.status_code == 200
    r3 = client.get("/api/info", headers={"host": "my-tunnel.example.com:443"})
    assert r3.status_code == 200


def test_trusted_host_flag_with_explicit_port(tmp_path):
    """A --trusted-host with :port is accepted only at that exact port."""
    client = _client(tmp_path, trusted_hosts=("my-tunnel.example.com:8443",))
    r_ok = client.get("/api/info", headers={"host": "my-tunnel.example.com:8443"})
    assert r_ok.status_code == 200
    # Different port → rejected (since user specified a port, no padding).
    r_bad = client.get("/api/info", headers={"host": "my-tunnel.example.com:9999"})
    assert r_bad.status_code == 400


def test_middleware_runs_before_route_handler(tmp_path):
    """Even a 404'd path returns 400 first if the Host is untrusted —
    confirms the middleware runs ahead of routing."""
    client = _client(tmp_path)
    r = client.get("/this-path-does-not-exist", headers={"host": "evil.com:8765"})
    # 400 from middleware, not 404 from FastAPI's not-found handler.
    assert r.status_code == 400
