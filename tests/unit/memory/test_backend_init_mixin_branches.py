"""Branch-coverage tests for BackendInitMixin._initialize_backends.

Complements tests/unit/memory/test_backend_init_mixin.py, which mostly
patches the method out. This suite actually DRIVES _initialize_backends
through its Redis-backend branches so a regression in the backend
selection logic turns these red:

- the no-redis-installed fallback (ImportError guard),
- explicit redis_mock mode,
- REDIS_URL, auto-start (available + unavailable), and the
  connect-to-existing-server default paths,
- the redis_required hard-fail (RuntimeError), and
- the graceful-degradation excepts (file session, inner connect,
  outer unexpected error).

Source symbols are patched at their DEFINING modules (the method does
`from ..x import Y` at call time), so the real method body executes.
Real RedisStatus/RedisStartMethod are used — not mocks — so the status
assertions pin real behavior.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
from contextlib import ExitStack
from enum import Enum
from unittest.mock import MagicMock, patch

import pytest

from attune.memory.mixins.backend_init_mixin import BackendInitMixin
from attune.memory.redis_bootstrap import RedisStartMethod, RedisStatus


class _Env(Enum):
    DEVELOPMENT = "development"


class _Config:
    """Minimal MemoryConfig stand-in; per-test instances tweak fields."""

    file_session_enabled = True
    file_session_dir = "/tmp/qa_bi_sessions"
    redis_mock = False
    redis_url: str | None = None
    redis_auto_start = False
    redis_required = False
    redis_host = "localhost"
    redis_port = 6379
    claude_memory_enabled = False
    load_enterprise_memory = False
    load_project_memory = False
    load_user_memory = False
    storage_dir = "/tmp/qa_bi_storage"
    encryption_enabled = False
    environment = _Env.DEVELOPMENT


def _make(config=None):
    """Build a bare mixin instance with the attrs UnifiedMemory provides."""
    obj = BackendInitMixin()
    obj.user_id = "qa-user"
    obj.config = config or _Config()
    obj._file_session = None
    obj._short_term = None
    obj._long_term = None
    obj._simple_long_term = None
    obj._redis_status = None
    obj._initialized = False
    return obj


def _patch_non_redis(stack: ExitStack):
    """Patch the always-run file/long-term backends with harmless fakes.

    Returns the FileSessionMemory mock so callers can assert on it.
    """
    fs = MagicMock(name="FileSessionMemory")
    fs.return_value._state.session_id = "sess-1"
    stack.enter_context(patch("attune.memory.file_session.FileSessionMemory", fs))
    stack.enter_context(patch("attune.memory.file_session.FileSessionConfig", MagicMock()))
    stack.enter_context(patch("attune.memory.long_term.SecureMemDocsIntegration", MagicMock()))
    stack.enter_context(patch("attune.memory.long_term.LongTermMemory", MagicMock()))
    stack.enter_context(patch("attune.memory.claude_memory.ClaudeMemoryConfig", MagicMock()))
    return fs


class TestRedisBackendUnavailable:
    """The optional-import guard and explicit-error fallbacks."""

    def test_no_redis_backend_installed_uses_file_only(self):
        """ImportError on the redis backend imports -> file-only, no status."""
        obj = _make()
        with ExitStack() as stack:
            _patch_non_redis(stack)
            # A None entry in sys.modules makes `from ..short_term import X`
            # raise ImportError, flipping _HAS_REDIS_BACKEND to False.
            stack.enter_context(patch.dict(sys.modules, {"attune.memory.short_term": None}))
            obj._initialize_backends()

        assert obj._short_term is None
        assert obj._redis_status is None
        assert obj._initialized is True
        # File session is the primary store and still initializes.
        assert obj._file_session is not None

    def test_redis_init_unexpected_error_degrades(self):
        """A non-RuntimeError inside redis init -> outer except, both None."""
        cfg = _Config()
        cfg.redis_mock = True
        obj = _make(cfg)
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch(
                    "attune.memory.short_term.RedisShortTermMemory",
                    side_effect=ValueError("boom"),
                )
            )
            obj._initialize_backends()

        assert obj._short_term is None
        assert obj._redis_status is None
        assert obj._initialized is True


class TestRedisSelectionPaths:
    """Each branch of the backend-selection ladder picks the right backend."""

    def test_redis_url_marks_already_running(self):
        """redis_url set -> connect via URL, ALREADY_RUNNING status."""
        cfg = _Config()
        cfg.redis_url = "redis://example:6379"
        obj = _make(cfg)
        client = MagicMock(name="redis_client")
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(patch("attune.memory.config.get_redis_memory", return_value=client))
            obj._initialize_backends()

        assert obj._short_term is client
        assert obj._redis_status.available is True
        assert obj._redis_status.method is RedisStartMethod.ALREADY_RUNNING
        assert "REDIS_URL" in obj._redis_status.message

    def test_auto_start_available_constructs_short_term(self):
        """auto_start + available status -> construct a real-mode client."""
        cfg = _Config()
        cfg.redis_auto_start = True
        obj = _make(cfg)
        status = RedisStatus(available=True, method=RedisStartMethod.ALREADY_RUNNING, message="up")
        stm = MagicMock(name="RedisShortTermMemory")
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch("attune.memory.redis_bootstrap.ensure_redis", return_value=status)
            )
            stack.enter_context(patch("attune.memory.short_term.RedisShortTermMemory", stm))
            obj._initialize_backends()

        assert obj._short_term is stm.return_value
        assert obj._redis_status is status
        # Constructed in real (non-mock) mode with the configured host/port.
        _, kwargs = stm.call_args
        assert kwargs["use_mock"] is False
        assert kwargs["host"] == "localhost"
        assert kwargs["port"] == 6379

    def test_auto_start_unavailable_falls_back_to_mock_status(self):
        """auto_start but Redis won't start -> no client, MOCK status."""
        cfg = _Config()
        cfg.redis_auto_start = True
        obj = _make(cfg)
        status = RedisStatus(available=False, method=RedisStartMethod.MOCK, message="down")
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch("attune.memory.redis_bootstrap.ensure_redis", return_value=status)
            )
            obj._initialize_backends()

        assert obj._short_term is None
        assert obj._redis_status.available is False
        assert obj._redis_status.method is RedisStartMethod.MOCK
        assert "file-based storage" in obj._redis_status.message

    def test_existing_redis_connected(self):
        """Default path, server reachable -> use it, ALREADY_RUNNING."""
        obj = _make()
        client = MagicMock()
        client.is_connected.return_value = True
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(patch("attune.memory.config.get_redis_memory", return_value=client))
            obj._initialize_backends()

        assert obj._short_term is client
        assert obj._redis_status.available is True
        assert obj._redis_status.method is RedisStartMethod.ALREADY_RUNNING
        assert "existing Redis" in obj._redis_status.message

    def test_existing_redis_not_connected(self):
        """Default path, server not connected -> drop client, MOCK status."""
        obj = _make()
        client = MagicMock()
        client.is_connected.return_value = False
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(patch("attune.memory.config.get_redis_memory", return_value=client))
            obj._initialize_backends()

        assert obj._short_term is None
        assert obj._redis_status.available is False
        assert obj._redis_status.method is RedisStartMethod.MOCK

    def test_existing_redis_connect_raises_falls_back(self):
        """Default path, get_redis_memory raises -> inner except, MOCK."""
        obj = _make()
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch(
                    "attune.memory.config.get_redis_memory",
                    side_effect=ConnectionError("refused"),
                )
            )
            obj._initialize_backends()

        assert obj._short_term is None
        assert obj._redis_status.available is False
        assert obj._redis_status.method is RedisStartMethod.MOCK


