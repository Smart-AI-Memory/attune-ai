"""Tests for Redis Configuration Module

Tests cover:
- URL parsing (redis:// and rediss://)
- Environment-based configuration
- Mock mode detection
- get_redis_memory with various parameters
- Railway deployment helpers

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import os
from unittest.mock import patch

import pytest

from attune.memory.short_term import RedisConfig

# Check if Redis is actually running locally
try:
    import redis as _redis_mod

    _r = _redis_mod.Redis(host="localhost", port=6379, socket_connect_timeout=1)
    _r.ping()
    _REDIS_RUNNING = True
except Exception:
    _REDIS_RUNNING = False
from attune.redis_config import (
    _resolve_redis_mode,
    check_redis_connection,
    get_railway_redis,
    get_redis_config,
    get_redis_config_dict,
    get_redis_memory,
    parse_redis_url,
)


class TestParseRedisUrl:
    """Test Redis URL parsing"""

    def test_parse_standard_url(self):
        """Test parsing standard redis:// URL"""
        url = "redis://user:secret@redis.example.com:6380/1"
        result = parse_redis_url(url)

        assert result["host"] == "redis.example.com"
        assert result["port"] == 6380
        assert result["password"] == "secret"
        assert result["db"] == 1
        assert result["ssl"] is False

    def test_parse_ssl_url(self):
        """Test parsing rediss:// URL (SSL enabled)"""
        url = "rediss://user:secret@redis.example.com:6380/2"
        result = parse_redis_url(url)

        assert result["host"] == "redis.example.com"
        assert result["ssl"] is True
        assert result["db"] == 2

    def test_parse_minimal_url(self):
        """Test parsing minimal URL"""
        url = "redis://localhost"
        result = parse_redis_url(url)

        assert result["host"] == "localhost"
        assert result["port"] == 6379  # default
        assert result["password"] is None
        assert result["db"] == 0  # default
        assert result["ssl"] is False

    def test_parse_url_with_port_only(self):
        """Test parsing URL with just host and port"""
        url = "redis://redis.example.com:6380"
        result = parse_redis_url(url)

        assert result["host"] == "redis.example.com"
        assert result["port"] == 6380
        assert result["db"] == 0

    def test_parse_url_no_password(self):
        """Test parsing URL without password"""
        url = "redis://redis.example.com:6379/3"
        result = parse_redis_url(url)

        assert result["host"] == "redis.example.com"
        assert result["password"] is None
        assert result["db"] == 3


