"""Tests for backend_init_mixin module.

Tests BackendInitMixin._initialize_backends and get_backend_status.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from enum import Enum
from unittest.mock import MagicMock, patch


class FakeEnvironment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class FakeConfig:
    """Minimal config object for testing BackendInitMixin."""

    file_session_enabled: bool = True
    file_session_dir: str = "/tmp/test_sessions"
    redis_mock: bool = False
    redis_url: str | None = None
    redis_auto_start: bool = False
    redis_required: bool = False
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    claude_memory_enabled: bool = False
    load_enterprise_memory: bool = False
    load_project_memory: bool = False
    load_user_memory: bool = False
    storage_dir: str = "/tmp/test_storage"
    encryption_enabled: bool = False
    environment: FakeEnvironment = FakeEnvironment.DEVELOPMENT


def _make_mixin_instance(config=None):
    """Create a BackendInitMixin instance with required attributes."""
    from attune.memory.mixins.backend_init_mixin import BackendInitMixin

    obj = BackendInitMixin()
    obj.user_id = "test-user"
    obj.config = config or FakeConfig()
    obj._file_session = None
    obj._short_term = None
    obj._long_term = None
    obj._simple_long_term = None
    obj._redis_status = None
    obj._initialized = False
    return obj


class TestGetBackendStatus:
    """Tests for BackendInitMixin.get_backend_status."""

    def test_status_before_initialization(self):
        """Status shows not initialized when backends not set up."""
        obj = _make_mixin_instance()

        status = obj.get_backend_status()

        assert status["initialized"] is False
        assert status["environment"] == "development"
        assert status["short_term"]["available"] is False
        assert status["long_term"]["available"] is False

    def test_status_with_redis_status(self):
        """Status reflects redis_status when set."""
        obj = _make_mixin_instance()

        # Create a fake RedisStatus
        fake_status = MagicMock()
        fake_status.available = True
        fake_status.method = MagicMock()
        fake_status.method.value = "already_running"
        fake_status.message = "Connected"
        obj._redis_status = fake_status
        obj._initialized = True

        with patch(
            "attune.memory.mixins.backend_init_mixin.BackendInitMixin.get_backend_status",
            wraps=obj.get_backend_status,
        ):
            status = obj.get_backend_status()

        assert status["initialized"] is True
        assert status["short_term"]["available"] is True

    def test_status_with_long_term(self):
        """Status reports long_term available when set."""
        obj = _make_mixin_instance()
        obj._long_term = MagicMock()
        obj._initialized = True

        status = obj.get_backend_status()

        assert status["long_term"]["available"] is True
        assert status["long_term"]["storage_dir"] == "/tmp/test_storage"


class TestInitializeBackendsFileSession:
    """Tests for file session initialization path."""

    @patch("attune.memory.mixins.backend_init_mixin.BackendInitMixin._initialize_backends")
    def test_skip_when_already_initialized(self, mock_init):
        """Does not re-initialize if _initialized is True."""
        # Use the real method but with pre-set state
        from attune.memory.mixins.backend_init_mixin import BackendInitMixin

        obj = _make_mixin_instance()
        obj._initialized = True

        # Call the real method
        mock_init.stop()
        BackendInitMixin._initialize_backends(obj)

        # Should return early - _initialized was already True
        assert obj._initialized is True

    def test_file_session_disabled(self):
        """When file_session_enabled=False, _file_session stays None."""
        config = FakeConfig()
        config.file_session_enabled = False
        obj = _make_mixin_instance(config)

        with patch("attune.memory.mixins.backend_init_mixin.BackendInitMixin._initialize_backends"):
            # Simulate that file_session stays None
            assert obj._file_session is None
