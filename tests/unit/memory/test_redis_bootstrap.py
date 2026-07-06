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
        assert status.host == "127.0.0.1"
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
        # Literal loopback IP, NOT "localhost": hostname resolution goes
        # through native getaddrinfo(), which intermittently segfaults
        # xdist workers on windows-latest (exit 139; hit twice on the
        # 10.0.1 release SHA). Same remedy as test_uses_custom_host_and_port
        # below (windows-xdist-flakes inventory).
        result = _check_redis_running(host="127.0.0.1", port=16379)
        assert result is False

    def test_uses_custom_host_and_port(self):
        """Test uses custom host and port without error."""
        # Use a literal IP, NOT a bogus hostname. "nonexistent-host"
        # triggered a real DNS getaddrinfo() that intermittently crashed
        # xdist workers under parallelism (windows-xdist-flakes inventory).
        # A loopback IP + closed port resolves with no DNS and refuses
        # instantly, exercising the same graceful-False path safely.
        result = _check_redis_running(host="127.0.0.1", port=16380)
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
        mock_memory_cls.assert_called_once_with(host="127.0.0.1", port=6379, use_mock=False)

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


# ---------------------------------------------------------------------------
# Coverage gap tests
# ---------------------------------------------------------------------------


class TestStartViaHomebrewFailure:
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_homebrew_start_returns_false_when_fails(self, mock_find, mock_run):
        """Lines 120-121: homebrew start fails → returns False."""
        from attune.memory.redis_bootstrap import _start_via_homebrew

        mock_find.return_value = "/usr/bin/brew"
        # First call: brew list redis succeeds; second call: start fails
        mock_run.side_effect = [(True, ""), (False, "boom")]
        assert _start_via_homebrew() is False


class TestStartViaSystemdBothFail:
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_returns_false_when_both_service_names_fail(self, mock_find, mock_run):
        """Lines 143-144: both systemctl attempts fail → False."""
        from attune.memory.redis_bootstrap import _start_via_systemd

        mock_find.return_value = "/usr/bin/systemctl"
        mock_run.side_effect = [(False, "no svc"), (False, "no svc")]
        assert _start_via_systemd() is False


class TestStartViaDockerFailures:
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_existing_container_start_fails_then_create_succeeds(
        self, mock_find, mock_run, mock_sleep
    ):
        """Lines 168-185: existing start fails → falls through to create."""
        from attune.memory.redis_bootstrap import _start_via_docker

        mock_find.return_value = "/usr/bin/docker"
        # docker info ok, ps shows existing, start existing fails, run new also fails
        mock_run.side_effect = [
            (True, ""),  # docker info
            (True, "empathy-redis\n"),  # docker ps
            (False, ""),  # docker start (fails)
            (False, "create failed"),  # docker run (also fails)
        ]
        assert _start_via_docker() is False

    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_existing_container_start_succeeds(self, mock_find, mock_run, mock_sleep):
        """Lines 167-171: existing container start succeeds."""
        from attune.memory.redis_bootstrap import _start_via_docker

        mock_find.return_value = "/usr/bin/docker"
        mock_run.side_effect = [
            (True, ""),  # docker info
            (True, "empathy-redis\n"),  # ps shows it
            (True, ""),  # docker start succeeds
        ]
        assert _start_via_docker() is True


class TestStartViaDirectWindows:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_windows_direct_start_success(self, mock_find, mock_sleep, mock_popen):
        """Lines 192, 202-214: Windows-specific lookup + Popen path."""
        from attune.memory.redis_bootstrap import _start_via_direct

        mock_find.side_effect = lambda cmd: (
            "C:\\redis-server.exe" if cmd == "redis-server.exe" else None
        )
        proc = MagicMock()
        proc.poll.return_value = None  # still running
        mock_popen.return_value = proc
        assert _start_via_direct() is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_windows_direct_start_process_died(self, mock_find, mock_sleep, mock_popen):
        """Line 212: process.poll() != None → not running → fall through."""
        from attune.memory.redis_bootstrap import _start_via_direct

        mock_find.side_effect = lambda cmd: (
            "C:\\redis-server.exe" if cmd == "redis-server.exe" else None
        )
        proc = MagicMock()
        proc.poll.return_value = 1  # died
        mock_popen.return_value = proc
        assert _start_via_direct() is False

    @patch("attune.memory.redis_bootstrap.subprocess.Popen", side_effect=OSError("nope"))
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_direct_exception_logged(self, mock_find, mock_popen):
        """Lines 228-232: Popen raises → logged + return False."""
        from attune.memory.redis_bootstrap import _start_via_direct

        mock_find.return_value = "/usr/bin/redis-server"
        assert _start_via_direct() is False


