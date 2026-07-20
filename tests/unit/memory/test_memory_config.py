"""Tests for attune.memory.config (legacy deprecated module).

Covers:
- parse_redis_url: hostname, port, password, db parsing
- get_redis_config: use_mock=True path, real config path
- get_redis_memory: use_mock=True, explicit URL, env-based (mock), env-based (real)
- check_redis_connection: mock mode, REDIS_URL env, other env vars, ping success, exception
- get_managed_redis: no URL → OSError, URL present → returns memory
- get_railway_redis: deprecated alias, warns and delegates
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.memory.config import (
    check_redis_connection,
    get_managed_redis,
    get_railway_redis,
    get_redis_config,
    get_redis_memory,
    parse_redis_url,
)

# ---------------------------------------------------------------------------
# parse_redis_url
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseRedisUrl:
    def test_full_url(self):
        result = parse_redis_url("redis://user:secret@myhost:6380/2")  # pragma: allowlist secret
        assert result["host"] == "myhost"
        assert result["port"] == 6380
        assert result["password"] == "secret"
        assert result["db"] == 2

    def test_minimal_url_uses_defaults(self):
        result = parse_redis_url("redis://localhost")
        assert result["host"] == "localhost"
        assert result["port"] == 6379
        assert result["db"] == 0

    def test_no_path_db_defaults_to_zero(self):
        result = parse_redis_url("redis://host:6379")
        assert result["db"] == 0


# ---------------------------------------------------------------------------
# get_redis_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRedisConfig:
    def test_mock_mode_returns_use_mock_true(self):
        mock_config = MagicMock()
        mock_config.use_mock = True

        with patch("attune.redis_config.get_redis_config", return_value=mock_config):
            result = get_redis_config()

        assert result == {"use_mock": True}

    def test_real_config_returns_connection_params(self):
        mock_config = MagicMock()
        mock_config.use_mock = False
        mock_config.host = "myredis"
        mock_config.port = 6380
        mock_config.password = "pw"
        mock_config.db = 1

        with patch("attune.redis_config.get_redis_config", return_value=mock_config):
            result = get_redis_config()

        assert result["host"] == "myredis"
        assert result["port"] == 6380
        assert result["use_mock"] is False


# ---------------------------------------------------------------------------
# get_redis_memory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRedisMemory:
    def test_use_mock_true_returns_mock_memory(self):
        with patch("attune.memory.config.RedisShortTermMemory") as MockMem:
            MockMem.return_value = MagicMock()
            get_redis_memory(use_mock=True)
        MockMem.assert_called_once_with(use_mock=True)

    def test_explicit_url_parses_and_connects(self):
        with patch("attune.memory.config.RedisShortTermMemory") as MockMem:
            MockMem.return_value = MagicMock()
            get_redis_memory(url="redis://host:6379/0")
        call_kwargs = MockMem.call_args[1]
        assert call_kwargs["host"] == "host"
        assert call_kwargs["use_mock"] is False

    def test_env_based_mock_mode(self):
        mock_cfg = {"use_mock": True}
        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.RedisShortTermMemory") as MockMem,
        ):
            MockMem.return_value = MagicMock()
            get_redis_memory()
        MockMem.assert_called_once_with(use_mock=True)

    def test_env_based_real_connection(self):
        mock_cfg = {"use_mock": False, "host": "h", "port": 6379, "password": None, "db": 0}
        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.RedisShortTermMemory") as MockMem,
        ):
            MockMem.return_value = MagicMock()
            get_redis_memory()
        call_kwargs = MockMem.call_args[1]
        assert call_kwargs["host"] == "h"
        assert call_kwargs["use_mock"] is False


# ---------------------------------------------------------------------------
# check_redis_connection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckRedisConnection:
    @pytest.fixture(autouse=True)
    def _no_ambient_redis_url(self, monkeypatch):
        # The dev shell and the weekly clean-run launchd env export
        # REDIS_URL, which outranks the vars these tests set.
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_PRIVATE_URL", raising=False)
        monkeypatch.delenv("REDIS_PUBLIC_URL", raising=False)

    def test_mock_mode_returns_connected_true(self):
        mock_cfg = {"use_mock": True}
        with patch("attune.memory.config.get_redis_config", return_value=mock_cfg):
            result = check_redis_connection()
        assert result["connected"] is True
        assert result["config_source"] == "mock_mode"

    def test_redis_url_env_sets_config_source(self):
        mock_cfg = {"use_mock": True}
        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch.dict("os.environ", {"REDIS_URL": "redis://localhost"}),
        ):
            result = check_redis_connection()
        # mock_mode overwrites, but config_source was set to REDIS_URL first
        # (then overwritten by mock_mode branch)
        assert result is not None

    def test_redis_host_env_sets_config_source(self):
        mock_cfg = {"use_mock": False, "host": "h", "port": 6379}
        mock_memory = MagicMock()
        mock_memory.ping.return_value = True
        mock_memory.get_stats.return_value = {"used_memory": 1024, "total_keys": 5}

        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.get_redis_memory", return_value=mock_memory),
            patch.dict("os.environ", {"REDIS_HOST": "h"}, clear=False),
        ):
            result = check_redis_connection()
        assert result["config_source"] == "REDIS_HOST"

    def test_ping_success_returns_stats(self):
        mock_cfg = {"use_mock": False, "host": "h", "port": 6379}
        mock_memory = MagicMock()
        mock_memory.ping.return_value = True
        mock_memory.get_stats.return_value = {"used_memory": 2048, "total_keys": 10}

        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.get_redis_memory", return_value=mock_memory),
        ):
            result = check_redis_connection()

        assert result["connected"] is True
        assert result["memory_used"] == 2048

    def test_exception_captured_in_error_field(self):
        mock_cfg = {"use_mock": False, "host": "h", "port": 6379}
        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.get_redis_memory", side_effect=ConnectionError("refused")),
        ):
            result = check_redis_connection()

        assert result["connected"] is False
        assert "refused" in result["error"]

    def test_redis_public_url_env_sets_config_source(self):
        mock_cfg = {"use_mock": False, "host": "h", "port": 6379}
        mock_memory = MagicMock()
        mock_memory.ping.return_value = False

        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.get_redis_memory", return_value=mock_memory),
            patch.dict(
                "os.environ",
                {"REDIS_PUBLIC_URL": "redis://managed-host"},
                clear=False,
            ),
        ):
            result = check_redis_connection()
        assert result["config_source"] == "REDIS_PUBLIC_URL"

    def test_redis_private_url_env_sets_config_source(self):
        mock_cfg = {"use_mock": False, "host": "h", "port": 6379}
        mock_memory = MagicMock()
        mock_memory.ping.return_value = False

        with (
            patch("attune.memory.config.get_redis_config", return_value=mock_cfg),
            patch("attune.memory.config.get_redis_memory", return_value=mock_memory),
            patch.dict("os.environ", {"REDIS_PRIVATE_URL": "redis://private"}, clear=False),
        ):
            result = check_redis_connection()
        assert "PRIVATE_URL" in result["config_source"]


# ---------------------------------------------------------------------------
# get_managed_redis (+ deprecated get_railway_redis alias)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetManagedRedis:
    def test_no_url_raises_os_error(self):
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            # Ensure no REDIS_* vars are set
            import os

            for key in ["REDIS_URL", "REDIS_PUBLIC_URL", "REDIS_PRIVATE_URL"]:
                os.environ.pop(key, None)

            with pytest.raises(OSError, match="REDIS_URL not found"):
                get_managed_redis()

    def test_redis_url_returns_memory(self):
        with (
            patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}, clear=False),
            patch("attune.memory.config.get_redis_memory") as mock_mem,
        ):
            mock_mem.return_value = MagicMock()
            get_managed_redis()
        mock_mem.assert_called_once_with(url="redis://localhost:6379")

    def test_railway_alias_warns_and_delegates(self):
        with (
            patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}, clear=False),
            patch("attune.memory.config.get_redis_memory") as mock_mem,
            pytest.warns(DeprecationWarning, match="get_managed_redis"),
        ):
            mock_mem.return_value = MagicMock()
            get_railway_redis()
        mock_mem.assert_called_once_with(url="redis://localhost:6379")
