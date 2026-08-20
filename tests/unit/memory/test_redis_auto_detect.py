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

import importlib.util
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

    # ---- Package-install verification (#1418 fake-success regression) ----

    def test_package_install_pip_success_but_import_fails(self, detector, capsys):
        """pip exiting 0 must NOT produce a success claim when the import
        still fails — the #1418 fake-success bug (a no-op install printed
        '✓ redis package installed' and sent the user to debug the server)."""
        with (
            patch("builtins.input", return_value="y"),
            patch("attune.memory.redis_auto_detect.subprocess.check_call", return_value=0),
            patch.object(detector, "_check_python_package", return_value=False),
        ):
            result = detector._prompt_python_package()

        out = capsys.readouterr().out
        assert result is False
        assert "✓ redis package installed" not in out
        assert "still not importable" in out
        # The remediation must not be the command that just ran (circular).
        assert "pip check" in out or "attune-ai" in out

    def test_package_install_success_verified_by_import(self, detector, capsys):
        """The success claim appears only after the import re-check passes,
        and the server flow continues."""
        with (
            patch("builtins.input", return_value="y"),
            patch("attune.memory.redis_auto_detect.subprocess.check_call", return_value=0),
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=True),
        ):
            result = detector._prompt_python_package()

        assert result is True
        assert "✓ redis package installed" in capsys.readouterr().out

    def test_package_install_subprocess_targets_pinned_redis(self, detector):
        """The pip invocation must target the real `redis` package with
        pyproject's version pin — never the deleted [redis] extra (whose
        no-op success created the fake-success bug), and never unpinned
        (which could pull a major that violates the core constraint)."""
        with (
            patch("builtins.input", return_value="y"),
            patch("attune.memory.redis_auto_detect.subprocess.check_call", return_value=0) as cc,
            patch.object(detector, "_check_python_package", return_value=True),
            patch.object(detector, "_check_server_reachable", return_value=True),
        ):
            detector._prompt_python_package()

        args = cc.call_args[0][0]
        assert "redis>=5.0.0,<9.0.0" in args
        assert not any("attune-ai[" in a for a in args)

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
        from attune.memory.short_term.base import BaseOperations

        # Patch _create_client_with_retry to avoid the real Redis
        # connection attempt. With REDIS_ENABLED=true and no server
        # running, the unpatched constructor blocks for ~17s
        # (3 retries × 5s socket timeout) and on Windows under xdist
        # that crashed workers. The test only cares that
        # auto_detect_redis was NOT called — the actual client is
        # incidental.
        with (
            patch.dict("os.environ", {"REDIS_ENABLED": "true"}),
            patch.object(BaseOperations, "_create_client_with_retry", return_value=None),
            patch("attune.memory.redis_auto_detect.auto_detect_redis") as mock_detect,
        ):
            BaseOperations()
            mock_detect.assert_not_called()

    def test_respects_redis_enabled_false(self):
        """Test that REDIS_ENABLED=false forces mock mode."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "false"}):
            from attune.memory.short_term.base import BaseOperations

            ops = BaseOperations()
            assert ops._config.use_mock is True


# =============================================================================
# ADDITIONAL COVERAGE: uncovered paths
# =============================================================================


class TestLoadConfigErrorPaths:
    """Test _load_config error handling."""

    def test_load_config_yaml_error_returns_empty_dict(self, tmp_path):
        """Test that YAML parse error in config returns empty dict."""
        config_path = tmp_path / "bad.yml"
        config_path.write_text(": : invalid: yaml: content: !!!")
        detector = RedisAutoDetector(config_path=config_path)
        assert detector.config == {}

    def test_load_config_oserror_returns_empty_dict(self, tmp_path):
        """Test that OSError reading config returns empty dict."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        config_path.write_text("redis:\n  key: value\n", encoding="utf-8")
        with up("builtins.open", side_effect=OSError("permission denied")):
            detector = RedisAutoDetector(config_path=config_path)
        assert detector.config == {}

    def test_load_config_nonexistent_file_returns_empty_dict(self, tmp_path):
        """Test that missing config file returns empty dict."""
        config_path = tmp_path / "nonexistent.yml"
        detector = RedisAutoDetector(config_path=config_path)
        assert detector.config == {}


class TestSaveConfigErrorPath:
    """Test _save_config error handling."""

    def test_save_config_oserror_logs_error(self, tmp_path, caplog):
        """Test that OSError during config save logs an error."""
        import logging
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)
        detector.config = {"redis": {"test": True}}

        with up("builtins.open", side_effect=OSError("disk full")):
            with caplog.at_level(logging.ERROR):
                detector._save_config()
        # Should log an error instead of raising
        assert any("Failed to save config" in r.message for r in caplog.records)


