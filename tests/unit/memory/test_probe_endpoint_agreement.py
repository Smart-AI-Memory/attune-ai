"""The availability oracle must probe THE configured endpoint (H1).

Library-review class H1: three probes decided Redis availability from a
hard-coded ``127.0.0.1:6379`` while clients connected to the RESOLVED
endpoint. On disagreement the store silently became an in-process mock,
so writes were accepted, reported successful, and lost.

Class M ("the mock defined the contract") applies directly here: the
existing suite patches ``_check_server_reachable`` 23 times, so the
endpoint the probe actually contacts was never exercised — which is why
H1 reached production. These tests therefore run a REAL TCP server
speaking REAL RESP and drive the REAL redis-py client. Nothing on the
resolve-then-connect path is patched; the stub is a genuine endpoint at
a genuine address, and what is under test is which address gets dialled.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import socket
import threading

import pytest

pytest.importorskip("redis")


def _read_command(rfile) -> list[bytes] | None:
    """Read one RESP command (array or inline) from a connection."""
    line = rfile.readline()
    if not line:
        return None
    if not line.startswith(b"*"):
        return line.strip().split()
    parts = []
    for _ in range(int(line[1:])):
        header = rfile.readline()
        if not header.startswith(b"$"):
            return None
        payload = rfile.read(int(header[1:]) + 2)
        parts.append(payload[:-2])
    return parts


class _RespStub:
    """A real listening socket that answers PING like a Redis would.

    Not a stand-in for the probe or the resolver — only for the server
    on the far side of a real connection, so the test can pin an
    endpoint at an address that is provably not the hard-coded one.
    """

    def __init__(self) -> None:
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self.port: int = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    #: RESP3 handshake reply — redis-py >= 5.1 opens with ``HELLO 3``.
    _HELLO_REPLY = (
        b"%3\r\n"
        b"$6\r\nserver\r\n$5\r\nredis\r\n"
        b"$7\r\nversion\r\n$5\r\n7.0.0\r\n"
        b"$5\r\nproto\r\n:3\r\n"
    )

    def _handle(self, conn: socket.socket) -> None:
        with conn, conn.makefile("rb") as rfile:
            while True:
                command = _read_command(rfile)
                if command is None:
                    return
                verb = command[0].upper() if command else b""
                if verb == b"HELLO":
                    conn.sendall(self._HELLO_REPLY)
                elif verb == b"PING":
                    conn.sendall(b"+PONG\r\n")
                else:
                    conn.sendall(b"+OK\r\n")

    def close(self) -> None:
        self._stop.set()
        self._sock.close()


@pytest.fixture()
def resp_stub():
    stub = _RespStub()
    yield stub
    stub.close()


@pytest.fixture()
def closed_port() -> int:
    """A port with nothing listening on it."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(autouse=True)
def clean_redis_env(monkeypatch):
    for var in (
        "REDIS_URL",
        "REDIS_PRIVATE_URL",
        "REDIS_PUBLIC_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_USER",
        "REDIS_PASSWORD",
    ):
        monkeypatch.delenv(var, raising=False)


def _probes():
    """Every availability oracle in the tree, called the way callers call it."""
    from attune.memory.features import MemoryFeatures
    from attune.memory.redis_auto_detect import RedisAutoDetector
    from attune.memory.redis_bootstrap import _check_redis_running

    return {
        "features.is_redis_running": MemoryFeatures.is_redis_running,
        "redis_bootstrap._check_redis_running": _check_redis_running,
        "auto_detect._check_server_reachable": RedisAutoDetector()._check_server_reachable,
    }


def test_probes_reach_a_non_default_configured_endpoint(monkeypatch, resp_stub):
    """REDIS_URL names the target; the probe must dial THAT target."""
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{resp_stub.port}/0")

    for name, probe in _probes().items():
        assert probe() is True, f"{name} did not reach the configured endpoint"


def test_probes_report_down_when_the_configured_endpoint_is_down(
    monkeypatch, resp_stub, closed_port
):
    """A live server at some OTHER address must not read as available.

    Paired with the test above this pins the oracle in both directions,
    so it fails whether or not the machine happens to run a Redis on the
    old hard-coded 6379.
    """
    assert resp_stub.port != closed_port
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{closed_port}/0")

    for name, probe in _probes().items():
        assert probe() is False, f"{name} reported a down endpoint as available"


def test_detector_result_follows_the_configured_endpoint(monkeypatch, resp_stub):
    """The cached detect() result — what picks real store vs mock."""
    from attune.memory import redis_auto_detect

    monkeypatch.setattr(redis_auto_detect, "_cached_result", None)
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{resp_stub.port}/0")

    result = redis_auto_detect.RedisAutoDetector().detect()

    assert result.server_reachable is True
    assert result.available is True


def test_probe_client_carries_resolved_credentials_and_endpoint():
    """The probe connects with the same spec real clients use."""
    from attune.memory.config import redis_probe_client

    env = {
        "REDIS_URL": "redis://cache.internal:6380/3",
        "REDIS_PASSWORD": "s3cret",
    }  # pragma: allowlist secret
    kwargs = redis_probe_client(env=env).connection_pool.connection_kwargs

    assert kwargs["host"] == "cache.internal"
    assert kwargs["port"] == 6380
    assert kwargs["db"] == 3
    assert kwargs["password"] == "s3cret"  # pragma: allowlist secret
