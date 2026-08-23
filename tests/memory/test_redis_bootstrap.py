"""Comprehensive tests for Redis Bootstrap Module

Tests cover:
- Platform detection
- Redis availability checking
- Multiple start methods (Homebrew, systemd, Docker, Windows Service, etc.)
- Redis stopping
- Error handling and edge cases
- Mock fallback scenarios
- Cross-platform code paths

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

# Check if redis is available
try:
    import redis  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from attune.memory.redis_bootstrap import (
    RedisStartMethod,
    RedisStatus,
    _check_redis_running,
    _find_command,
    _run_silent,
    _start_via_chocolatey,
    _start_via_direct,
    _start_via_docker,
    _start_via_homebrew,
    _start_via_scoop,
    _start_via_systemd,
    _start_via_windows_service,
    _start_via_wsl,
    ensure_redis,
    get_redis_or_mock,
    stop_redis,
)
from tests.support.redis_stub import RespStub, closed_port


class TestRedisStatus:
    """Test RedisStatus dataclass"""

    def test_redis_status_creation(self):
        """Test creating RedisStatus with various parameters"""
        status = RedisStatus(
            available=True,
            method=RedisStartMethod.HOMEBREW,
            host="localhost",
            port=6379,
            message="Redis started successfully",
            pid=12345,
        )
        assert status.available is True
        assert status.method == RedisStartMethod.HOMEBREW
        assert status.host == "localhost"
        assert status.port == 6379
        assert status.message == "Redis started successfully"
        assert status.pid == 12345

    def test_redis_status_defaults(self):
        """Test RedisStatus default values"""
        status = RedisStatus(
            available=False,
            method=RedisStartMethod.MOCK,
        )
        assert status.host == "127.0.0.1"
        assert status.port == 6379
        assert status.message == ""
        assert status.pid is None


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis package not installed")
class TestCheckRedisRunning:
    """Test _check_redis_running against real endpoints.

    These previously patched ``redis.Redis`` and asserted the kwargs it
    was called with — which proved the mock got the arguments the test
    handed it, and said nothing about which endpoint was dialled. That
    is how library-review H1 (a probe hard-coded to 127.0.0.1:6379 while
    clients connect to the resolved endpoint) survived. Real sockets
    now; the resolver-default path is covered in
    ``tests/unit/memory/test_probe_endpoint_agreement.py``.
    """

    def test_explicit_endpoint_that_answers_is_reported_running(self):
        """An explicit host/port — how ensure_redis probes a server it starts."""
        stub = RespStub()
        try:
            assert _check_redis_running("127.0.0.1", stub.port) is True
        finally:
            stub.close()

    def test_explicit_endpoint_with_nothing_listening_is_reported_down(self):
        assert _check_redis_running("127.0.0.1", closed_port()) is False

    def test_an_explicit_endpoint_overrides_the_resolved_one(self, monkeypatch):
        """The override must actually win, in both directions."""
        stub = RespStub()
        dead = closed_port()
        try:
            monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{dead}/0")
            assert _check_redis_running("127.0.0.1", stub.port) is True

            monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{stub.port}/0")
            assert _check_redis_running("127.0.0.1", dead) is False
        finally:
            stub.close()


class TestFindCommand:
    """Test _find_command function"""

    @patch("attune.memory.redis_bootstrap.shutil.which")
    def test_command_found(self, mock_which):
        """Test when command is found in PATH"""
        mock_which.return_value = "/usr/local/bin/redis-server"
        result = _find_command("redis-server")
        assert result == "/usr/local/bin/redis-server"
        mock_which.assert_called_once_with("redis-server")

    @patch("attune.memory.redis_bootstrap.shutil.which")
    def test_command_not_found(self, mock_which):
        """Test when command is not found"""
        mock_which.return_value = None
        result = _find_command("nonexistent-command")
        assert result is None


class TestRunSilent:
    """Test _run_silent function"""

    @patch("attune.memory.redis_bootstrap.subprocess.run")
    def test_successful_command(self, mock_run):
        """Test successful command execution"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        success, output = _run_silent(["echo", "test"])
        assert success is True
        assert "Success output" in output

    @patch("attune.memory.redis_bootstrap.subprocess.run")
    def test_failed_command(self, mock_run):
        """Test failed command execution"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error message"
        mock_run.return_value = mock_result

        success, output = _run_silent(["false"])
        assert success is False
        assert "Error message" in output

    @patch("attune.memory.redis_bootstrap.subprocess.run")
    def test_command_timeout(self, mock_run):
        """Test command timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)

        success, output = _run_silent(["sleep", "10"], timeout=5)
        assert success is False
        assert output == "timeout"

    @patch("attune.memory.redis_bootstrap.subprocess.run")
    def test_command_exception(self, mock_run):
        """Test command raising exception"""
        mock_run.side_effect = Exception("Command failed")

        success, output = _run_silent(["bad-command"])
        assert success is False
        assert "Command failed" in output


