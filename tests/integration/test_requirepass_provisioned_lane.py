"""Self-provisioning requirepass regression lane — redis-config-truth rct-5.

R4's non-mocked round trip: the lane SPAWNS its own ephemeral
``redis-server --requirepass`` (random password, scratch port,
auto-teardown) whenever the binary is on PATH — it never depends on a
pre-configured requirepass instance, so the core incident AC is
verified on every host with the binary instead of only on machines
that happen to run hardened Redis. The ONLY permitted skip condition
is binary absence, and a meta-test pins that contract.

The incident shape (password-less ``REDIS_URL`` + ``REDIS_PASSWORD``
env) authenticates through the canonical resolver AND the migrated
consumers (rct-4) against the live provisioned server.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

# Plain import, NOT importorskip (codex D11 lane): redis is a CORE
# attune-ai dependency, so its absence is a broken environment that
# must FAIL loudly — an importorskip here would be a second skip
# condition evading the lane's skip-only-on-binary-absence contract.
import redis as redis_lib

#: The lane's ONLY skip condition (meta-test pins this).
REDIS_SERVER_BIN = shutil.which("redis-server")

pytestmark = pytest.mark.xdist_group("requirepass-lane")

#: Env vars scrubbed for hermeticity in every live test.
_CONNECTION_AND_TOGGLE_VARS = (
    "REDIS_URL",
    "REDIS_PRIVATE_URL",
    "REDIS_PUBLIC_URL",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DB",
    "REDIS_USER",
    "REDIS_PASSWORD",
    "REDIS_MODE",
    "ATTUNE_REDIS_MOCK",
    "EMPATHY_REDIS_MOCK",
)


def _scrub_env(monkeypatch) -> None:
    for var in _CONNECTION_AND_TOGGLE_VARS:
        monkeypatch.delenv(var, raising=False)


def _free_port() -> int:
    while True:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = int(s.getsockname()[1])
        # Never provision on the default port — the non-default-port
        # independence proof must hold structurally, not by luck of
        # the kernel's ephemeral range (codex D11 lane).
        if port != 6379:
            return port


@pytest.fixture(scope="module")
def provisioned_server():
    """Ephemeral requirepass redis-server: random password, scratch port."""
    if REDIS_SERVER_BIN is None:
        pytest.skip("redis-server binary not on PATH (the lane's only skip)")
    password = secrets.token_urlsafe(16)
    port = _free_port()
    proc = subprocess.Popen(  # noqa: S603 — fixed argv, vetted binary path
        [
            REDIS_SERVER_BIN,
            "--port",
            str(port),
            "--requirepass",
            password,
            "--bind",
            "127.0.0.1",
            "--save",
            "",
            "--appendonly",
            "no",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        client = redis_lib.Redis(
            host="127.0.0.1", port=port, password=password, socket_connect_timeout=0.5
        )
        for _ in range(100):
            try:
                if client.ping():
                    break
            except (redis_lib.exceptions.ConnectionError, redis_lib.exceptions.TimeoutError):
                time.sleep(0.1)
        else:
            pytest.fail("provisioned redis-server did not become ready in 10s")
        yield {"port": port, "password": password}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture()
def incident_env(provisioned_server, monkeypatch):
    """The R4 incident shape pointed at the provisioned server."""
    _scrub_env(monkeypatch)
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{provisioned_server['port']}/0")
    monkeypatch.setenv("REDIS_PASSWORD", provisioned_server["password"])
    yield provisioned_server


class TestIncidentShapeLive:
    def test_resolver_url_authenticates(self, incident_env):
        """The merged URL round-trips a PING against requirepass."""
        from attune.memory.config import resolve_redis_connection

        resolved = resolve_redis_connection()
        assert resolved.source_map["password"] == "REDIS_PASSWORD"
        client = redis_lib.Redis.from_url(resolved.url, socket_connect_timeout=2)
        assert client.ping() is True

    def test_recall_reader_authenticates(self, incident_env):
        """rct-4 consumer: connect_recall_redis round-trips live."""
        from attune.memory import recall_redis

        client = recall_redis.connect_recall_redis(socket_connect_timeout=2)
        assert client.ping() is True

    def test_classifier_reports_healthy(self, incident_env):
        from attune.memory.features import MemoryFeatures, RedisHealthState

        report = MemoryFeatures.classify_redis_health()
        assert report.state is RedisHealthState.HEALTHY

    def test_wrong_password_classifies_degraded_auth_live(self, provisioned_server, monkeypatch):
        """A real NOAUTH/WRONGPASS from a real server → degraded_auth."""
        from attune.memory.features import MemoryFeatures, RedisHealthState

        _scrub_env(monkeypatch)
        monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{provisioned_server['port']}/0")
        monkeypatch.setenv("REDIS_PASSWORD", "definitely-wrong")
        report = MemoryFeatures.classify_redis_health()
        assert report.state is RedisHealthState.DEGRADED_AUTH
        assert provisioned_server["password"] not in (report.detail or "")

    def test_missing_password_fails_auth_live(self, provisioned_server, monkeypatch):
        """The pre-fix incident: bare URL, no password → auth rejected."""
        _scrub_env(monkeypatch)
        monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{provisioned_server['port']}/0")
        from attune.memory.config import resolve_redis_connection

        resolved = resolve_redis_connection()
        client = redis_lib.Redis.from_url(resolved.url, socket_connect_timeout=2)
        with pytest.raises(redis_lib.exceptions.AuthenticationError):
            client.ping()


class TestLaneContract:
    """The rct-5 meta-contract: skip ONLY when the binary is absent."""

    def test_lane_runs_when_binary_present(self, provisioned_server):
        """Meta-test: with redis-server on PATH, provisioning MUST work
        — a lane that skips or fails here while the binary exists is
        the drift this test forbids."""
        client = redis_lib.Redis(
            host="127.0.0.1",
            port=provisioned_server["port"],
            password=provisioned_server["password"],
            socket_connect_timeout=2,
        )
        assert client.ping() is True

    def test_skip_guard_is_binary_absence_only(self):
        """Pin the ONLY skip: this module contains exactly one
        ``pytest.skip`` call, guarded by ``REDIS_SERVER_BIN is None``."""
        source = Path(__file__).read_text(encoding="utf-8")
        # Literal splits so these counting lines don't count themselves.
        # The importorskip CALL form is ALSO forbidden (codex D11
        # lane): it would be a second skip condition evading this very
        # count — redis is a core dependency, absence must FAIL.
        assert source.count("pytest.importor" + "skip(") == 0, (
            "pytest.importorskip call found — it adds a skip condition "
            "the rct-5 contract forbids"
        )
        skip_count = source.count("pytest." + "skip(")
        assert skip_count == 1, (
            f"{skip_count} pytest.skip calls — the lane may skip ONLY on "
            "binary absence (rct-5 AC); remove the extra skip or justify "
            "it in the spec"
        )
        assert "if REDIS_SERVER_BIN is None:" in source

    def test_no_dependence_on_preconfigured_instance(self, provisioned_server):
        """The provisioned port differs from the default 6379 — proof
        the lane is NOT riding a pre-configured local instance."""
        assert provisioned_server["port"] != 6379