class TestCheckPythonPackageImportError:
    """Test _check_python_package when redis not importable."""

    def test_check_python_package_returns_false_when_not_installed(self, tmp_path):
        """Test that ImportError leads to _check_python_package returning False."""
        import builtins
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("No module named redis")
            return original_import(name, *args, **kwargs)

        with up("builtins.__import__", side_effect=fake_import):
            result = detector._check_python_package()

        assert result is False


@pytest.mark.skipif(
    not importlib.util.find_spec("redis"),
    reason="redis not installed",
)
class TestCheckServerReachable:
    """Test _check_server_reachable paths.

    Real endpoints only. These previously patched ``redis.Redis``, which
    made them pass no matter which host and port the probe dialled —
    the mock defined the contract, and that is how library-review H1
    (probe hard-coded to 127.0.0.1:6379 while clients connect to the
    resolved endpoint) survived 23 references to this method. The
    reachable-endpoint direction is covered against a real listening
    socket in ``test_probe_endpoint_agreement.py``.
    """

    def test_returns_false_when_configured_endpoint_is_not_listening(self, tmp_path, monkeypatch):
        """Nothing listening on the resolved endpoint means unreachable."""
        import socket

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        closed_port = sock.getsockname()[1]
        sock.close()

        # The other six connection vars are cleared for every test by
        # conftest's _scrub_redis_connection_env, so setting REDIS_URL is
        # enough to pin the endpoint; REDIS_HOST is suite-pinned to
        # loopback and loses to a URL var on precedence either way.
        monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{closed_port}/0")

        detector = RedisAutoDetector(config_path=tmp_path / "config.yml")

        assert detector._check_server_reachable() is False

    def test_returns_false_on_a_malformed_configured_url(self, tmp_path, monkeypatch):
        """A bad REDIS_URL degrades to "unreachable", it does not raise.

        Hermetic via the same conftest fixture as the test above — checked
        by running this file with hostile REDIS_PRIVATE_URL / REDIS_HOST /
        REDIS_PASSWORD exported (codex D11 lane, 2026-08-20).
        """
        monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:not-a-port/0")

        detector = RedisAutoDetector(config_path=tmp_path / "config.yml")

        assert detector._check_server_reachable() is False


class TestPromptInstall:
    """Test prompt_install flow."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache before each test."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    def test_prompt_install_already_available_returns_true(self, tmp_path):
        """Test prompt_install returns True when Redis is already available."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up.object(detector, "_check_python_package", return_value=True),
            up.object(detector, "_check_server_reachable", return_value=True),
        ):
            result = detector.prompt_install()

        assert result is True

    def test_prompt_install_no_package_calls_python_prompt(self, tmp_path):
        """Test prompt_install calls _prompt_python_package when no package."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up.object(detector, "_check_python_package", return_value=False),
            up.object(detector, "_prompt_python_package", return_value=False) as mock_pp,
        ):
            result = detector.prompt_install()

        mock_pp.assert_called_once()
        assert result is False

    def test_prompt_install_no_server_calls_server_prompt(self, tmp_path):
        """Test prompt_install calls _prompt_server_install when server not reachable."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up.object(detector, "_check_python_package", return_value=True),
            up.object(detector, "_check_server_reachable", return_value=False),
            up.object(detector, "_prompt_server_install", return_value=False) as mock_sp,
        ):
            result = detector.prompt_install()

        mock_sp.assert_called_once()
        assert result is False


class TestPromptPythonPackage:
    """Test _prompt_python_package interactive flow."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache before each test."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    def test_prompt_python_package_decline_returns_false(self, tmp_path):
        """Test declining the python package prompt saves preference."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with up("builtins.input", return_value="d"):
            result = detector._prompt_python_package()

        assert result is False
        assert detector.config.get("redis", {}).get("install_declined") is True

    def test_prompt_python_package_skip_returns_false(self, tmp_path):
        """Test skipping the python package prompt returns False."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with up("builtins.input", return_value="s"):
            result = detector._prompt_python_package()

        assert result is False

    def test_prompt_python_package_eof_returns_false(self, tmp_path):
        """Test EOF during python package prompt returns False."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with up("builtins.input", side_effect=EOFError):
            result = detector._prompt_python_package()

        assert result is False

    def test_prompt_python_package_install_success(self, tmp_path):
        """Test that a successful pip install triggers server check."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("builtins.input", return_value="y"),
            up("subprocess.check_call", return_value=0),
            up.object(detector, "_check_server_reachable", return_value=True),
        ):
            result = detector._prompt_python_package()

        assert result is True

    def test_prompt_python_package_install_failure(self, tmp_path):
        """Test that a failed pip install returns False."""
        import subprocess
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("builtins.input", return_value="y"),
            up(
                "subprocess.check_call",
                side_effect=subprocess.CalledProcessError(1, "pip"),
            ),
        ):
            result = detector._prompt_python_package()

        assert result is False

    def test_prompt_python_package_install_then_prompt_server(self, tmp_path):
        """Test that successful pip install but no server triggers server prompt."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("builtins.input", return_value="y"),
            up("subprocess.check_call", return_value=0),
            up.object(detector, "_check_server_reachable", return_value=False),
            up.object(detector, "_prompt_server_install", return_value=True),
        ):
            result = detector._prompt_python_package()

        assert result is True


