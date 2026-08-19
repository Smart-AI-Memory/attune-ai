# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for platform utilities, agent loader, Redis config — Batch 13.

Covers: platform_utils, agents_md/loader, redis_config.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# === Module: platform_utils.py ===


class TestPlatformUtils:
    def test_is_windows_returns_bool(self):
        from attune.platform_utils import is_windows

        assert isinstance(is_windows(), bool)

    def test_is_macos_returns_bool(self):
        from attune.platform_utils import is_macos

        assert isinstance(is_macos(), bool)

    def test_is_linux_returns_bool(self):
        from attune.platform_utils import is_linux

        assert isinstance(is_linux(), bool)

    def test_exactly_one_platform_true(self):
        from attune.platform_utils import is_linux, is_macos, is_windows

        # Exactly one should be true on any real system
        # (allow all False for exotic systems)
        count = sum([is_windows(), is_macos(), is_linux()])
        assert count <= 1

    def test_is_windows_patches(self):
        from attune.platform_utils import is_windows

        with patch("platform.system", return_value="Windows"):
            assert is_windows() is True

    def test_is_macos_patches(self):
        from attune.platform_utils import is_macos

        with patch("platform.system", return_value="Darwin"):
            assert is_macos() is True

    def test_is_linux_patches(self):
        from attune.platform_utils import is_linux

        with patch("platform.system", return_value="Linux"):
            assert is_linux() is True

    def test_get_default_log_dir_returns_path(self):
        from attune.platform_utils import get_default_log_dir

        result = get_default_log_dir()
        assert isinstance(result, Path)

    def test_get_default_data_dir_returns_path(self):
        from attune.platform_utils import get_default_data_dir

        result = get_default_data_dir()
        assert isinstance(result, Path)

    def test_get_default_config_dir_returns_path(self):
        from attune.platform_utils import get_default_config_dir

        result = get_default_config_dir()
        assert isinstance(result, Path)

    def test_get_default_cache_dir_returns_path(self):
        from attune.platform_utils import get_default_cache_dir

        result = get_default_cache_dir()
        assert isinstance(result, Path)

    def test_get_default_log_dir_macos(self):
        from attune.platform_utils import get_default_log_dir

        with patch("platform.system", return_value="Darwin"):
            result = get_default_log_dir()
        assert "Logs" in str(result)

    def test_get_default_data_dir_linux(self):
        from attune.platform_utils import get_default_data_dir

        with patch("platform.system", return_value="Linux"):
            with patch.dict(os.environ, {"XDG_DATA_HOME": "/custom/data"}, clear=False):
                result = get_default_data_dir()
        assert "empathy" in str(result)

    def test_setup_asyncio_policy_noop_on_non_windows(self):
        from attune.platform_utils import setup_asyncio_policy

        with patch("platform.system", return_value="Darwin"):
            setup_asyncio_policy()  # Should not raise

    def test_safe_run_async_runs_coroutine(self):

        from attune.platform_utils import safe_run_async

        async def echo(x):
            return x

        result = safe_run_async(echo(42))
        assert result == 42

    def test_open_text_file_defaults_utf8(self, tmp_path):
        from attune.platform_utils import open_text_file

        test_file = tmp_path / "test.txt"
        test_file.write_text("hello", encoding="utf-8")
        with open_text_file(str(test_file)) as f:
            assert f.read() == "hello"

    def test_read_text_file(self, tmp_path):
        from attune.platform_utils import read_text_file

        test_file = tmp_path / "test.txt"
        test_file.write_text("world", encoding="utf-8")
        assert read_text_file(str(test_file)) == "world"

    def test_write_text_file(self, tmp_path):
        from attune.platform_utils import write_text_file

        target = tmp_path / "out.txt"
        count = write_text_file(str(target), "hello world")
        assert count == len("hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_normalize_path_returns_absolute(self, tmp_path):
        from attune.platform_utils import normalize_path

        result = normalize_path(str(tmp_path / "foo"))
        assert result.is_absolute()

    def test_get_temp_dir_returns_path(self):
        from attune.platform_utils import get_temp_dir

        result = get_temp_dir()
        assert isinstance(result, Path)
        assert result.exists()

    def test_ensure_dir_creates_directory(self, tmp_path):
        from attune.platform_utils import ensure_dir

        new_dir = tmp_path / "nested" / "dir"
        result = ensure_dir(str(new_dir))
        assert result.exists()
        assert result.is_dir()

    def test_get_platform_info_returns_dict(self):
        from attune.platform_utils import get_platform_info

        info = get_platform_info()
        assert isinstance(info, dict)
        assert "system" in info
        assert "python_version" in info

    def test_platform_info_constant_exists(self):
        from attune.platform_utils import PLATFORM_INFO

        assert isinstance(PLATFORM_INFO, dict)
        assert "is_windows" in PLATFORM_INFO
        assert "is_macos" in PLATFORM_INFO


# === Module: agents_md/loader.py ===


class TestAgentLoader:
    def test_loader_init_default_parser(self):
        from attune.agents_md.loader import AgentLoader

        loader = AgentLoader()
        assert loader.parser is not None

    def test_loader_init_custom_parser(self):
        from attune.agents_md.loader import AgentLoader

        mock_parser = MagicMock()
        loader = AgentLoader(parser=mock_parser)
        assert loader.parser is mock_parser

    def test_load_delegates_to_parser(self):
        from attune.agents_md.loader import AgentLoader

        mock_parser = MagicMock()
        mock_config = MagicMock()
        mock_parser.parse_file.return_value = mock_config

        loader = AgentLoader(parser=mock_parser)
        result = loader.load("/some/agent.md")
        mock_parser.parse_file.assert_called_once_with("/some/agent.md")
        assert result is mock_config

    def test_discover_nonexistent_dir_yields_nothing(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        loader = AgentLoader()
        result = list(loader.discover(tmp_path / "nonexistent"))
        assert result == []

    def test_discover_not_a_dir_raises(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        f = tmp_path / "file.txt"
        f.write_text("x")
        loader = AgentLoader()
        with pytest.raises(ValueError, match="Not a directory"):
            list(loader.discover(f))

    def test_discover_skips_underscore_files(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        (tmp_path / "_private.md").write_text("# Agent\nname: private")
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = MagicMock(name="priv")
        loader = AgentLoader(parser=mock_parser)
        list(loader.discover(tmp_path))
        mock_parser.parse_file.assert_not_called()

    def test_discover_skips_readme(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        (tmp_path / "README.md").write_text("# Not an agent")
        mock_parser = MagicMock()
        loader = AgentLoader(parser=mock_parser)
        list(loader.discover(tmp_path))
        mock_parser.parse_file.assert_not_called()

    def test_discover_yields_valid_agents(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        (tmp_path / "agent.md").write_text("# Agent")
        mock_config = MagicMock()
        mock_config.name = "agent"
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = mock_config
        loader = AgentLoader(parser=mock_parser)
        results = list(loader.discover(tmp_path))
        assert len(results) == 1
        assert results[0].name == "agent"

    def test_discover_skips_invalid_on_value_error(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        (tmp_path / "bad.md").write_text("invalid")
        mock_parser = MagicMock()
        mock_parser.parse_file.side_effect = ValueError("bad format")
        loader = AgentLoader(parser=mock_parser)
        results = list(loader.discover(tmp_path))
        assert results == []

    def test_load_directory_returns_dict(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        mock_config = MagicMock()
        mock_config.name = "my_agent"
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = mock_config
        (tmp_path / "my_agent.md").write_text("# Agent")

        loader = AgentLoader(parser=mock_parser)
        result = loader.load_directory(tmp_path)
        assert "my_agent" in result

    def test_load_directory_skips_duplicates(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        mock_config = MagicMock()
        mock_config.name = "same"
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = mock_config

        (tmp_path / "agent1.md").write_text("# Agent")
        (tmp_path / "agent2.md").write_text("# Agent")

        loader = AgentLoader(parser=mock_parser)
        result = loader.load_directory(tmp_path)
        assert len(result) == 1

    def test_get_agent_names_returns_list(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        mock_config = MagicMock()
        mock_config.name = "my_agent"
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = mock_config
        (tmp_path / "my_agent.md").write_text("# Agent")

        loader = AgentLoader(parser=mock_parser)
        names = loader.get_agent_names(tmp_path)
        assert names == ["my_agent"]

    def test_validate_directory_empty_on_valid(self, tmp_path):
        from attune.agents_md.loader import AgentLoader

        (tmp_path / "agent.md").write_text("# Agent")
        mock_parser = MagicMock()
        mock_parser.validate_file.return_value = []
        loader = AgentLoader(parser=mock_parser)
        result = loader.validate_directory(tmp_path)
        assert result == {}

    def test_load_agents_from_paths_file(self, tmp_path):
        from attune.agents_md.loader import load_agents_from_paths

        f = tmp_path / "agent.md"
        f.write_text("# Agent")
        mock_config = MagicMock()
        mock_config.name = "agent"
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = mock_config

        result = load_agents_from_paths([f], parser=mock_parser)
        assert "agent" in result

    def test_load_agents_from_paths_missing_warns(self, tmp_path):
        from attune.agents_md.loader import load_agents_from_paths

        # Should not raise for nonexistent path
        result = load_agents_from_paths([tmp_path / "missing.md"])
        assert result == {}


# === Module: redis_config.py ===


class TestRedisConfig:
    def test_resolve_redis_mode_defaults_local(self):
        from attune.redis_config import _resolve_redis_mode

        with patch.dict(os.environ, {}, clear=True):
            assert _resolve_redis_mode() == "local"

    def test_resolve_redis_mode_explicit_cloud(self):
        from attune.redis_config import _resolve_redis_mode

        with patch.dict(os.environ, {"REDIS_MODE": "cloud"}, clear=False):
            assert _resolve_redis_mode() == "cloud"

    def test_resolve_redis_mode_explicit_local(self):
        from attune.redis_config import _resolve_redis_mode

        with patch.dict(os.environ, {"REDIS_MODE": "local"}, clear=False):
            assert _resolve_redis_mode() == "local"

    def test_resolve_redis_mode_invalid_raises(self):
        from attune.redis_config import _resolve_redis_mode

        with patch.dict(os.environ, {"REDIS_MODE": "sentinel"}, clear=False):
            with pytest.raises(ValueError, match="Invalid REDIS_MODE"):
                _resolve_redis_mode()

    def test_resolve_redis_mode_infers_cloud_from_host(self):
        """rct-4: the helper no longer reads REDIS_HOST — callers pass
        the resolver-derived host for inference."""
        from attune.redis_config import _resolve_redis_mode

        env = dict(os.environ)
        env.pop("REDIS_MODE", None)
        with patch.dict(os.environ, env, clear=True):
            assert _resolve_redis_mode("redis.example.com") == "cloud"

    def test_parse_redis_url_standard(self):
        from attune.redis_config import parse_redis_url

        result = parse_redis_url("redis://user:pass@host.example.com:6380/1")
        assert result["host"] == "host.example.com"
        assert result["port"] == 6380
        assert result["password"] == "pass"
        assert result["db"] == 1
        assert result["ssl"] is False

    def test_parse_redis_url_ssl(self):
        from attune.redis_config import parse_redis_url

        result = parse_redis_url("rediss://user:pass@host.example.com:6380/0")
        assert result["ssl"] is True

    def test_parse_redis_url_defaults(self):
        from attune.redis_config import parse_redis_url

        result = parse_redis_url("redis://host.example.com")
        assert result["port"] == 6379
        assert result["db"] == 0
        assert result["ssl"] is False

    def test_get_redis_memory_with_mock(self):
        from attune.redis_config import get_redis_memory

        memory = get_redis_memory(use_mock=True)
        assert memory is not None

    def test_get_railway_redis_raises_without_url(self):
        from attune.redis_config import get_railway_redis

        env = {k: v for k, v in os.environ.items() if k not in ("REDIS_URL", "REDIS_PRIVATE_URL")}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(OSError, match="REDIS_URL not found"):
                get_railway_redis()

    def test_check_redis_connection_mock_mode(self):
        from attune.redis_config import check_redis_connection

        with patch("attune.redis_config.get_redis_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                use_mock=True, host="localhost", port=6379, password=None, db=0
            )
            result = check_redis_connection()
        assert result["use_mock"] is True
        assert result["connected"] is True