class TestStartViaHomebrew:
    """Test _start_via_homebrew function"""

    @patch("attune.memory.redis_bootstrap._find_command")
    def test_homebrew_not_installed(self, mock_find):
        """Test when Homebrew is not installed"""
        mock_find.return_value = None
        result = _start_via_homebrew()
        assert result is False

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_redis_not_installed_via_homebrew(self, mock_sleep, mock_find, mock_run):
        """Test when redis is not installed via Homebrew"""
        mock_find.return_value = "/usr/local/bin/brew"
        mock_run.return_value = (False, "redis not found")

        result = _start_via_homebrew()
        assert result is False
        mock_run.assert_called_once_with(["brew", "list", "redis"])

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_homebrew_start_success(self, mock_sleep, mock_find, mock_run):
        """Test successful Redis start via Homebrew"""
        mock_find.return_value = "/usr/local/bin/brew"
        # First call checks if redis is installed, second call starts it
        mock_run.side_effect = [(True, "redis installed"), (True, "Started")]

        result = _start_via_homebrew()
        assert result is True
        assert mock_run.call_count == 2

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_homebrew_start_fails(self, mock_sleep, mock_find, mock_run):
        """Test when Homebrew fails to start Redis"""
        mock_find.return_value = "/usr/local/bin/brew"
        mock_run.side_effect = [(True, "redis installed"), (False, "Failed to start")]

        result = _start_via_homebrew()
        assert result is False


class TestStartViaSystemd:
    """Test _start_via_systemd function"""

    @patch("attune.memory.redis_bootstrap._find_command")
    def test_systemd_not_available(self, mock_find):
        """Test when systemd is not available"""
        mock_find.return_value = None
        result = _start_via_systemd()
        assert result is False

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_systemd_start_success(self, mock_sleep, mock_find, mock_run):
        """Test successful Redis start via systemd"""
        mock_find.return_value = "/usr/bin/systemctl"
        mock_run.return_value = (True, "Started")

        result = _start_via_systemd()
        assert result is True
        mock_run.assert_called_once_with(["systemctl", "start", "redis"], timeout=10)

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_systemd_fallback_to_redis_server(self, mock_sleep, mock_find, mock_run):
        """Test systemd fallback to redis-server service name"""
        mock_find.return_value = "/usr/bin/systemctl"
        # First attempt fails, second succeeds
        mock_run.side_effect = [(False, "Failed"), (True, "Started")]

        result = _start_via_systemd()
        assert result is True
        assert mock_run.call_count == 2


class TestStartViaDocker:
    """Test _start_via_docker function"""

    @patch("attune.memory.redis_bootstrap._find_command")
    def test_docker_not_installed(self, mock_find):
        """Test when Docker is not installed"""
        mock_find.return_value = None
        result = _start_via_docker()
        assert result is False

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_docker_daemon_not_running(self, mock_find, mock_run):
        """Test when Docker daemon is not running"""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.return_value = (False, "Cannot connect to Docker daemon")

        result = _start_via_docker()
        assert result is False

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_docker_start_existing_container(self, mock_sleep, mock_find, mock_run):
        """Test starting existing Docker container"""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.side_effect = [
            (True, "Docker info"),  # docker info
            (True, "empathy-redis"),  # docker ps -a (container exists)
            (True, "Started"),  # docker start
        ]

        result = _start_via_docker()
        assert result is True

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_docker_create_new_container(self, mock_sleep, mock_find, mock_run):
        """Test creating new Docker container"""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.side_effect = [
            (True, "Docker info"),  # docker info
            (True, ""),  # docker ps -a (no container)
            (True, "Container created"),  # docker run
        ]

        result = _start_via_docker()
        assert result is True

    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_docker_custom_port(self, mock_sleep, mock_find, mock_run):
        """Test Docker with custom port"""
        mock_find.return_value = "/usr/bin/docker"
        mock_run.side_effect = [
            (True, "Docker info"),
            (True, ""),
            (True, "Container created"),
        ]

        result = _start_via_docker(port=6380)
        assert result is True
        # Check that the port was used in docker run command
        docker_run_call = mock_run.call_args_list[2]
        assert "-p" in docker_run_call[0][0]
        assert "6380:6379" in docker_run_call[0][0]