class TestStartViaWindowsService:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    def test_returns_false_on_non_windows(self):
        """Line 237-238: not Windows → returns False."""
        from attune.memory.redis_bootstrap import _start_via_windows_service

        assert _start_via_windows_service() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_starts_successfully(self, mock_run, mock_sleep):
        """Lines 242-246: net start Redis succeeds → True."""
        from attune.memory.redis_bootstrap import _start_via_windows_service

        mock_run.return_value = (True, "")
        assert _start_via_windows_service() is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_already_started(self, mock_run, mock_sleep):
        """Lines 243-246: already started message → True."""
        from attune.memory.redis_bootstrap import _start_via_windows_service

        mock_run.return_value = (False, "service has already been started")
        assert _start_via_windows_service() is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._run_silent", side_effect=RuntimeError("boom"))
    def test_exception_returns_false(self, mock_run):
        """Lines 247-251: exception in net start → caught."""
        from attune.memory.redis_bootstrap import _start_via_windows_service

        assert _start_via_windows_service() is False


class TestStartViaChocolatey:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    def test_non_windows_returns_false(self):
        from attune.memory.redis_bootstrap import _start_via_chocolatey

        assert _start_via_chocolatey() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._find_command", return_value=None)
    def test_no_choco(self, mock_find):
        from attune.memory.redis_bootstrap import _start_via_chocolatey

        assert _start_via_chocolatey() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_redis_not_installed(self, mock_find, mock_run):
        """Lines 264-267: redis not in choco list → False."""
        from attune.memory.redis_bootstrap import _start_via_chocolatey

        mock_find.return_value = "C:\\choco.exe"
        mock_run.return_value = (True, "other-package")
        assert _start_via_chocolatey() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._start_via_windows_service", return_value=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_redis_installed_delegates_to_service(self, mock_find, mock_run, mock_svc):
        """Line 270: choco list → delegates to _start_via_windows_service."""
        from attune.memory.redis_bootstrap import _start_via_chocolatey

        mock_find.return_value = "C:\\choco.exe"
        mock_run.return_value = (True, "redis 6.2.0")
        assert _start_via_chocolatey() is True


