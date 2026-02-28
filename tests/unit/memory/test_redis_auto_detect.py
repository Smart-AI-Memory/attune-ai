"""Tests for Redis auto-detection and install prompting.

Covers:
- RedisDetectionResult dataclass
- RedisAutoDetector detection flow
- Module-level caching with TTL
- Preference persistence (config.yml)
- Platform-specific install commands
- Interactive vs non-interactive behavior
- Backward compatibility with REDIS_ENABLED env var

Copyright 2025 Smart AI Memory, LLC
"""

import time
from unittest.mock import patch

import pytest

from attune.memory.redis_auto_detect import (
    _CACHE_TTL,
    RedisAutoDetector,
    RedisDetectionResult,
    auto_detect_redis,
)

# =============================================================================
# REDIS DETECTION RESULT
# =============================================================================


class TestRedisDetectionResult:
    """Test RedisDetectionResult dataclass."""

    def test_available_result(self):
        """Test result when Redis is available."""
        result = RedisDetectionResult(
            available=True,
            has_python_package=True,
            server_reachable=True,
            reason="Redis server is running",
        )
        assert result.available is True
        assert result.has_python_package is True
        assert result.server_reachable is True

    def test_unavailable_no_package(self):
        """Test result when Python package is missing."""
        result = RedisDetectionResult(
            available=False,
            has_python_package=False,
            server_reachable=False,
            reason="redis Python package not installed",
        )
        assert result.available is False
        assert result.has_python_package is False

    def test_unavailable_no_server(self):
        """Test result when server is not reachable."""
        result = RedisDetectionResult(
            available=False,
            has_python_package=True,
            server_reachable=False,
            reason="Redis server not reachable",
        )
        assert result.available is False
        assert result.has_python_package is True
        assert result.server_reachable is False


# =============================================================================
# REDIS AUTO DETECTOR
# =============================================================================