class TestStartViaDirect:
    """_start_via_direct refuses on every platform (chair-ruled C4, 2026-08-23).

    A config-less redis-server listened on every interface with no
    password, masked the crash-looping configured stack, and wrote
    dump.rdb into the caller's cwd. The method now returns False without
    spawning — on Unix AND Windows, binary on PATH or not.
    """

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap._find_command", return_value=None)
    def test_refuses_without_binary(self, mock_find, mock_popen):
        assert _start_via_direct() is False
        mock_popen.assert_not_called()

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch("attune.memory.redis_bootstrap._find_command", return_value="/usr/bin/redis-server")
    def test_refuses_on_unix_with_binary(self, mock_find, mock_popen):
        assert _start_via_direct() is False
        mock_popen.assert_not_called()

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap.subprocess.Popen")
    @patch(
        "attune.memory.redis_bootstrap._find_command",
        return_value="C:\\Program Files\\Redis\\redis-server.exe",
    )
    def test_refuses_on_windows_with_binary(self, mock_find, mock_popen):
        assert _start_via_direct() is False
        mock_popen.assert_not_called()


class TestStartViaWindowsService:
    """Test _start_via_windows_service function"""

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_not_on_windows(self):
        """Test when not on Windows"""
        result = _start_via_windows_service()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_windows_service_start_success(self, mock_sleep, mock_run):
        """Test successful Windows service start"""
        mock_run.return_value = (True, "Service started")

        result = _start_via_windows_service()
        assert result is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap.time.sleep")
    def test_windows_service_already_started(self, mock_sleep, mock_run):
        """Test when service is already started"""
        mock_run.return_value = (False, "already been started")

        result = _start_via_windows_service()
        assert result is True


class TestStartViaChocolatey:
    """Test _start_via_chocolatey function"""

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_not_on_windows(self):
        """Test when not on Windows"""
        result = _start_via_chocolatey()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_chocolatey_not_installed(self, mock_find):
        """Test when Chocolatey is not installed"""
        mock_find.return_value = None
        result = _start_via_chocolatey()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._start_via_windows_service")
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_chocolatey_redis_not_installed(self, mock_find, mock_run, mock_service):
        """Test when redis is not installed via Chocolatey"""
        mock_find.return_value = "C:\\ProgramData\\chocolatey\\bin\\choco.exe"
        mock_run.return_value = (True, "No packages found")

        result = _start_via_chocolatey()
        assert result is False


class TestStartViaScoop:
    """Test _start_via_scoop function"""

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_not_on_windows(self):
        """Test when not on Windows"""
        result = _start_via_scoop()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_scoop_not_installed(self, mock_find):
        """Test when Scoop is not installed"""
        mock_find.return_value = None
        result = _start_via_scoop()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_scoop_redis_not_installed(self, mock_find, mock_run):
        """Test when redis is not installed via Scoop"""
        mock_find.return_value = "C:\\Users\\user\\scoop\\shims\\scoop.cmd"
        mock_run.return_value = (True, "No packages found")

        result = _start_via_scoop()
        assert result is False


class TestStartViaWSL:
    """Test _start_via_wsl function"""

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    def test_not_on_windows(self):
        """Test when not on Windows"""
        result = _start_via_wsl()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_wsl_not_installed(self, mock_find):
        """Test when WSL is not installed"""
        mock_find.return_value = None
        result = _start_via_wsl()
        assert result is False

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    @patch("attune.memory.redis_bootstrap._find_command")
    def test_wsl_redis_not_installed(self, mock_find, mock_run):
        """Test when redis is not installed in WSL"""
        mock_find.return_value = "C:\\Windows\\System32\\wsl.exe"
        mock_run.return_value = (False, "redis-server not found")

        result = _start_via_wsl()
        assert result is False


