"""Tests for the auth-aware recall Redis factory (R3).

The factory injects REDIS_PASSWORD so a single env var makes every recall/ops
reader authenticate under `requirepass`, without disturbing URLs that already
embed credentials. redis.Redis.from_url is patched — no live socket.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from attune.memory import recall_redis


def _fake_redis():
    """A stand-in `redis` module capturing from_url(url, **kwargs)."""
    calls: list[tuple] = []
    mod = SimpleNamespace(
        Redis=SimpleNamespace(from_url=lambda url, **kw: calls.append((url, kw)) or MagicMock())
    )
    return mod, calls


def _scrub_connection_env(monkeypatch):
    """Hermetic: dotenv injects ambient REDIS_* into attune processes."""
    for var in (
        "REDIS_URL",
        "REDIS_PRIVATE_URL",
        "REDIS_PUBLIC_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_PASSWORD",
        "REDIS_USER",
    ):
        monkeypatch.delenv(var, raising=False)


def test_resolve_url_prefers_arg_then_resolver_then_default(monkeypatch):
    _scrub_connection_env(monkeypatch)
    assert recall_redis.resolve_url() == recall_redis.DEFAULT_RECALL_URL
    monkeypatch.setenv("REDIS_URL", "redis://envhost:6379/1")
    assert recall_redis.resolve_url() == "redis://envhost:6379/1"
    assert recall_redis.resolve_url("redis://arg:6379/2") == "redis://arg:6379/2"


def test_resolver_embeds_password_when_no_explicit_url(monkeypatch):
    """rct-4: no separate kwarg injection — the resolver URL carries it."""
    _scrub_connection_env(monkeypatch)
    monkeypatch.setenv("REDIS_PASSWORD", "s3cret")  # pragma: allowlist secret
    fake, calls = _fake_redis()
    with patch.dict(sys.modules, {"redis": fake}):
        recall_redis.connect_recall_redis()
    url, kw = calls[0]
    assert url == "redis://:s3cret@127.0.0.1:6379/0"  # pragma: allowlist secret
    assert "password" not in kw
    assert kw["decode_responses"] is True


def test_injects_resolver_password_into_bare_explicit_url(monkeypatch):
    _scrub_connection_env(monkeypatch)
    monkeypatch.setenv("REDIS_PASSWORD", "s3cret")  # pragma: allowlist secret
    fake, calls = _fake_redis()
    with patch.dict(sys.modules, {"redis": fake}):
        recall_redis.connect_recall_redis("redis://127.0.0.1:6390/2")
    url, kw = calls[0]
    assert url == "redis://127.0.0.1:6390/2"
    assert kw["password"] == "s3cret"  # pragma: allowlist secret
    assert kw["decode_responses"] is True


def test_does_not_override_url_embedded_credentials(monkeypatch):
    monkeypatch.setenv("REDIS_PASSWORD", "envpass")
    fake, calls = _fake_redis()
    with patch.dict(sys.modules, {"redis": fake}):
        recall_redis.connect_recall_redis("rediss://user:urlpass@host:6379/0")
    _, kw = calls[0]
    assert "password" not in kw  # URL creds win; env secret not injected


def test_no_password_when_unset(monkeypatch):
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    fake, calls = _fake_redis()
    with patch.dict(sys.modules, {"redis": fake}):
        recall_redis.connect_recall_redis(socket_connect_timeout=2)
    _, kw = calls[0]
    assert "password" not in kw
    assert kw["socket_connect_timeout"] == 2  # passthrough kwargs preserved


def test_import_error_propagates(monkeypatch):
    monkeypatch.setitem(sys.modules, "redis", None)  # forces ImportError on `import redis`
    with pytest.raises(ImportError):
        recall_redis.connect_recall_redis()
