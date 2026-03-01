"""Tests for Redis bootstrap utilities.

Covers:
- RedisStatus and RedisStartMethod
- Platform detection
- Start method functions
- ensure_redis function
- stop_redis function

Copyright 2025 Smart AI Memory, LLC
"""

import subprocess
from unittest.mock import MagicMock, patch

from attune.memory.redis_bootstrap import (
    RedisStartMethod,
    RedisStatus,
    _check_redis_running,
    _find_command,
    _run_silent,
    _start_via_direct,
    _start_via_docker,
    _start_via_homebrew,
    _start_via_systemd,
    ensure_redis,
    get_redis_or_mock,
    stop_redis,
)

# =============================================================================
# REDIS STATUS AND START METHOD
# =============================================================================


class TestRedisStatus:
    """Test RedisStatus dataclass."""

    def test_default_values(self):
        """Test default values."""
        status = RedisStatus(
            available=True,
            method=RedisStartMethod.ALREADY_RUNNING,
        )

        assert status.available is True
        assert status.method == RedisStartMethod.ALREADY_RUNNING
        assert status.host == "localhost"
        assert status.port == 6379
        assert status.message == ""
        assert status.pid is None

    def test_custom_values(self):
        """Test custom values."""
        status = RedisStatus(
            available=False,
            method=RedisStartMethod.MOCK,
            host="redis.example.com",
            port=6380,
            message="Failed to connect",
            pid=12345,
        )

        assert status.available is False
        assert status.host == "redis.example.com"
        assert status.port == 6380
        assert status.message == "Failed to connect"
        assert status.pid == 12345


class TestRedisStartMethod:
    """Test RedisStartMethod enum."""

    def test_all_methods_have_values(self):
        """Test all start methods have string values."""
        assert RedisStartMethod.ALREADY_RUNNING.value == "already_running"
        assert RedisStartMethod.HOMEBREW.value == "homebrew"
        assert RedisStartMethod.SYSTEMD.value == "systemd"
        assert RedisStartMethod.WINDOWS_SERVICE.value == "windows_service"
        assert RedisStartMethod.DOCKER.value == "docker"
        assert RedisStartMethod.DIRECT.value == "direct"
        assert RedisStartMethod.MOCK.value == "mock"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


class TestCheckRedisRunning:
    """Test _check_redis_running function."""

    def test_returns_false_when_redis_not_available(self):
        """Test returns False when Redis is not available on default port."""
        # Test against a port that's almost certainly not running Redis
        result = _check_redis_running(host="localhost", port=16379)
        assert result is False

    def test_uses_custom_host_and_port(self):
        """Test uses custom host and port without error."""
        # Just verify it doesn't crash with custom params
        result = _check_redis_running(host="nonexistent-host", port=6380)
        assert result is False


class TestFindCommand:
    """Test _find_command function."""

    @patch("shutil.which")
    def test_finds_existing_command(self, mock_which):
        """Test finding an existing command."""
        mock_which.return_value = "/usr/bin/redis-server"

        result = _find_command("redis-server")

        assert result == "/usr/bin/redis-server"

    @patch("shutil.which")
    def test_returns_none_for_missing_command(self, mock_which):
        """Test returns None for missing command."""
        mock_which.return_value = None

        result = _find_command("nonexistent-command")

        assert result is None