class TestEnsureRedis:
    """Test ensure_redis function"""

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    def test_redis_already_running(self, mock_check):
        """Test when Redis is already running"""
        mock_check.return_value = True

        status = ensure_redis(verbose=False)
        assert status.available is True
        assert status.method == RedisStartMethod.ALREADY_RUNNING

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    def test_auto_start_disabled(self, mock_check):
        """Test when auto_start is disabled"""
        mock_check.return_value = False

        status = ensure_redis(auto_start=False, verbose=False)
        assert status.available is False
        assert status.method == RedisStartMethod.MOCK

    @patch("attune.memory.redis_bootstrap.IS_MACOS", True)
    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_homebrew")
    def test_macos_homebrew_success(self, mock_homebrew, mock_check):
        """Test successful start via Homebrew on macOS"""
        mock_check.side_effect = [False, True]  # Not running, then running
        mock_homebrew.return_value = True

        status = ensure_redis(verbose=False)
        assert status.available is True
        assert status.method == RedisStartMethod.HOMEBREW

    @patch("attune.memory.redis_bootstrap.IS_MACOS", False)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", True)
    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_systemd")
    def test_linux_systemd_success(self, mock_systemd, mock_check):
        """Test successful start via systemd on Linux"""
        mock_check.side_effect = [False, True]
        mock_systemd.return_value = True

        status = ensure_redis(verbose=False)
        assert status.available is True
        assert status.method == RedisStartMethod.SYSTEMD

    @patch("attune.memory.redis_bootstrap.IS_MACOS", False)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", False)
    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_windows_service")
    def test_windows_service_success(self, mock_service, mock_check):
        """Test successful start via Windows Service"""
        mock_check.side_effect = [False, True]
        mock_service.return_value = True

        status = ensure_redis(verbose=False)
        assert status.available is True
        assert status.method == RedisStartMethod.WINDOWS_SERVICE

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    @patch("attune.memory.redis_bootstrap.IS_LINUX", False)
    @patch("attune.memory.redis_bootstrap.IS_MACOS", True)
    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_homebrew")
    @patch("attune.memory.redis_bootstrap._start_via_docker")
    @patch("attune.memory.redis_bootstrap._start_via_direct")
    def test_fallback_to_docker(self, mock_direct, mock_docker, mock_homebrew, mock_check):
        """Test fallback to Docker when Homebrew fails"""
        mock_check.side_effect = [False, True]  # Initial check False, verify after Docker True
        mock_homebrew.return_value = False
        mock_docker.return_value = True
        mock_direct.return_value = False  # Prevent fallback to direct

        status = ensure_redis(verbose=False)
        assert status.available is True
        assert status.method == RedisStartMethod.DOCKER

    @patch("attune.memory.redis_bootstrap.IS_MACOS", True)
    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_homebrew")
    @patch("attune.memory.redis_bootstrap._start_via_docker")
    @patch("attune.memory.redis_bootstrap._start_via_direct")
    def test_all_methods_fail(self, mock_direct, mock_docker, mock_homebrew, mock_check):
        """Test when all start methods fail"""
        mock_check.return_value = False
        mock_homebrew.return_value = False
        mock_docker.return_value = False
        mock_direct.return_value = False

        status = ensure_redis(verbose=False)
        assert status.available is False
        assert status.method == RedisStartMethod.MOCK

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    def test_custom_host_port(self, mock_check):
        """Test with custom host and port"""
        mock_check.return_value = True

        status = ensure_redis(host="192.168.1.100", port=6380, verbose=False)
        assert status.available is True
        assert status.host == "192.168.1.100"
        assert status.port == 6380


