"""Unit tests for ``AMSMemoryBackend.prune`` (30-day retention parity).

The AMS backend retires long-term findings older than the configured TTL
via the client's ``forget_long_term_memories(ForgetPolicy(...))``, scoped to
the backend's namespace. These tests run unconditionally in CI (where the
optional ``agent-memory-client`` dep is absent) by injecting a fake
``agent_memory_client.models.ForgetPolicy`` into ``sys.modules`` and
patching ``_run_sync`` to an identity passthrough, so neither a live AMS
server nor the real client package is required.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

import attune_redis.memory as ams
from attune_redis.memory import _DEFAULT_TTL_DAYS, AMSMemoryBackend


class _FakeForgetPolicy:
    """Stand-in capturing the ``max_age_days`` the backend forgets with."""

    def __init__(self, max_age_days: int) -> None:
        self.max_age_days = max_age_days


class _FakeResponse:
    def __init__(self, deleted: int) -> None:
        self.deleted = deleted


@pytest.fixture
def fake_forget_policy(monkeypatch):
    """Inject a fake ``agent_memory_client.models`` so the function-local
    ``from agent_memory_client.models import ForgetPolicy`` resolves."""
    pkg = types.ModuleType("agent_memory_client")
    models = types.ModuleType("agent_memory_client.models")
    models.ForgetPolicy = _FakeForgetPolicy
    monkeypatch.setitem(sys.modules, "agent_memory_client", pkg)
    monkeypatch.setitem(sys.modules, "agent_memory_client.models", models)
    return _FakeForgetPolicy


@pytest.fixture
def backend(monkeypatch):
    """An ``AMSMemoryBackend`` with a fake client, bypassing the real
    ``__init__`` (which would construct a live HTTP client)."""
    be = object.__new__(AMSMemoryBackend)
    be._client = MagicMock()
    be._namespace = "itest-ns"
    # _run_sync would await the coroutine; the fake client returns a plain
    # value, so pass it straight through.
    monkeypatch.setattr(ams, "_run_sync", lambda coro: coro)
    return be


def test_prune_default_uses_30_days(backend, fake_forget_policy):
    backend._client.forget_long_term_memories.return_value = _FakeResponse(deleted=4)
    deleted = backend.prune()
    assert deleted == 4
    policy = backend._client.forget_long_term_memories.call_args.args[0]
    assert isinstance(policy, _FakeForgetPolicy)
    assert policy.max_age_days == _DEFAULT_TTL_DAYS == 30
    assert backend._client.forget_long_term_memories.call_args.kwargs["namespace"] == "itest-ns"


def test_prune_explicit_max_age(backend, fake_forget_policy):
    backend._client.forget_long_term_memories.return_value = _FakeResponse(deleted=1)
    deleted = backend.prune(max_age_days=10)
    assert deleted == 1
    assert backend._client.forget_long_term_memories.call_args.args[0].max_age_days == 10


def test_prune_floors_age_at_one_day(backend, fake_forget_policy):
    # A zero/negative window would forget everything; the backend floors at 1.
    backend._client.forget_long_term_memories.return_value = _FakeResponse(deleted=0)
    backend.prune(max_age_days=0)
    assert backend._client.forget_long_term_memories.call_args.args[0].max_age_days == 1


def test_prune_returns_zero_on_missing_deleted(backend, fake_forget_policy):
    # A response without a usable ``deleted`` count coerces to 0, no raise.
    backend._client.forget_long_term_memories.return_value = object()
    assert backend.prune() == 0


def test_prune_swallows_client_error(backend, fake_forget_policy):
    backend._client.forget_long_term_memories.side_effect = RuntimeError("AMS 503")
    assert backend.prune() == 0