class TestRunSilent:
    """Test _run_silent function."""

    @patch("subprocess.run")
    def test_returns_success_and_output(self, mock_run):
        """Test returns success and output for successful command."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        success, output = _run_silent(["echo", "test"])

        assert success is True
        assert "output" in output

    @patch("subprocess.run")
    def test_returns_failure_for_failed_command(self, mock_run):
        """Test returns failure for failed command."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        success, output = _run_silent(["false"])

        assert success is False

    @patch("subprocess.run")
    def test_handles_timeout(self, mock_run):
        """Test handles command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

        success, output = _run_silent(["sleep", "100"], timeout=1)

        assert success is False
        assert "timeout" in output

    @patch("subprocess.run")
    def test_handles_exception(self, mock_run):
        """Test handles other exceptions."""
        mock_run.side_effect = Exception("Some error")

        success, output = _run_silent(["test"])

        assert success is False
        assert "error" in output.lower()


# =============================================================================
# START METHODS
# =============================================================================


class TestStartViaHomebrew:
    """Test Homebrew start method."""

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_if_brew_not_found(self, mock_find, mock_run):
        """Test returns False if brew command not found."""
        mock_find.return_value = None

        result = _start_via_homebrew()

        assert result is False

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_if_redis_not_installed(self, mock_find, mock_run):
        """Test returns False if Redis not installed via Homebrew."""
        mock_find.return_value = "/usr/local/bin/brew"
        mock_run.return_value = (False, "redis not installed")

        result = _start_via_homebrew()

        assert result is False

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_true_on_successful_start(self, mock_find, mock_run, mock_sleep):
        """Test returns True when Redis starts successfully."""
        mock_find.return_value = "/usr/local/bin/brew"
        mock_run.side_effect = [
            (True, "redis"),  # brew list redis
            (True, ""),  # brew services start redis
        ]

        result = _start_via_homebrew()

        assert result is True


class TestStartViaSystemd:
    """Test systemd start method."""

    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_if_systemctl_not_found(self, mock_find):
        """Test returns False if systemctl not found."""
        mock_find.return_value = None

        result = _start_via_systemd()

        assert result is False

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_true_on_successful_start(self, mock_find, mock_run, mock_sleep):
        """Test returns True when Redis starts successfully."""
        mock_find.return_value = "/usr/bin/systemctl"
        mock_run.return_value = (True, "")

        result = _start_via_systemd()

        assert result is True

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_tries_redis_server_service(self, mock_find, mock_run, mock_sleep):
        """Test tries redis-server service name as fallback."""
        mock_find.return_value = "/usr/bin/systemctl"
        mock_run.side_effect = [
            (False, ""),  # systemctl start redis
            (True, ""),  # systemctl start redis-server
        ]

        result = _start_via_systemd()

        assert result is True


class TestStartViaDocker:
    """Test Docker start method."""

    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_if_docker_not_found(self, mock_find):
        """Test returns False if docker not found."""
        mock_find.return_value = None

        result = _start_via_docker()

        assert result is False

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_if_daemon_not_running(self, mock_find, mock_run):
        """Test returns False if Docker daemon not running."""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.return_value = (False, "daemon not running")

        result = _start_via_docker()

        assert result is False

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_starts_existing_container(self, mock_find, mock_run, mock_sleep):
        """Test starts existing container if present."""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.side_effect = [
            (True, ""),  # docker info
            (True, "empathy-redis"),  # docker ps -a (container exists)
            (True, ""),  # docker start
        ]

        result = _start_via_docker()

        assert result is True

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_creates_new_container(self, mock_find, mock_run, mock_sleep):
        """Test creates new container if not present."""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.side_effect = [
            (True, ""),  # docker info
            (True, ""),  # docker ps -a (no container)
            (True, ""),  # docker run
        ]

        result = _start_via_docker()

        assert result is True


class TestStartViaDirect:
    """Test direct redis-server start method."""

    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_if_redis_server_not_found(self, mock_find):
        """Test returns False if redis-server not found."""
        mock_find.return_value = None

        result = _start_via_direct()

        assert result is False

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_uses_daemonize_on_unix(self, mock_find, mock_popen, mock_sleep):
        """Test uses daemonize flag on Unix."""
        mock_find.return_value = "/usr/bin/redis-server"
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = _start_via_direct()

        assert result is True
        # Check daemonize flag was used
        call_args = mock_popen.call_args[0][0]
        assert "--daemonize" in call_args


# =============================================================================
# ENSURE REDIS
# =============================================================================


class TestEnsureRedis:
    """Test ensure_redis function."""

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    def test_returns_already_running_if_available(self, mock_check):
        """Test returns ALREADY_RUNNING if Redis is available."""
        mock_check.return_value = True

        status = ensure_redis(verbose=False)

        assert status.available is True
        assert status.method == RedisStartMethod.ALREADY_RUNNING

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    def test_returns_mock_if_auto_start_false(self, mock_check):
        """Test returns MOCK if auto_start is False and Redis not running."""
        mock_check.return_value = False

        status = ensure_redis(auto_start=False, verbose=False)

        assert status.available is False
        assert status.method == RedisStartMethod.MOCK

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_homebrew")
    @patch("attune.memory.redis_bootstrap.IS_MACOS", True)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", False)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_tries_homebrew_on_macos(self, mock_homebrew, mock_check):
        """Test tries Homebrew on macOS."""
        mock_check.side_effect = [False, True]  # Not running, then running
        mock_homebrew.return_value = True

        status = ensure_redis(verbose=False)

        assert status.available is True
        assert status.method == RedisStartMethod.HOMEBREW
        mock_homebrew.assert_called_once()

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_systemd")
    @patch("attune.memory.redis_bootstrap.IS_MACOS", False)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", True)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_tries_systemd_on_linux(self, mock_systemd, mock_check):
        """Test tries systemd on Linux."""
        mock_check.side_effect = [False, True]
        mock_systemd.return_value = True

        status = ensure_redis(verbose=False)

        assert status.available is True
        assert status.method == RedisStartMethod.SYSTEMD

    def test_ensure_redis_returns_status(self):
        """Test ensure_redis returns a valid RedisStatus."""
        # This test just verifies the function returns valid status
        status = ensure_redis(auto_start=False, verbose=False)

        assert isinstance(status, RedisStatus)
        assert hasattr(status, "available")
        assert hasattr(status, "method")

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_direct")
    @patch("attune.memory.redis_bootstrap._start_via_docker")
    @patch("attune.memory.redis_bootstrap._start_via_homebrew")
    @patch("attune.memory.redis_bootstrap.IS_MACOS", True)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", False)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_returns_mock_when_all_methods_fail(
        self,
        mock_homebrew,
        mock_docker,
        mock_direct,
        mock_check,
    ):
        """Test returns MOCK when all start methods fail."""
        mock_check.return_value = False
        mock_homebrew.return_value = False
        mock_docker.return_value = False
        mock_direct.return_value = False

        status = ensure_redis(verbose=False)

        assert status.available is False
        assert status.method == RedisStartMethod.MOCK


# =============================================================================
# STOP REDIS
# =============================================================================


class TestStopRedis:
    """Test stop_redis function."""

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stops_homebrew(self, mock_run):
        """Test stops Redis started via Homebrew."""
        mock_run.return_value = (True, "")

        result = stop_redis(RedisStartMethod.HOMEBREW)

        assert result is True
        mock_run.assert_called_with(["brew", "services", "stop", "redis"])

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stops_systemd(self, mock_run):
        """Test stops Redis started via systemd."""
        mock_run.return_value = (True, "")

        result = stop_redis(RedisStartMethod.SYSTEMD)

        assert result is True

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stops_docker(self, mock_run):
        """Test stops Redis started via Docker."""
        mock_run.return_value = (True, "")

        result = stop_redis(RedisStartMethod.DOCKER)

        assert result is True
        mock_run.assert_called_with(["docker", "stop", "empathy-redis"])

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_stops_direct(self, mock_find, mock_run):
        """Test stops Redis started directly."""
        mock_find.return_value = "/usr/bin/redis-cli"
        mock_run.return_value = (True, "")

        result = stop_redis(RedisStartMethod.DIRECT)

        assert result is True

    def test_returns_false_for_already_running(self):
        """Test returns False for ALREADY_RUNNING (we didn't start it)."""
        result = stop_redis(RedisStartMethod.ALREADY_RUNNING)

        assert result is False

    def test_returns_false_for_mock(self):
        """Test returns False for MOCK (nothing to stop)."""
        result = stop_redis(RedisStartMethod.MOCK)

        assert result is False


# =============================================================================
# GET REDIS OR MOCK
# =============================================================================


class TestGetRedisOrMock:
    """Test get_redis_or_mock convenience function."""

    @patch("attune.memory.short_term.RedisShortTermMemory")
    @patch("attune.memory.redis_bootstrap.ensure_redis")
    def test_returns_status_when_available(self, mock_ensure, mock_memory_cls):
        """Test returns status indicating Redis availability."""
        mock_ensure.return_value = RedisStatus(
            available=True,
            method=RedisStartMethod.ALREADY_RUNNING,
        )
        mock_memory = mock_memory_cls.return_value

        memory, status = get_redis_or_mock()

        assert status.available is True
        assert memory is mock_memory
        mock_memory_cls.assert_called_once_with(host="localhost", port=6379, use_mock=False)

    @patch("attune.memory.redis_bootstrap.ensure_redis")
    def test_returns_mock_status_when_unavailable(self, mock_ensure):
        """Test returns mock status when Redis unavailable."""
        mock_ensure.return_value = RedisStatus(
            available=False,
            method=RedisStartMethod.MOCK,
        )

        memory, status = get_redis_or_mock()

        assert status.available is False
        assert memory is not None