class TestStartViaScoop:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    def test_non_windows_returns_false(self):
        from attune.memory.redis_bootstrap import _start_via_scoop

        assert _start_via_scoop() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._find_command", return_value=None)
    def test_no_scoop(self, mock_find):
        from attune.memory.redis_bootstrap import _start_via_scoop

        assert _start_via_scoop() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_redis_not_in_scoop_list(self, mock_find, mock_run):
        """Lines 284-286: redis not in scoop list → False."""
        from attune.memory.redis_bootstrap import _start_via_scoop

        mock_find.return_value = "C:\\scoop"
        mock_run.return_value = (True, "other")
        assert _start_via_scoop() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap.os.path.exists", return_value=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_scoop_installs_and_starts(
        self, mock_find, mock_run, mock_exists, mock_sleep, mock_popen
    ):
        """Lines 290-303: scoop redis exists → Popen success."""
        from attune.memory.redis_bootstrap import _start_via_scoop

        mock_find.return_value = "C:\\scoop"
        mock_run.return_value = (True, "redis 6")
        proc = MagicMock()
        proc.poll.return_value = None
        mock_popen.return_value = proc
        assert _start_via_scoop() is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch(
        "attune.memory.redis_bootstrap.subprocess.Popen",
        side_effect=RuntimeError("oops"),
    )
    @patch("attune.memory.redis_bootstrap.os.path.exists", return_value=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_scoop_popen_exception(self, mock_find, mock_run, mock_exists, mock_popen):
        """Lines 304-306: Popen raises → logged + return False."""
        from attune.memory.redis_bootstrap import _start_via_scoop

        mock_find.return_value = "C:\\scoop"
        mock_run.return_value = (True, "redis 6")
        assert _start_via_scoop() is False


class TestStartViaWsl:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    def test_non_windows_returns_false(self):
        from attune.memory.redis_bootstrap import _start_via_wsl

        assert _start_via_wsl() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._find_command", return_value=None)
    def test_no_wsl(self, mock_find):
        from attune.memory.redis_bootstrap import _start_via_wsl

        assert _start_via_wsl() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_redis_not_in_wsl(self, mock_find, mock_run):
        """Lines 322-325: which redis-server fails → False."""
        from attune.memory.redis_bootstrap import _start_via_wsl

        mock_find.return_value = "C:\\wsl.exe"
        mock_run.return_value = (False, "")
        assert _start_via_wsl() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_wsl_starts_successfully(self, mock_find, mock_run, mock_sleep, mock_popen):
        """Lines 328-338: wsl Popen + wait → success."""
        from attune.memory.redis_bootstrap import _start_via_wsl

        mock_find.return_value = "C:\\wsl.exe"
        mock_run.return_value = (True, "")
        proc = MagicMock()
        proc.returncode = 0
        proc.wait = MagicMock()
        mock_popen.return_value = proc
        assert _start_via_wsl() is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch(
        "attune.memory.redis_bootstrap.subprocess.Popen",
        side_effect=RuntimeError("wsl crashed"),
    )
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_wsl_exception(self, mock_find, mock_run, mock_popen):
        """Lines 339-343: Popen raises → caught."""
        from attune.memory.redis_bootstrap import _start_via_wsl

        mock_find.return_value = "C:\\wsl.exe"
        mock_run.return_value = (True, "")
        assert _start_via_wsl() is False


class TestEnsureRedisVerbose:
    @patch("attune.memory.redis_bootstrap._check_redis_running", return_value=True)
    def test_already_running_verbose_logs(self, mock_check):
        """Line 381: verbose=True & already running → logger.info hit."""
        from attune.memory.redis_bootstrap import ensure_redis

        status = ensure_redis(verbose=True)
        assert status.available is True

    @patch("attune.memory.redis_bootstrap._try_interactive_install", return_value=None)
    @patch("attune.memory.redis_bootstrap._try_start_methods", return_value=None)
    @patch("attune.memory.redis_bootstrap._check_redis_running", return_value=False)
    def test_all_fail_with_verbose_prints(self, mock_check, mock_try, mock_install, capsys):
        """Line 394 + 408: verbose prints when nothing works."""
        from attune.memory.redis_bootstrap import ensure_redis

        status = ensure_redis(verbose=True)
        assert status.available is False
        out = capsys.readouterr().out
        assert "Redis not running" in out
        assert "⚠" in out

    @patch("attune.memory.redis_bootstrap._try_interactive_install")
    @patch("attune.memory.redis_bootstrap._try_start_methods", return_value=None)
    @patch("attune.memory.redis_bootstrap._check_redis_running", return_value=False)
    def test_interactive_install_returns_status(self, mock_check, mock_try, mock_install):
        """Line 404: interactive install returns a started status."""
        from attune.memory.redis_bootstrap import (
            RedisStartMethod,
            RedisStatus,
            ensure_redis,
        )

        mock_install.return_value = RedisStatus(available=True, method=RedisStartMethod.DIRECT)
        status = ensure_redis(verbose=False)
        assert status.available is True


class TestTryStartMethodsBranches:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", new=False)
    @patch("attune.memory.redis_bootstrap.IS_MACOS", new=False)
    @patch("attune.memory.redis_bootstrap._check_redis_running", return_value=True)
    @patch("attune.memory.redis_bootstrap._start_via_windows_service", return_value=True)
    def test_windows_methods_attempted(self, mock_svc, mock_check):
        """Lines 431-432, 452: Windows path of _try_start_methods + verbose print."""
        from attune.memory.redis_bootstrap import _try_start_methods

        result = _try_start_methods("localhost", 6379, verbose=True)
        assert result is not None and result.available is True

    @patch("attune.memory.redis_bootstrap._start_via_homebrew", side_effect=RuntimeError("boom"))
    @patch("attune.memory.redis_bootstrap.IS_MACOS", new=True)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", new=False)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    @patch("attune.memory.redis_bootstrap._start_via_docker", return_value=False)
    @patch("attune.memory.redis_bootstrap._start_via_direct", return_value=False)
    def test_method_exception_caught(self, mock_direct, mock_docker, mock_brew):
        """Lines 460-462: start_func raises → debug log, continue to next."""
        from attune.memory.redis_bootstrap import _try_start_methods

        result = _try_start_methods("localhost", 6379, verbose=False)
        assert result is None


class TestInteractiveInstall:
    @patch("attune.memory.redis_bootstrap.sys.stdin")
    def test_no_tty_returns_none(self, mock_stdin):
        """Line 469-470: no TTY → returns None."""
        from attune.memory.redis_bootstrap import _try_interactive_install

        mock_stdin.isatty.return_value = False
        assert _try_interactive_install("localhost", 6379) is None

    @patch("attune.memory.redis_bootstrap.sys.stdin")
    def test_install_path_succeeds(self, mock_stdin, monkeypatch):
        """Lines 471-487: detector path success."""
        import sys
        from types import SimpleNamespace

        from attune.memory.redis_bootstrap import _try_interactive_install

        mock_stdin.isatty.return_value = True

        fake_detector = MagicMock()
        fake_detector.should_prompt.return_value = True
        fake_detector.prompt_install.return_value = True
        fake_module = SimpleNamespace(RedisAutoDetector=lambda: fake_detector)
        monkeypatch.setitem(sys.modules, "attune.memory.redis_auto_detect", fake_module)

        with patch("attune.memory.redis_bootstrap._check_redis_running", return_value=True):
            result = _try_interactive_install("localhost", 6379)
        assert result is not None and result.available is True

    @patch("attune.memory.redis_bootstrap.sys.stdin")
    def test_install_exception_returns_none(self, mock_stdin, monkeypatch):
        """Lines 484-486: detector raises → caught."""
        import sys

        from attune.memory.redis_bootstrap import _try_interactive_install

        mock_stdin.isatty.return_value = True

        class _Broken:
            def __getattr__(self, name):
                raise RuntimeError("import failed")

        monkeypatch.setitem(sys.modules, "attune.memory.redis_auto_detect", _Broken())
        assert _try_interactive_install("localhost", 6379) is None


class TestGetInstallInstructionsBranches:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.IS_MACOS", new=False)
    def test_windows_instructions(self):
        """Line 516: IS_WINDOWS branch."""
        from attune.memory.redis_bootstrap import _get_install_instructions

        text = _get_install_instructions()
        assert "Chocolatey" in text

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    @patch("attune.memory.redis_bootstrap.IS_MACOS", new=False)
    def test_linux_instructions(self):
        """Line 520: linux fallback branch."""
        from attune.memory.redis_bootstrap import _get_install_instructions

        text = _get_install_instructions()
        assert "Ubuntu/Debian" in text


class TestStopViaSystemdSecondAttempt:
    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_falls_back_to_redis_server(self, mock_run):
        """Line 531: first stop fails → tries 'redis-server'."""
        from attune.memory.redis_bootstrap import _stop_via_systemd

        mock_run.side_effect = [(False, ""), (True, "")]
        assert _stop_via_systemd() is True


class TestStopViaDirectWindows:
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._run_silent", return_value=(True, ""))
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_windows_redis_cli_lookup(self, mock_find, mock_run):
        """Line 538: Windows path tries redis-cli.exe."""
        from attune.memory.redis_bootstrap import _stop_via_direct

        mock_find.side_effect = lambda c: ("C:\\redis-cli.exe" if c == "redis-cli.exe" else None)
        assert _stop_via_direct() is True

    @patch("attune.memory.redis_bootstrap._find_command", return_value=None)
    def test_no_redis_cli_returns_false(self, mock_find):
        """Line 545: redis_cli is None → returns False."""
        from attune.memory.redis_bootstrap import _stop_via_direct

        assert _stop_via_direct() is False


class TestRemainingBranches:
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_unix_direct_nonzero_returncode(self, mock_find, mock_popen):
        """Line 224->232: Unix daemonize Popen returncode != 0 → False."""
        from attune.memory.redis_bootstrap import _start_via_direct

        mock_find.return_value = "/usr/bin/redis-server"
        proc = MagicMock()
        proc.returncode = 1
        mock_popen.return_value = proc
        assert _start_via_direct() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_windows_service_neither_succeeds_nor_already(self, mock_run):
        """Line 243->251: net start fails AND no 'already been started' → False."""
        from attune.memory.redis_bootstrap import _start_via_windows_service

        mock_run.return_value = (False, "service unknown")
        assert _start_via_windows_service() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.os.path.exists", return_value=False)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_scoop_path_does_not_exist(self, mock_find, mock_run, mock_exists):
        """Line 290->308: scoop redis path missing → falls through to return False."""
        from attune.memory.redis_bootstrap import _start_via_scoop

        mock_find.return_value = "C:\\scoop"
        mock_run.return_value = (True, "redis 6")
        assert _start_via_scoop() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    @patch("attune.memory.redis_bootstrap.os.path.exists", return_value=True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_scoop_popen_dies(self, mock_find, mock_run, mock_exists, mock_sleep, mock_popen):
        """Line 301->308: poll returns non-None (process died) → fall through."""
        from attune.memory.redis_bootstrap import _start_via_scoop

        mock_find.return_value = "C:\\scoop"
        mock_run.return_value = (True, "redis 6")
        proc = MagicMock()
        proc.poll.return_value = 1  # died
        mock_popen.return_value = proc
        assert _start_via_scoop() is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_wsl_returncode_nonzero(self, mock_find, mock_run, mock_popen):
        """Line 335->343: WSL Popen returncode != 0 → fall through."""
        from attune.memory.redis_bootstrap import _start_via_wsl

        mock_find.return_value = "C:\\wsl.exe"
        mock_run.return_value = (True, "")
        proc = MagicMock()
        proc.returncode = 1
        proc.wait = MagicMock()
        mock_popen.return_value = proc
        assert _start_via_wsl() is False

    @patch("attune.memory.redis_bootstrap.IS_LINUX", new=False)
    @patch("attune.memory.redis_bootstrap.IS_MACOS", new=False)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", new=False)
    @patch("attune.memory.redis_bootstrap._check_redis_running", return_value=False)
    @patch("attune.memory.redis_bootstrap._start_via_docker", return_value=False)
    @patch("attune.memory.redis_bootstrap._start_via_direct", return_value=False)
    def test_other_platform_no_specific_methods(self, mock_direct, mock_docker, mock_check):
        """Line 431->441: not mac/linux/windows → only docker+direct attempted."""
        from attune.memory.redis_bootstrap import _try_start_methods

        result = _try_start_methods("localhost", 6379, verbose=False)
        assert result is None

    @patch("attune.memory.redis_bootstrap.sys.stdin")
    def test_interactive_install_should_not_prompt(self, mock_stdin, monkeypatch):
        """Line 475->487: detector.should_prompt returns False → falls through."""
        import sys
        from types import SimpleNamespace

        from attune.memory.redis_bootstrap import _try_interactive_install

        mock_stdin.isatty.return_value = True

        fake_detector = MagicMock()
        fake_detector.should_prompt.return_value = False
        fake_module = SimpleNamespace(RedisAutoDetector=lambda: fake_detector)
        monkeypatch.setitem(sys.modules, "attune.memory.redis_auto_detect", fake_module)
        assert _try_interactive_install("localhost", 6379) is None

    @patch("attune.memory.redis_bootstrap.sys.stdin")
    def test_interactive_install_prompt_declined(self, mock_stdin, monkeypatch):
        """Line 476->487: prompt_install returns False → falls through."""
        import sys
        from types import SimpleNamespace

        from attune.memory.redis_bootstrap import _try_interactive_install

        mock_stdin.isatty.return_value = True

        fake_detector = MagicMock()
        fake_detector.should_prompt.return_value = True
        fake_detector.prompt_install.return_value = False
        fake_module = SimpleNamespace(RedisAutoDetector=lambda: fake_detector)
        monkeypatch.setitem(sys.modules, "attune.memory.redis_auto_detect", fake_module)
        assert _try_interactive_install("localhost", 6379) is None

    @patch("attune.memory.redis_bootstrap.sys.stdin")
    def test_interactive_install_prompt_succeeds_but_redis_still_down(
        self, mock_stdin, monkeypatch
    ):
        """Line 476->487: prompt_install returns True but _check_redis_running False."""
        import sys
        from types import SimpleNamespace

        from attune.memory.redis_bootstrap import _try_interactive_install

        mock_stdin.isatty.return_value = True

        fake_detector = MagicMock()
        fake_detector.should_prompt.return_value = True
        fake_detector.prompt_install.return_value = True
        fake_module = SimpleNamespace(RedisAutoDetector=lambda: fake_detector)
        monkeypatch.setitem(sys.modules, "attune.memory.redis_auto_detect", fake_module)

        with patch("attune.memory.redis_bootstrap._check_redis_running", return_value=False):
            assert _try_interactive_install("localhost", 6379) is None