class TestStopRedis:
    """Test stop_redis function"""

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stop_homebrew(self, mock_run):
        """Test stopping Redis started via Homebrew"""
        mock_run.return_value = (True, "Stopped")

        result = stop_redis(RedisStartMethod.HOMEBREW)
        assert result is True
        mock_run.assert_called_once_with(["brew", "services", "stop", "redis"])

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stop_systemd(self, mock_run):
        """Test stopping Redis started via systemd"""
        mock_run.return_value = (True, "Stopped")

        result = stop_redis(RedisStartMethod.SYSTEMD)
        assert result is True

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stop_systemd_fallback(self, mock_run):
        """Test systemd stop with fallback"""
        mock_run.side_effect = [(False, "Failed"), (True, "Stopped")]

        result = stop_redis(RedisStartMethod.SYSTEMD)
        assert result is True

    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stop_docker(self, mock_run):
        """Test stopping Docker container"""
        mock_run.return_value = (True, "Stopped")

        result = stop_redis(RedisStartMethod.DOCKER)
        assert result is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", True)
    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stop_windows_service(self, mock_run):
        """Test stopping Windows service"""
        mock_run.return_value = (True, "Stopped")

        result = stop_redis(RedisStartMethod.WINDOWS_SERVICE)
        assert result is True

    @patch("attune.memory.redis_bootstrap.IS_WINDOWS", False)
    @patch("attune.memory.redis_bootstrap._find_command")
    @patch("attune.memory.redis_bootstrap._run_silent")
    def test_stop_direct_unix(self, mock_run, mock_find):
        """Test stopping directly started Redis on Unix"""
        mock_find.return_value = "/usr/bin/redis-cli"
        mock_run.return_value = (True, "OK")

        result = stop_redis(RedisStartMethod.DIRECT)
        assert result is True

    def test_stop_already_running(self):
        """Test stopping Redis that was already running"""
        result = stop_redis(RedisStartMethod.ALREADY_RUNNING)
        assert result is False

    def test_stop_mock(self):
        """Test stopping mock Redis"""
        result = stop_redis(RedisStartMethod.MOCK)
        assert result is False


class TestGetRedisOrMock:
    """Test get_redis_or_mock convenience function"""

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="redis not installed")
    @patch("attune.memory.short_term.base.redis.Redis")
    @patch("attune.memory.redis_bootstrap.ensure_redis")
    def test_get_redis_real_connection(self, mock_ensure, mock_redis_cls):
        """Test getting real Redis connection"""
        mock_status = RedisStatus(
            available=True,
            method=RedisStartMethod.ALREADY_RUNNING,
        )
        mock_ensure.return_value = mock_status
        mock_redis_cls.return_value.ping.return_value = True

        memory, status = get_redis_or_mock()
        assert status.available is True
        assert memory is not None

    @patch("attune.memory.redis_bootstrap.ensure_redis")
    def test_get_redis_fallback_to_mock(self, mock_ensure):
        """Test fallback to mock when Redis unavailable"""
        mock_status = RedisStatus(
            available=False,
            method=RedisStartMethod.MOCK,
        )
        mock_ensure.return_value = mock_status

        memory, status = get_redis_or_mock()
        assert status.available is False
        assert memory is not None

    @patch("attune.memory.redis_bootstrap.ensure_redis")
    def test_get_redis_custom_host_port(self, mock_ensure):
        """Test with custom host and port (mock fallback)"""
        # When Redis is unavailable, should fall back to mock
        mock_status = RedisStatus(
            available=False,
            method=RedisStartMethod.DOCKER,  # Method doesn't matter when not available
            host="192.168.1.100",
            port=6380,
        )
        mock_ensure.return_value = mock_status

        memory, status = get_redis_or_mock(host="192.168.1.100", port=6380)
        assert status.host == "192.168.1.100"
        assert status.port == 6380
        assert memory is not None  # Should get a mock memory


class TestEdgeCases:
    """Test edge cases and error handling"""

    @patch("attune.memory.redis_bootstrap._check_redis_running")
    def test_ensure_redis_with_verbose_output(self, mock_check, capsys):
        """Test verbose output mode"""
        mock_check.return_value = True

        status = ensure_redis(verbose=True)
        # Just verify it doesn't crash with verbose mode
        assert status.available is True

    @patch("attune.memory.redis_bootstrap.IS_MACOS", True)
    @patch("attune.memory.redis_bootstrap._check_redis_running")
    @patch("attune.memory.redis_bootstrap._start_via_homebrew")
    def test_ensure_redis_start_exception_handling(self, mock_homebrew, mock_check):
        """Test exception handling in start methods"""
        mock_check.return_value = False
        mock_homebrew.side_effect = Exception("Unexpected error")

        status = ensure_redis(verbose=False)
        # Should continue to next method despite exception
        assert status is not None

    @patch("attune.memory.redis_bootstrap.subprocess.run")
    def test_run_silent_with_combined_output(self, mock_run):
        """Test _run_silent combines stdout and stderr"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "stdout output"
        mock_result.stderr = "stderr output"
        mock_run.return_value = mock_result

        success, output = _run_silent(["test"])
        assert "stdout output" in output
        assert "stderr output" in output