class TestGetRedisConfig:
    """Test get_redis_config function"""

    def test_mock_mode_from_env(self):
        """Test mock mode detection from environment"""
        with patch.dict(os.environ, {"EMPATHY_REDIS_MOCK": "true"}, clear=False):
            config = get_redis_config()
            assert config.use_mock is True

    def test_mock_mode_from_attune_env(self):
        """Test mock mode detection from ATTUNE_REDIS_MOCK."""
        with patch.dict(os.environ, {"ATTUNE_REDIS_MOCK": "true"}, clear=False):
            config = get_redis_config()
            assert config.use_mock is True

    def test_attune_redis_mock_takes_precedence(self):
        """Test ATTUNE_REDIS_MOCK wins over EMPATHY_REDIS_MOCK."""
        env = {
            "ATTUNE_REDIS_MOCK": "true",
            "EMPATHY_REDIS_MOCK": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            config = get_redis_config()
            assert config.use_mock is True

    def test_redis_url_from_env(self):
        """Test configuration from REDIS_URL"""
        with patch.dict(
            os.environ,
            {
                "REDIS_URL": "redis://user:pass@remote.redis.com:6380/2",
                "EMPATHY_REDIS_MOCK": "",
            },
            clear=False,
        ):
            config = get_redis_config()
            assert config.host == "remote.redis.com"
            assert config.port == 6380
            assert config.password == "pass"
            assert config.db == 2
            assert config.use_mock is False

    def test_redis_private_url_from_env(self):
        """Test configuration from REDIS_PRIVATE_URL"""
        with patch.dict(
            os.environ,
            {
                "REDIS_PRIVATE_URL": "redis://internal:secret@internal-redis:6379/0",
                "REDIS_URL": "",
                "EMPATHY_REDIS_MOCK": "",
            },
            clear=False,
        ):
            config = get_redis_config()
            assert config.host == "internal-redis"
            assert config.password == "secret"

    def test_individual_env_vars(self):
        """Test configuration from individual env vars"""
        with patch.dict(
            os.environ,
            {
                "REDIS_HOST": "custom.redis.com",
                "REDIS_PORT": "6380",
                "REDIS_PASSWORD": "mysecret",
                "REDIS_DB": "5",
                "REDIS_SSL": "true",
                "REDIS_URL": "",
                "REDIS_PRIVATE_URL": "",
                "EMPATHY_REDIS_MOCK": "",
            },
            clear=False,
        ):
            config = get_redis_config()
            assert config.host == "custom.redis.com"
            assert config.port == 6380
            assert config.password == "mysecret"
            assert config.db == 5
            assert config.ssl is True

    def test_default_values(self):
        """Test default configuration values"""
        with patch.dict(
            os.environ,
            {
                "REDIS_URL": "",
                "REDIS_PRIVATE_URL": "",
                "REDIS_HOST": "",
                "REDIS_PORT": "",
                "EMPATHY_REDIS_MOCK": "",
            },
            clear=False,
        ):
            # Clear specific vars
            env_backup = {}
            for key in [
                "REDIS_URL",
                "REDIS_PRIVATE_URL",
                "REDIS_HOST",
                "REDIS_PORT",
                "EMPATHY_REDIS_MOCK",
            ]:
                env_backup[key] = os.environ.pop(key, None)

            try:
                config = get_redis_config()
                assert config.host == "127.0.0.1"
                assert config.port == 6379
                assert config.db == 0
            finally:
                # Restore
                for key, val in env_backup.items():
                    if val is not None:
                        os.environ[key] = val


class TestGetRedisConfigDict:
    """Test legacy dict-based config"""

    def test_returns_dict(self):
        """Test that it returns a dict"""
        with patch.dict(os.environ, {"EMPATHY_REDIS_MOCK": "true"}, clear=False):
            result = get_redis_config_dict()
            assert isinstance(result, dict)
            assert "host" in result
            assert "port" in result
            assert "use_mock" in result
            assert result["use_mock"] is True


class TestGetRedisMemory:
    """Test get_redis_memory factory function"""

    def test_with_explicit_config(self):
        """Test creating memory with explicit config"""
        config = RedisConfig(host="test.redis.com", use_mock=True)
        memory = get_redis_memory(config=config)

        assert memory.ping() is True

    def test_with_explicit_mock(self):
        """Test creating memory with explicit mock mode"""
        memory = get_redis_memory(use_mock=True)
        assert memory.ping() is True

    @pytest.mark.skipif(not _REDIS_RUNNING, reason="Redis not running on localhost")
    def test_with_url(self):
        """Test creating memory with URL"""
        # Use mock to avoid actual connection
        with patch.dict(os.environ, {"EMPATHY_REDIS_MOCK": "true"}, clear=False):
            memory = get_redis_memory(url="redis://localhost:6379/0")
            # The URL is parsed but mock env takes precedence
            assert memory is not None

    def test_from_environment(self):
        """Test creating memory from environment"""
        with patch.dict(os.environ, {"EMPATHY_REDIS_MOCK": "true"}, clear=False):
            memory = get_redis_memory()
            assert memory.ping() is True


class TestCheckRedisConnection:
    """Test connection checking"""

    def test_mock_mode_connected(self):
        """Test connection check in mock mode"""
        with patch.dict(os.environ, {"EMPATHY_REDIS_MOCK": "true"}, clear=False):
            result = check_redis_connection()

            assert result["connected"] is True
            assert result["config_source"] == "mock_mode"


class TestGetRailwayRedis:
    """Test Railway-specific helper"""

    def test_raises_without_url(self):
        """Test that it raises when REDIS_URL is missing"""
        with patch.dict(
            os.environ,
            {"REDIS_URL": "", "REDIS_PRIVATE_URL": ""},
            clear=False,
        ):
            # Remove the env vars
            os.environ.pop("REDIS_URL", None)
            os.environ.pop("REDIS_PRIVATE_URL", None)

            with pytest.raises(OSError) as exc_info:
                get_railway_redis()

            assert "REDIS_URL not found" in str(exc_info.value)

    def test_with_redis_url(self):
        """Test Railway with REDIS_URL set - just verify URL is parsed"""
        from attune.redis_config import parse_redis_url

        # Test that the URL would be parsed correctly
        url = "redis://railway-redis:6379/0"
        result = parse_redis_url(url)

        assert result["host"] == "railway-redis"
        assert result["port"] == 6379
        assert result["db"] == 0


class TestRedisMode:
    """Tests for REDIS_MODE support (cloud/local)."""

    # --- _resolve_redis_mode() ---

    def test_explicit_cloud_mode(self):
        """Test explicit REDIS_MODE=cloud returns cloud."""
        with patch.dict(os.environ, {"REDIS_MODE": "cloud"}, clear=False):
            assert _resolve_redis_mode() == "cloud"

    def test_explicit_local_mode(self):
        """Test explicit REDIS_MODE=local returns local."""
        with patch.dict(os.environ, {"REDIS_MODE": "local"}, clear=False):
            assert _resolve_redis_mode() == "local"

    def test_invalid_mode_raises(self):
        """Test that invalid REDIS_MODE raises ValueError."""
        with patch.dict(os.environ, {"REDIS_MODE": "invalid"}, clear=False):
            with pytest.raises(ValueError, match="Invalid REDIS_MODE"):
                _resolve_redis_mode()

    def test_infer_cloud_from_nonlocal_host(self):
        """Test mode inferred as cloud from non-localhost REDIS_HOST."""
        env = {"REDIS_MODE": "", "REDIS_HOST": "redis-cloud.example.com"}
        with patch.dict(os.environ, env, clear=False):
            assert _resolve_redis_mode() == "cloud"

    def test_infer_local_from_localhost(self):
        """Test mode inferred as local when REDIS_HOST is localhost."""
        env = {"REDIS_MODE": "", "REDIS_HOST": "localhost"}
        with patch.dict(os.environ, env, clear=False):
            assert _resolve_redis_mode() == "local"

    def test_infer_local_when_no_host(self):
        """Test mode inferred as local when REDIS_HOST not set."""
        env = {"REDIS_MODE": "", "REDIS_HOST": ""}
        with patch.dict(os.environ, env, clear=False):
            assert _resolve_redis_mode() == "local"

    # --- get_redis_config() with REDIS_MODE ---

    def test_cloud_mode_uses_env_credentials(self):
        """Test cloud mode reads host/password from env."""
        env = {
            "REDIS_MODE": "cloud",
            "REDIS_HOST": "my-cloud.redislabs.com",
            "REDIS_PORT": "15667",
            "REDIS_PASSWORD": "secretpass",
            "REDIS_DB": "2",
            "REDIS_URL": "",
            "REDIS_PRIVATE_URL": "",
            "EMPATHY_REDIS_MOCK": "",
        }
        with patch.dict(os.environ, env, clear=False):
            config = get_redis_config()
            assert config.host == "my-cloud.redislabs.com"
            assert config.port == 15667
            assert config.password == "secretpass"
            assert config.db == 2
            assert config.use_mock is False

    def test_local_mode_ignores_password(self):
        """Test local mode uses literal loopback and ignores REDIS_PASSWORD."""
        env = {
            "REDIS_MODE": "local",
            "REDIS_HOST": "should-be-ignored.com",
            "REDIS_PASSWORD": "should-be-ignored",
            "REDIS_URL": "",
            "REDIS_PRIVATE_URL": "",
            "EMPATHY_REDIS_MOCK": "",
        }
        with patch.dict(os.environ, env, clear=False):
            config = get_redis_config()
            assert config.host == "127.0.0.1"
            assert config.password is None
            assert config.use_mock is False

    def test_url_takes_precedence_over_mode(self):
        """Test REDIS_URL overrides REDIS_MODE."""
        env = {
            "REDIS_URL": "redis://url-host:6380/3",
            "REDIS_MODE": "local",
            "REDIS_HOST": "mode-host.com",
            "EMPATHY_REDIS_MOCK": "",
        }
        with patch.dict(os.environ, env, clear=False):
            config = get_redis_config()
            assert config.host == "url-host"
            assert config.port == 6380
            assert config.db == 3

    def test_mock_takes_precedence_over_mode(self):
        """Test EMPATHY_REDIS_MOCK=true overrides REDIS_MODE."""
        env = {
            "EMPATHY_REDIS_MOCK": "true",
            "REDIS_MODE": "cloud",
            "REDIS_HOST": "cloud-host.com",
            "REDIS_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=False):
            config = get_redis_config()
            assert config.use_mock is True


class TestCloudModeMissingCredentials:
    """Cover the cloud-mode warning branches (missing host / password)."""

    def test_cloud_mode_missing_host_warns(self, monkeypatch, caplog):
        """REDIS_MODE=cloud with no REDIS_HOST logs a warning and falls
        back to the loopback host."""
        import logging

        monkeypatch.setenv("REDIS_MODE", "cloud")
        monkeypatch.delenv("REDIS_HOST", raising=False)
        monkeypatch.setenv("REDIS_PASSWORD", "some-pass")
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)
        monkeypatch.delenv("EMPATHY_REDIS_MOCK", raising=False)
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)

        with caplog.at_level(logging.WARNING, logger="attune.redis_config"):
            config = get_redis_config()

        assert config.host == "127.0.0.1"
        assert any("REDIS_HOST not set" in r.message for r in caplog.records)

    def test_cloud_mode_missing_password_warns(self, monkeypatch, caplog):
        """REDIS_MODE=cloud with a host but no REDIS_PASSWORD logs a
        warning and proceeds with password=None."""
        import logging

        monkeypatch.setenv("REDIS_MODE", "cloud")
        monkeypatch.setenv("REDIS_HOST", "my-cloud-host.example.com")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)
        monkeypatch.delenv("EMPATHY_REDIS_MOCK", raising=False)
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)

        with caplog.at_level(logging.WARNING, logger="attune.redis_config"):
            config = get_redis_config()

        assert config.host == "my-cloud-host.example.com"
        assert config.password is None
        assert any("REDIS_PASSWORD not set" in r.message for r in caplog.records)