class TestRedisAutoDetector:
    """Test RedisAutoDetector class."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache before each test."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    @pytest.fixture
    def detector(self, tmp_path):
        """Create detector with temp config path."""
        config_path = tmp_path / "config.yml"
        return RedisAutoDetector(config_path=config_path)

    # ---- Detection Flow ----

    def test_detects_running_redis(self, detector):
        """Test detection when Redis is fully available."""
        with (
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=True),
        ):
            result = detector.detect()

        assert result.available is True
        assert result.has_python_package is True
        assert result.server_reachable is True
        assert "running" in result.reason

    def test_detects_no_redis_package(self, detector):
        """Test detection when redis Python package is missing."""
        with patch.object(detector, "_check_python_package", return_value=False):
            result = detector.detect()

        assert result.available is False
        assert result.has_python_package is False
        assert "package" in result.reason

    def test_detects_no_server(self, detector):
        """Test detection when server is not reachable."""
        with (
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=False),
        ):
            result = detector.detect()

        assert result.available is False
        assert result.has_python_package is True
        assert result.server_reachable is False

    # ---- Caching ----

    def test_caches_detection_result(self, detector):
        """Test that successful detection results are cached."""
        with (
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=True) as mock_ping,
        ):
            result1 = detector.detect()
            result2 = detector.detect()

        assert result1.available is True
        assert result2.available is True
        # Ping should only be called once — second call uses cache
        mock_ping.assert_called_once()

    def test_cache_expires_after_ttl(self, detector):
        """Test that cache expires after TTL."""
        import attune.memory.redis_auto_detect as mod

        with (
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=True) as mock_ping,
        ):
            detector.detect()
            # Manually expire the cache
            mod._cached_at = time.monotonic() - _CACHE_TTL - 1
            detector.detect()

        assert mock_ping.call_count == 2

    def test_unavailable_server_not_cached(self, detector):
        """Test that server-not-reachable results are not cached."""
        import attune.memory.redis_auto_detect as mod

        with (
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=False),
        ):
            detector.detect()

        # Should not be cached (so ensure_redis retries can work)
        assert mod._cached_result is None

    # ---- should_prompt ----

    def test_no_prompt_in_non_tty(self, detector):
        """Test that prompts are suppressed in non-interactive mode."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert detector.should_prompt() is False

    def test_prompt_in_tty(self, detector):
        """Test that prompts are shown in interactive mode."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert detector.should_prompt() is True

    def test_declined_never_prompts_again(self, detector):
        """Test that install_declined suppresses future prompts."""
        detector._save_preference("install_declined", True)

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert detector.should_prompt() is False

    # ---- Preferences ----

    def test_save_and_load_preference(self, tmp_path):
        """Test preference persistence via config.yml."""
        config_path = tmp_path / "config.yml"
        detector1 = RedisAutoDetector(config_path=config_path)
        detector1._save_preference("install_declined", True)

        # Create new instance to read from disk
        detector2 = RedisAutoDetector(config_path=config_path)
        redis_config = detector2.config.get("redis", {})
        assert redis_config.get("install_declined") is True

    def test_config_file_created(self, tmp_path):
        """Test that config directory and file are created."""
        config_path = tmp_path / "subdir" / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)
        detector._save_preference("test_key", "test_value")
        assert config_path.exists()

    # ---- Platform Detection ----

    def test_platform_install_command_macos(self, detector):
        """Test macOS install command."""
        with (
            patch("attune.memory.redis_auto_detect.IS_MACOS", True),
            patch("attune.memory.redis_auto_detect.IS_LINUX", False),
        ):
            cmd = detector._get_install_command()
        assert "brew" in cmd

    def test_platform_install_command_linux(self, detector):
        """Test Linux install command."""
        with (
            patch("attune.memory.redis_auto_detect.IS_MACOS", False),
            patch("attune.memory.redis_auto_detect.IS_LINUX", True),
            patch("shutil.which", return_value="/usr/bin/apt"),
        ):
            cmd = detector._get_install_command()
        assert "apt" in cmd

    def test_platform_install_command_fallback_docker(self, detector):
        """Test Docker fallback for unknown platforms."""
        with (
            patch("attune.memory.redis_auto_detect.IS_MACOS", False),
            patch("attune.memory.redis_auto_detect.IS_LINUX", False),
        ):
            cmd = detector._get_install_command()
        assert "docker" in cmd

    # ---- Prompt UX ----

    def test_prompt_server_install_accept(self, detector):
        """Test accepting server install prompt."""
        with (
            patch.object(detector, "_check_server_reachable", return_value=False),
            patch.object(detector, "_run_server_install", return_value=True),
            patch.object(detector, "_get_install_command", return_value="brew install redis"),
            patch("builtins.input", return_value="y"),
        ):
            result = detector._prompt_server_install()
        assert result is True

    def test_prompt_server_install_skip(self, detector):
        """Test skipping server install prompt."""
        with (
            patch.object(detector, "_get_install_command", return_value="brew install redis"),
            patch("builtins.input", return_value="s"),
        ):
            result = detector._prompt_server_install()
        assert result is False

    def test_prompt_server_install_decline(self, detector):
        """Test permanently declining server install."""
        with (
            patch.object(detector, "_get_install_command", return_value="brew install redis"),
            patch("builtins.input", return_value="d"),
        ):
            result = detector._prompt_server_install()

        assert result is False
        redis_config = detector.config.get("redis", {})
        assert redis_config.get("install_declined") is True

    def test_prompt_handles_eof(self, detector):
        """Test graceful handling of EOF in prompt."""
        with (
            patch.object(detector, "_get_install_command", return_value="brew install redis"),
            patch("builtins.input", side_effect=EOFError),
        ):
            result = detector._prompt_server_install()
        assert result is False

    def test_prompt_handles_keyboard_interrupt(self, detector):
        """Test graceful handling of Ctrl+C in prompt."""
        with (
            patch.object(detector, "_get_install_command", return_value="brew install redis"),
            patch("builtins.input", side_effect=KeyboardInterrupt),
        ):
            result = detector._prompt_server_install()
        assert result is False

    # ---- Cache invalidation ----

    def test_invalidate_cache(self, detector):
        """Test cache invalidation."""
        import attune.memory.redis_auto_detect as mod

        with (
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=True),
        ):
            detector.detect()

        assert mod._cached_result is not None
        detector._invalidate_cache()
        assert mod._cached_result is None


# =============================================================================
# AUTO DETECT CONVENIENCE FUNCTION
# =============================================================================


class TestAutoDetectRedis:
    """Test the auto_detect_redis convenience function."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache before each test."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    def test_returns_available_when_redis_running(self):
        """Test convenience function with running Redis."""
        with (
            patch(
                "attune.memory.redis_auto_detect.RedisAutoDetector._check_python_package",
                return_value=True,
            ),
            patch(
                "attune.memory.redis_auto_detect.RedisAutoDetector._check_server_reachable",
                return_value=True,
            ),
        ):
            result = auto_detect_redis()

        assert result.available is True

    def test_returns_unavailable_in_non_tty(self):
        """Test convenience function in non-interactive mode."""
        with (
            patch(
                "attune.memory.redis_auto_detect.RedisAutoDetector._check_python_package",
                return_value=True,
            ),
            patch(
                "attune.memory.redis_auto_detect.RedisAutoDetector._check_server_reachable",
                return_value=False,
            ),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            result = auto_detect_redis()

        assert result.available is False


# =============================================================================
# BACKWARD COMPATIBILITY (base.py integration)
# =============================================================================


class TestBaseOperationsBackwardCompat:
    """Test that REDIS_ENABLED env var still takes precedence."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    def test_respects_redis_enabled_true(self):
        """Test that REDIS_ENABLED=true bypasses auto-detection."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "true"}):
            from attune.memory.short_term.base import BaseOperations

            # Should not call auto_detect_redis at all
            with patch("attune.memory.redis_auto_detect.auto_detect_redis") as mock_detect:
                try:
                    BaseOperations()
                except Exception:
                    # INTENTIONAL: Connection may fail — we only care that
                    # auto-detect was NOT called
                    pass
                mock_detect.assert_not_called()

    def test_respects_redis_enabled_false(self):
        """Test that REDIS_ENABLED=false forces mock mode."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "false"}):
            from attune.memory.short_term.base import BaseOperations

            ops = BaseOperations()
            assert ops._config.use_mock is True