class TestRequiredAndDegradation:
    """redis_required hard-fail and the file-session degradation path."""

    def test_redis_required_but_unavailable_raises(self):
        """redis_required=True with no Redis -> RuntimeError, not swallowed."""
        cfg = _Config()
        cfg.redis_required = True
        obj = _make(cfg)
        client = MagicMock()
        client.is_connected.return_value = False
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(patch("attune.memory.config.get_redis_memory", return_value=client))
            with pytest.raises(RuntimeError, match="Redis is required"):
                obj._initialize_backends()

    def test_file_session_init_failure_degrades_to_none(self):
        """FileSessionMemory raising -> _file_session is None, no crash."""
        cfg = _Config()
        cfg.redis_mock = True  # keep the redis path off the network
        obj = _make(cfg)
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch(
                    "attune.memory.file_session.FileSessionMemory",
                    side_effect=RuntimeError("disk full"),
                )
            )
            obj._initialize_backends()

        assert obj._file_session is None
        assert obj._initialized is True


class TestIdempotencyAndLongTerm:
    """Early-return guard and long-term backend degradation."""

    def test_already_initialized_returns_early(self):
        """_initialized=True -> no backends touched (idempotent re-entry)."""
        obj = _make()
        obj._initialized = True
        obj._initialize_backends()

        # Nothing was set up: the early return fired before any init.
        assert obj._file_session is None
        assert obj._short_term is None
        assert obj._long_term is None
        assert obj._simple_long_term is None

    def test_long_term_init_failure_degrades_to_none(self):
        """SecureMemDocsIntegration raising -> _long_term None, no crash."""
        cfg = _Config()
        cfg.redis_mock = True
        obj = _make(cfg)
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch(
                    "attune.memory.long_term.SecureMemDocsIntegration",
                    side_effect=RuntimeError("no docs"),
                )
            )
            obj._initialize_backends()

        assert obj._long_term is None
        # Simple long-term is a separate try and still initializes.
        assert obj._simple_long_term is not None

    def test_simple_long_term_init_failure_degrades_to_none(self):
        """LongTermMemory raising -> _simple_long_term None, no crash."""
        cfg = _Config()
        cfg.redis_mock = True
        obj = _make(cfg)
        with ExitStack() as stack:
            _patch_non_redis(stack)
            stack.enter_context(
                patch(
                    "attune.memory.long_term.LongTermMemory",
                    side_effect=RuntimeError("no store"),
                )
            )
            obj._initialize_backends()

        assert obj._simple_long_term is None
        assert obj._initialized is True


class TestGetBackendStatusImportGuard:
    """get_backend_status' redis_bootstrap import guard."""

    def test_import_error_marks_mock_true(self):
        """If redis_bootstrap import fails, status is conservatively mock."""
        obj = _make()
        fake_status = MagicMock()
        fake_status.available = True
        fake_status.method.value = "already_running"
        fake_status.message = "Connected"
        obj._redis_status = fake_status

        with patch.dict(sys.modules, {"attune.memory.redis_bootstrap": None}):
            status = obj.get_backend_status()

        assert status["short_term"]["mock"] is True
        assert status["short_term"]["available"] is True
        assert status["short_term"]["method"] == "already_running"
        assert status["short_term"]["message"] == "Connected"