class TestGetRedisMemoryWithUrl:
    """Cover get_redis_memory(url=...) building an explicit RedisConfig
    and handing it to RedisShortTermMemory (never touching a real
    connection — RedisShortTermMemory itself is stubbed out)."""

    def test_url_builds_config_and_constructs_memory(self, monkeypatch):
        from unittest.mock import MagicMock

        sentinel_memory = MagicMock(name="sentinel_memory")
        ctor = MagicMock(return_value=sentinel_memory)
        monkeypatch.setattr("attune.redis_config.RedisShortTermMemory", ctor)

        from attune.redis_config import get_redis_memory

        result = get_redis_memory(url="rediss://user:secret@explicit-host:6390/4")

        assert result is sentinel_memory
        ctor.assert_called_once()
        passed_config = ctor.call_args.kwargs["config"]
        assert passed_config.host == "explicit-host"
        assert passed_config.port == 6390
        assert passed_config.password == "secret"
        assert passed_config.db == 4
        assert passed_config.ssl is True
        assert passed_config.use_mock is False


class TestCheckRedisConnectionSourceAndReachability:
    """Cover the config_source branches (REDIS_URL / REDIS_PRIVATE_URL /
    REDIS_MODE) and the non-mock connected/exception paths of
    check_redis_connection — always with get_redis_memory stubbed so no
    real Redis connection is attempted."""

    def _fake_memory(self, *, ping_result=True, ping_error=None, stats=None):
        from unittest.mock import MagicMock

        memory = MagicMock(name="fake_memory")
        if ping_error is not None:
            memory.ping.side_effect = ping_error
        else:
            memory.ping.return_value = ping_result
        memory.get_stats.return_value = stats or {
            "used_memory": "1.2M",
            "total_keys": 7,
        }
        return memory

    def test_redis_url_source_and_successful_ping(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://source-host:6379/0")
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)
        monkeypatch.delenv("REDIS_MODE", raising=False)
        monkeypatch.delenv("EMPATHY_REDIS_MOCK", raising=False)
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)

        fake_memory = self._fake_memory(ping_result=True)
        monkeypatch.setattr(
            "attune.redis_config.get_redis_memory",
            lambda: fake_memory,
        )

        from attune.redis_config import check_redis_connection

        result = check_redis_connection()

        assert result["config_source"] == "REDIS_URL"
        assert result["connected"] is True
        assert result["memory_used"] == "1.2M"
        assert result["total_keys"] == 7
        assert result["error"] is None

    def test_redis_private_url_source(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("REDIS_PRIVATE_URL", "redis://internal-host:6379/0")
        monkeypatch.delenv("REDIS_MODE", raising=False)
        monkeypatch.delenv("EMPATHY_REDIS_MOCK", raising=False)
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)

        fake_memory = self._fake_memory(ping_result=True)
        monkeypatch.setattr(
            "attune.redis_config.get_redis_memory",
            lambda: fake_memory,
        )

        from attune.redis_config import check_redis_connection

        result = check_redis_connection()

        assert result["config_source"] == "REDIS_PRIVATE_URL"
        assert result["connected"] is True

    def test_redis_mode_source_and_ping_exception(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)
        monkeypatch.setenv("REDIS_MODE", "local")
        monkeypatch.delenv("EMPATHY_REDIS_MOCK", raising=False)
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)

        fake_memory = self._fake_memory(ping_error=ConnectionError("refused"))
        monkeypatch.setattr(
            "attune.redis_config.get_redis_memory",
            lambda: fake_memory,
        )

        from attune.redis_config import check_redis_connection

        result = check_redis_connection()

        assert result["config_source"] == "REDIS_MODE=local"
        assert result["connected"] is False
        assert "refused" in result["error"]

    def test_resolve_mode_reporting_failure_yields_unknown(self, monkeypatch):
        """REDIS_URL bypasses mode resolution inside get_redis_config(),
        but check_redis_connection() separately resolves the mode purely
        for reporting — an invalid REDIS_MODE there is caught and
        reported as 'unknown' rather than propagating."""
        monkeypatch.setenv("REDIS_URL", "redis://source-host:6379/0")
        monkeypatch.setenv("REDIS_MODE", "not-a-real-mode")
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)
        monkeypatch.delenv("EMPATHY_REDIS_MOCK", raising=False)
        monkeypatch.delenv("ATTUNE_REDIS_MOCK", raising=False)

        fake_memory = self._fake_memory(ping_result=True)
        monkeypatch.setattr(
            "attune.redis_config.get_redis_memory",
            lambda: fake_memory,
        )

        from attune.redis_config import check_redis_connection

        result = check_redis_connection()

        assert result["redis_mode"] == "unknown"
        assert result["connected"] is True


class TestGetManagedRedisSuccess:
    """Cover the get_managed_redis() success path (REDIS_URL present)."""

    def test_returns_memory_from_url(self, monkeypatch):
        from unittest.mock import MagicMock

        monkeypatch.setenv("REDIS_URL", "redis://managed-host:6379/0")
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)

        sentinel_memory = MagicMock(name="sentinel_memory")
        get_memory_mock = MagicMock(return_value=sentinel_memory)
        monkeypatch.setattr("attune.redis_config.get_redis_memory", get_memory_mock)

        from attune.redis_config import get_managed_redis

        result = get_managed_redis()

        assert result is sentinel_memory
        get_memory_mock.assert_called_once_with(url="redis://managed-host:6379/0")