class TestGetInstallCommandLinuxYum:
    """Test _get_install_command for Linux with yum."""

    def test_platform_install_command_linux_yum(self, tmp_path):
        """Test Linux yum install command when apt not available."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        def fake_which(cmd):
            return None if cmd == "apt" else "/usr/bin/yum"

        with (
            up("attune.memory.redis_auto_detect.IS_MACOS", False),
            up("attune.memory.redis_auto_detect.IS_LINUX", True),
            up("shutil.which", side_effect=fake_which),
        ):
            cmd = detector._get_install_command()

        assert "yum" in cmd

    def test_platform_install_command_linux_no_pkg_manager(self, tmp_path):
        """Test Linux fallback when neither apt nor yum is available."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("attune.memory.redis_auto_detect.IS_MACOS", False),
            up("attune.memory.redis_auto_detect.IS_LINUX", True),
            up("shutil.which", return_value=None),
        ):
            cmd = detector._get_install_command()

        assert "apt" in cmd


class TestRunServerInstall:
    """Test _run_server_install paths."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache before each test."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    def test_run_server_install_success(self, tmp_path):
        """Test successful server install invalidates cache and returns True."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("subprocess.check_call", return_value=0),
            up("time.sleep"),
            up.object(detector, "_check_server_reachable", return_value=True),
        ):
            result = detector._run_server_install("brew install redis")

        assert result is True
        assert detector.config.get("redis", {}).get("installed") is True

    def test_run_server_install_failure_called_process_error(self, tmp_path):
        """Test that CalledProcessError returns False."""
        import subprocess
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with up(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(1, "brew"),
        ):
            result = detector._run_server_install("brew install redis")

        assert result is False

    def test_run_server_install_timeout_returns_false(self, tmp_path):
        """Test that TimeoutExpired returns False."""
        import subprocess
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with up(
            "subprocess.check_call",
            side_effect=subprocess.TimeoutExpired("brew", 120),
        ):
            result = detector._run_server_install("brew install redis")

        assert result is False

    def test_run_server_install_installed_but_not_responding(self, tmp_path):
        """Test that install succeeds but server not responding returns False."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("subprocess.check_call", return_value=0),
            up("time.sleep"),
            up.object(detector, "_check_server_reachable", return_value=False),
        ):
            result = detector._run_server_install("brew install redis")

        assert result is False

    def test_run_server_install_compound_command(self, tmp_path):
        """Test that compound commands split on && are executed sequentially."""
        from unittest.mock import patch as up

        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)

        with (
            up("subprocess.check_call", return_value=0) as mock_call,
            up("time.sleep"),
            up.object(detector, "_check_server_reachable", return_value=True),
        ):
            detector._run_server_install("brew install redis && brew services start redis")

        # Should have been called twice (one per && part)
        assert mock_call.call_count == 2


class TestSavePreference:
    """Test _save_preference initializes redis dict."""

    def test_save_preference_creates_redis_dict_if_missing(self, tmp_path):
        """Test that _save_preference creates 'redis' key if absent."""
        config_path = tmp_path / "config.yml"
        detector = RedisAutoDetector(config_path=config_path)
        assert "redis" not in detector.config

        detector._save_preference("my_key", "my_value")

        assert detector.config["redis"]["my_key"] == "my_value"


class TestAutoDetectRedisTriggerPrompt:
    """Test auto_detect_redis when prompt triggers and install succeeds."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset module-level cache before each test."""
        import attune.memory.redis_auto_detect as mod

        mod._cached_result = None
        mod._cached_at = 0.0
        yield
        mod._cached_result = None
        mod._cached_at = 0.0

    def test_auto_detect_returns_updated_result_after_install(self):
        """Test auto_detect_redis re-detects after successful install."""
        from unittest.mock import patch as up

        available_result = RedisDetectionResult(
            available=True,
            has_python_package=True,
            server_reachable=True,
            reason="Redis server is running",
        )
        unavailable_result = RedisDetectionResult(
            available=False,
            has_python_package=True,
            server_reachable=False,
            reason="Redis server not reachable",
        )

        call_count = {"n": 0}

        def detect_side_effect(self_):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return unavailable_result
            return available_result

        with (
            up.object(RedisAutoDetector, "detect", detect_side_effect),
            up.object(RedisAutoDetector, "should_prompt", return_value=True),
            up.object(RedisAutoDetector, "prompt_install", return_value=True),
        ):
            result = auto_detect_redis()

        assert result.available is True
