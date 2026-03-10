"""Tests for config load observability — corrupt configs must log warnings.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

from attune.models.auth_strategy import AuthStrategy
from attune.models.provider_config import ProviderConfig


class TestAuthStrategyLoadObservability:
    """Verify auth config load logs on failure."""

    def test_corrupt_json_logs_warning_and_returns_default(self, tmp_path, caplog):
        config_path = tmp_path / "auth.json"
        config_path.write_text("{{invalid json content")

        with caplog.at_level(logging.WARNING):
            result = AuthStrategy.load(path=config_path)

        # Should return default
        assert isinstance(result, AuthStrategy)
        # Should have logged a warning
        assert "auth_strategy_load_failed" in caplog.text

    def test_missing_file_returns_default_no_warning(self, tmp_path, caplog):
        config_path = tmp_path / "nonexistent.json"

        with caplog.at_level(logging.WARNING):
            result = AuthStrategy.load(path=config_path)

        assert isinstance(result, AuthStrategy)
        # No warning — file simply doesn't exist (normal first-run)
        assert "auth_strategy_load_failed" not in caplog.text

    def test_valid_file_loads_without_warning(self, tmp_path, caplog):
        config_path = tmp_path / "auth.json"
        default = AuthStrategy()
        config_path.write_text(json.dumps(default.to_dict()))

        with caplog.at_level(logging.WARNING):
            result = AuthStrategy.load(path=config_path)

        assert isinstance(result, AuthStrategy)
        assert "auth_strategy_load_failed" not in caplog.text


class TestProviderConfigLoadObservability:
    """Verify provider config load logs on failure."""

    def test_corrupt_json_logs_warning_and_falls_back(self, tmp_path, caplog):
        config_path = tmp_path / "provider.json"
        config_path.write_text("not valid json at all")

        with caplog.at_level(logging.WARNING):
            result = ProviderConfig.load(path=config_path)

        assert isinstance(result, ProviderConfig)
        assert "provider_config_load_failed" in caplog.text

    def test_missing_file_returns_autodetect_no_warning(self, tmp_path, caplog):
        config_path = tmp_path / "nonexistent.json"

        with caplog.at_level(logging.WARNING):
            result = ProviderConfig.load(path=config_path)

        assert isinstance(result, ProviderConfig)
        assert "provider_config_load_failed" not in caplog.text

    def test_valid_file_loads_without_warning(self, tmp_path, caplog):
        config_path = tmp_path / "provider.json"
        default = ProviderConfig.auto_detect()
        config_path.write_text(json.dumps(default.to_dict()))

        with caplog.at_level(logging.WARNING):
            result = ProviderConfig.load(path=config_path)

        assert isinstance(result, ProviderConfig)
        assert "provider_config_load_failed" not in caplog.text


class TestEnvFileReadObservability:
    """Verify .env read failures are logged."""

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not reliable on Windows")
    def test_unreadable_env_logs_warning(self, tmp_path, caplog, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=test-key-123")
        env_file.chmod(0o000)

        try:
            # Patch the env_paths to include our unreadable file
            with caplog.at_level(logging.WARNING):
                # We need to test _load_env_files directly
                # Patch Path.cwd and Path.home to return tmp_path
                monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))
                monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
                ProviderConfig._load_env_files()

            assert "env_file_read_failed" in caplog.text
            # Verify no secret values leaked into logs
            assert "test-key-123" not in caplog.text
        finally:
            env_file.chmod(0o644)  # Restore for cleanup


class TestNoSecretsInLogs:
    """Verify sensitive values never appear in log output."""

    def test_api_key_not_in_corrupt_config_log(self, tmp_path, caplog):
        """Even if corrupt JSON contains key-like strings, they shouldn't leak."""
        config_path = tmp_path / "auth.json"
        # Write JSON that's valid but has wrong structure
        config_path.write_text('{"api_key": "sk-secret-123", "bad_field": [1,2,}')

        with caplog.at_level(logging.WARNING):
            AuthStrategy.load(path=config_path)

        # The secret value should not appear in log output
        assert "sk-secret-123" not in caplog.text
