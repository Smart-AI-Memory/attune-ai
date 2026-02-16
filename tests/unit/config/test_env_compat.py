"""Tests for environment variable compatibility layer.

Verifies ATTUNE_ takes precedence, EMPATHY_ works as fallback with
deprecation warning, and default values are returned correctly.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from attune.config.env_compat import (
    _warned_vars,
    get_attune_env,
    iter_attune_env_prefix,
)


@pytest.fixture(autouse=True)
def _clear_warned_vars():
    """Reset deprecation tracking between tests."""
    _warned_vars.clear()
    yield
    _warned_vars.clear()


class TestGetAttuneEnv:
    """Tests for get_attune_env()."""

    def test_attune_prefix_preferred(self):
        """ATTUNE_ value wins when both prefixes are set."""
        env = {"ATTUNE_LOG_LEVEL": "DEBUG", "EMPATHY_LOG_LEVEL": "INFO"}
        with patch.dict("os.environ", env, clear=False):
            assert get_attune_env("LOG_LEVEL") == "DEBUG"

    def test_empathy_fallback_works(self):
        """EMPATHY_ value returned when ATTUNE_ is not set."""
        env = {"EMPATHY_LOG_LEVEL": "WARNING"}
        with patch.dict("os.environ", env, clear=False):
            assert get_attune_env("LOG_LEVEL") == "WARNING"

    def test_default_returned_when_neither_set(self):
        """Default value returned when no env var is set."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_attune_env("LOG_LEVEL", "INFO") == "INFO"
            assert get_attune_env("LOG_LEVEL") is None

    def test_deprecation_logged_once(self, caplog):
        """Deprecation warning logged only on first use of EMPATHY_ var."""
        env = {"EMPATHY_LOG_LEVEL": "DEBUG"}
        with patch.dict("os.environ", env, clear=False):
            with caplog.at_level(logging.WARNING, logger="attune.config.env_compat"):
                get_attune_env("LOG_LEVEL")
                get_attune_env("LOG_LEVEL")  # Second call
                get_attune_env("LOG_LEVEL")  # Third call

        deprecation_msgs = [r for r in caplog.records if "deprecated" in r.message]
        assert len(deprecation_msgs) == 1
        assert "EMPATHY_LOG_LEVEL" in deprecation_msgs[0].message
        assert "ATTUNE_LOG_LEVEL" in deprecation_msgs[0].message

    def test_attune_prefix_no_deprecation_warning(self, caplog):
        """No deprecation warning when using ATTUNE_ prefix."""
        env = {"ATTUNE_LOG_LEVEL": "DEBUG"}
        with patch.dict("os.environ", env, clear=False):
            with caplog.at_level(logging.WARNING, logger="attune.config.env_compat"):
                result = get_attune_env("LOG_LEVEL")

        assert result == "DEBUG"
        deprecation_msgs = [r for r in caplog.records if "deprecated" in r.message]
        assert len(deprecation_msgs) == 0


class TestIterAttuneEnvPrefix:
    """Tests for iter_attune_env_prefix()."""

    def test_prefix_iteration(self):
        """Iterates env vars with given prefix."""
        env = {
            "ATTUNE_WORKFLOW_SECURITY_PROVIDER": "anthropic",
            "ATTUNE_WORKFLOW_REVIEW_PROVIDER": "openai",
            "UNRELATED_VAR": "ignored",
        }
        with patch.dict("os.environ", env, clear=True):
            results = dict(iter_attune_env_prefix("WORKFLOW_", "_PROVIDER"))

        assert results == {
            "SECURITY": "anthropic",
            "REVIEW": "openai",
        }

    def test_empathy_prefix_fallback(self):
        """Falls back to EMPATHY_ prefix for iteration."""
        env = {
            "EMPATHY_WORKFLOW_SECURITY_PROVIDER": "anthropic",
        }
        with patch.dict("os.environ", env, clear=True):
            results = dict(iter_attune_env_prefix("WORKFLOW_", "_PROVIDER"))

        assert results == {"SECURITY": "anthropic"}

    def test_attune_overrides_empathy_in_iteration(self):
        """ATTUNE_ wins over EMPATHY_ for same middle part."""
        env = {
            "ATTUNE_WORKFLOW_REVIEW_PROVIDER": "anthropic",
            "EMPATHY_WORKFLOW_REVIEW_PROVIDER": "openai",
        }
        with patch.dict("os.environ", env, clear=True):
            results = dict(iter_attune_env_prefix("WORKFLOW_", "_PROVIDER"))

        assert results == {"REVIEW": "anthropic"}

    def test_no_suffix(self):
        """Works without a suffix parameter."""
        env = {
            "ATTUNE_MODEL_CHEAP": "haiku",
            "ATTUNE_MODEL_CAPABLE": "sonnet",
        }
        with patch.dict("os.environ", env, clear=True):
            results = dict(iter_attune_env_prefix("MODEL_"))

        assert results == {"CHEAP": "haiku", "CAPABLE": "sonnet"}

    def test_empty_results(self):
        """Returns empty iterator when no matching vars exist."""
        with patch.dict("os.environ", {}, clear=True):
            results = list(iter_attune_env_prefix("WORKFLOW_", "_PROVIDER"))

        assert results == []
