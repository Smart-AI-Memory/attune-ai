"""Comprehensive Tests for Memory Control Panel

Target: Boost coverage from 12.2% to 70%+

Test Coverage:
- Security validation functions (_validate_pattern_id, _validate_agent_id, etc.)
- RateLimiter class (tracking, window resets, limits)
- APIKeyAuth class (validation, API key checking)
- MemoryStats and ControlPanelConfig dataclasses
- MemoryControlPanel class methods
- CLI print functions
- Edge cases and error handling

Testing Pattern:
- Use real data (no mocks except for Redis connections)
- Use tmp_path fixtures for file operations
- Test security validation thoroughly
- Use capsys for CLI output testing
"""

import time
from dataclasses import asdict
from unittest.mock import patch

import pytest

from attune.memory.control_panel import (
    PATTERN_ID_ALT_REGEX,
    PATTERN_ID_REGEX,
    APIKeyAuth,
    ControlPanelConfig,
    MemoryControlPanel,
    MemoryStats,
    RateLimiter,
    _validate_agent_id,
    _validate_classification,
    _validate_pattern_id,
    print_health,
    print_stats,
    print_status,
)
from attune.security.path_validation import _validate_file_path

# =============================================================================
# Test Security Validation Functions
# =============================================================================


class TestValidatePatternId:
    """Test pattern ID validation."""

    def test_valid_pattern_id_standard_format(self):
        """Test validation of standard pattern ID format."""
        # Format: pat_YYYYMMDDHHMMSS_hexstring
        assert _validate_pattern_id("pat_20260115123456_abc12345") is True
        assert _validate_pattern_id("pat_20251231235959_deadbeef") is True

    def test_valid_pattern_id_alternative_format(self):
        """Test validation of alternative pattern ID format."""
        # Format: alphanumeric with underscores/hyphens
        assert _validate_pattern_id("pattern-123") is True
        assert _validate_pattern_id("test_pattern_v2") is True
        assert _validate_pattern_id("abc") is True

    def test_invalid_pattern_id_empty(self):
        """Test rejection of empty pattern IDs."""
        assert _validate_pattern_id("") is False
        assert _validate_pattern_id(None) is False

    def test_invalid_pattern_id_wrong_type(self):
        """Test rejection of non-string pattern IDs."""
        assert _validate_pattern_id(123) is False
        assert _validate_pattern_id([]) is False
        assert _validate_pattern_id({}) is False

    def test_invalid_pattern_id_path_traversal(self):
        """Test blocking of path traversal attempts."""
        assert _validate_pattern_id("../etc/passwd") is False
        assert _validate_pattern_id("pattern/../admin") is False
        assert _validate_pattern_id("test/pattern") is False
        assert _validate_pattern_id("test\\pattern") is False

    def test_invalid_pattern_id_null_bytes(self):
        """Test blocking of null byte injection."""
        assert _validate_pattern_id("pattern\x00id") is False
        assert _validate_pattern_id("test\x00.json") is False

    def test_invalid_pattern_id_length_bounds(self):
        """Test length validation."""
        # Too short (< 3)
        assert _validate_pattern_id("ab") is False

        # Too long (> 64)
        long_id = "a" * 65
        assert _validate_pattern_id(long_id) is False

        # Just right
        assert _validate_pattern_id("abc") is True
        assert _validate_pattern_id("a" * 64) is True


class TestValidateAgentId:
    """Test agent ID validation."""

    def test_valid_agent_id_simple(self):
        """Test validation of simple agent IDs."""
        assert _validate_agent_id("admin") is True
        assert _validate_agent_id("user123") is True
        assert _validate_agent_id("agent_001") is True

    def test_valid_agent_id_email_format(self):
        """Test validation of email-style agent IDs."""
        assert _validate_agent_id("user@example.com") is True
        assert _validate_agent_id("admin@system") is True
        assert _validate_agent_id("test.user@domain.com") is True

    def test_valid_agent_id_with_dots_and_dashes(self):
        """Test validation with allowed special characters."""
        assert _validate_agent_id("first.last") is True
        assert _validate_agent_id("user-123") is True
        assert _validate_agent_id("test_user@domain.org") is True

    def test_invalid_agent_id_empty(self):
        """Test rejection of empty agent IDs."""
        assert _validate_agent_id("") is False
        assert _validate_agent_id(None) is False

    def test_invalid_agent_id_wrong_type(self):
        """Test rejection of non-string agent IDs."""
        assert _validate_agent_id(123) is False
        assert _validate_agent_id([]) is False

    def test_invalid_agent_id_dangerous_characters(self):
        """Test blocking of command injection attempts."""
        assert _validate_agent_id("admin;rm -rf /") is False
        assert _validate_agent_id("user|cat /etc/passwd") is False
        assert _validate_agent_id("test&whoami") is False
        assert _validate_agent_id("../etc/passwd") is False
        assert _validate_agent_id("test\\admin") is False

    def test_invalid_agent_id_null_bytes(self):
        """Test blocking of null byte injection."""
        assert _validate_agent_id("admin\x00") is False

    def test_invalid_agent_id_length_bounds(self):
        """Test length validation."""
        # Too long (> 64)
        assert _validate_agent_id("a" * 65) is False

        # Just right
        assert _validate_agent_id("a" * 64) is True


class TestValidateClassification:
    """Test classification validation."""

    def test_valid_classification_uppercase(self):
        """Test validation of uppercase classifications."""
        assert _validate_classification("PUBLIC") is True
        assert _validate_classification("INTERNAL") is True
        assert _validate_classification("SENSITIVE") is True

    def test_valid_classification_lowercase(self):
        """Test validation of lowercase classifications (converted)."""
        assert _validate_classification("public") is True
        assert _validate_classification("internal") is True
        assert _validate_classification("sensitive") is True

    def test_valid_classification_mixed_case(self):
        """Test validation of mixed case classifications."""
        assert _validate_classification("Public") is True
        assert _validate_classification("InTeRnAl") is True

    def test_valid_classification_none(self):
        """Test that None is valid (no filter)."""
        assert _validate_classification(None) is True

    def test_invalid_classification_wrong_value(self):
        """Test rejection of invalid classification values."""
        assert _validate_classification("PRIVATE") is False
        assert _validate_classification("SECRET") is False
        assert _validate_classification("random") is False

    def test_invalid_classification_wrong_type(self):
        """Test rejection of non-string classifications."""
        assert _validate_classification(123) is False
        assert _validate_classification([]) is False


class TestValidateFilePath:
    """Test file path validation."""

    def test_valid_file_path_simple(self, tmp_path):
        """Test validation of simple file paths."""
        path = tmp_path / "test.json"
        validated = _validate_file_path(str(path))
        assert validated == path.resolve()

    def test_valid_file_path_with_allowed_dir(self, tmp_path):
        """Test validation with allowed directory restriction."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        path = allowed / "file.json"

        validated = _validate_file_path(str(path), allowed_dir=str(allowed))
        assert validated == path.resolve()

    def test_invalid_file_path_empty(self):
        """Test rejection of empty paths."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path("")

        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path(None)

    def test_invalid_file_path_wrong_type(self):
        """Test rejection of non-string paths."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path(123)

    def test_invalid_file_path_null_bytes(self):
        """Test blocking of null byte injection."""
        with pytest.raises(ValueError, match="contains null bytes"):
            _validate_file_path("test\x00.json")

    def test_invalid_file_path_system_directories(self):
        """Test blocking of writes to system directories."""
        # Note: On macOS, /etc resolves to /private/etc which starts with /private not /etc
        # So we test the resolved path logic
        # Test that the function tries to resolve and may fail on permission or match the check
        dangerous_paths = ["/sys/test", "/proc/test", "/dev/null"]

        for path in dangerous_paths:
            try:
                result = _validate_file_path(path)
                # If it doesn't raise, check the path starts with a dangerous prefix
                assert not any(str(result).startswith(d) for d in ["/sys", "/proc", "/dev"])
            except (ValueError, OSError):
                # Expected: either validation error or OS error is fine
                pass

    def test_invalid_file_path_outside_allowed_dir(self, tmp_path):
        """Test blocking of paths outside allowed directory."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside" / "file.json"

        with pytest.raises(ValueError, match="outside allowed directory"):
            _validate_file_path(str(outside), allowed_dir=str(allowed))


# =============================================================================
# Test RateLimiter Class
# =============================================================================


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_initialization_default_values(self):
        """Test rate limiter initialization with defaults."""
        limiter = RateLimiter()
        assert limiter.window_seconds == 60
        assert limiter.max_requests == 100
        assert limiter._requests == {}

    def test_initialization_custom_values(self):
        """Test rate limiter initialization with custom values."""
        limiter = RateLimiter(window_seconds=30, max_requests=50)
        assert limiter.window_seconds == 30
        assert limiter.max_requests == 50

    def test_initialization_invalid_window(self):
        """Test rejection of invalid window_seconds."""
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimiter(window_seconds=0)

        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimiter(window_seconds=-1)

    def test_initialization_invalid_max_requests(self):
        """Test rejection of invalid max_requests."""
        with pytest.raises(ValueError, match="max_requests must be positive"):
            RateLimiter(max_requests=0)

        with pytest.raises(ValueError, match="max_requests must be positive"):
            RateLimiter(max_requests=-1)

    def test_is_allowed_first_request(self):
        """Test that first request is always allowed."""
        limiter = RateLimiter(max_requests=10)
        assert limiter.is_allowed("192.168.1.1") is True

    def test_is_allowed_under_limit(self):
        """Test requests under the limit."""
        limiter = RateLimiter(max_requests=5)
        client_ip = "192.168.1.1"

        # Make 4 requests (under limit of 5)
        for _ in range(4):
            assert limiter.is_allowed(client_ip) is True

    def test_is_allowed_at_limit(self):
        """Test behavior at the exact limit."""
        limiter = RateLimiter(max_requests=5)
        client_ip = "192.168.1.1"

        # Make exactly 5 requests (at limit)
        for _ in range(5):
            assert limiter.is_allowed(client_ip) is True

        # 6th request should be blocked
        assert limiter.is_allowed(client_ip) is False

    def test_is_allowed_window_expiration(self):
        """Test that old requests are removed after window expires."""
        limiter = RateLimiter(window_seconds=1, max_requests=2)
        client_ip = "192.168.1.1"

        # Make 2 requests (at limit)
        assert limiter.is_allowed(client_ip) is True
        assert limiter.is_allowed(client_ip) is True

        # 3rd request blocked
        assert limiter.is_allowed(client_ip) is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed(client_ip) is True

    def test_is_allowed_multiple_clients(self):
        """Test that rate limiting is per-client."""
        limiter = RateLimiter(max_requests=2)

        # Client 1 makes 2 requests
        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is False

        # Client 2 should still be allowed
        assert limiter.is_allowed("192.168.1.2") is True
        assert limiter.is_allowed("192.168.1.2") is True

    def test_get_remaining_no_requests(self):
        """Test remaining count with no requests."""
        limiter = RateLimiter(max_requests=10)
        assert limiter.get_remaining("192.168.1.1") == 10

    def test_get_remaining_after_requests(self):
        """Test remaining count decreases with requests."""
        limiter = RateLimiter(max_requests=10)
        client_ip = "192.168.1.1"

        # Make 3 requests
        for _ in range(3):
            limiter.is_allowed(client_ip)

        assert limiter.get_remaining(client_ip) == 7

    def test_get_remaining_at_zero(self):
        """Test remaining count is zero when rate limited."""
        limiter = RateLimiter(max_requests=2)
        client_ip = "192.168.1.1"

        limiter.is_allowed(client_ip)
        limiter.is_allowed(client_ip)

        assert limiter.get_remaining(client_ip) == 0


# =============================================================================
# Test APIKeyAuth Class
# =============================================================================


class TestAPIKeyAuth:
    """Test API key authentication."""

    def test_initialization_with_key(self):
        """Test initialization with explicit API key."""
        auth = APIKeyAuth(api_key="test-key-123")
        assert auth.enabled is True
        assert auth.api_key == "test-key-123"
        assert auth._key_hash is not None

    def test_initialization_from_env(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("EMPATHY_MEMORY_API_KEY", "env-key-456")
        auth = APIKeyAuth()
        assert auth.enabled is True
        assert auth.api_key == "env-key-456"

    def test_initialization_no_key(self, monkeypatch):
        """Test initialization without API key auto-generates one."""
        monkeypatch.delenv("EMPATHY_MEMORY_API_KEY", raising=False)
        auth = APIKeyAuth()
        assert auth.enabled is True
        assert auth._key_hash is not None

    def test_is_valid_correct_key(self):
        """Test validation with correct API key."""
        auth = APIKeyAuth(api_key="correct-key")
        assert auth.is_valid("correct-key") is True

    def test_is_valid_incorrect_key(self):
        """Test validation with incorrect API key."""
        auth = APIKeyAuth(api_key="correct-key")
        assert auth.is_valid("wrong-key") is False

    def test_is_valid_no_key_provided(self):
        """Test validation with no key provided."""
        auth = APIKeyAuth(api_key="correct-key")
        assert auth.is_valid(None) is False
        assert auth.is_valid("") is False

    def test_auto_generated_key_rejects_wrong_keys(self):
        """Test that auto-generated key rejects arbitrary keys."""
        auth = APIKeyAuth(api_key=None)
        assert auth.enabled is True
        # Auto-generated key rejects None and wrong keys
        assert auth.is_valid(None) is False
        assert auth.is_valid("wrong-key") is False


# =============================================================================
# Test MemoryStats Dataclass
# =============================================================================


class TestMemoryStats:
    """Test MemoryStats dataclass."""

    def test_default_initialization(self):
        """Test MemoryStats with default values."""
        stats = MemoryStats()
        assert stats.redis_available is False
        assert stats.redis_method == "none"
        assert stats.redis_keys_total == 0
        assert stats.long_term_available is False
        assert stats.patterns_total == 0
        assert stats.redis_ping_ms == 0.0
        assert stats.collected_at == ""

    def test_custom_initialization(self):
        """Test MemoryStats with custom values."""
        stats = MemoryStats(
            redis_available=True,
            redis_method="docker",
            redis_keys_total=150,
            patterns_total=42,
            redis_ping_ms=1.5,
            collected_at="2026-01-15T12:00:00Z",
        )
        assert stats.redis_available is True
        assert stats.redis_method == "docker"
        assert stats.redis_keys_total == 150
        assert stats.patterns_total == 42
        assert stats.redis_ping_ms == 1.5

    def test_asdict_conversion(self):
        """Test conversion to dictionary."""
        stats = MemoryStats(redis_available=True, patterns_total=10)
        data = asdict(stats)
        assert isinstance(data, dict)
        assert data["redis_available"] is True
        assert data["patterns_total"] == 10


# =============================================================================
# Test ControlPanelConfig Dataclass
# =============================================================================


class TestControlPanelConfig:
    """Test ControlPanelConfig dataclass."""

    def test_default_initialization(self):
        """Test ControlPanelConfig with default values."""
        config = ControlPanelConfig()
        assert config.redis_host == "127.0.0.1"
        assert config.redis_port == 6379
        assert config.storage_dir.endswith("memdocs_storage")
        assert config.audit_dir == "./logs"
        assert config.auto_start_redis is True

    def test_custom_initialization(self):
        """Test ControlPanelConfig with custom values."""
        config = ControlPanelConfig(
            redis_host="redis.example.com",
            redis_port=6380,
            storage_dir="/var/lib/memdocs",
            audit_dir="/var/log/empathy",
            auto_start_redis=False,
        )
        assert config.redis_host == "redis.example.com"
        assert config.redis_port == 6380
        assert config.storage_dir == "/var/lib/memdocs"
        assert config.auto_start_redis is False


# =============================================================================
# Test MemoryControlPanel Class
# =============================================================================


class TestMemoryControlPanelInitialization:
    """Test MemoryControlPanel initialization."""

    def test_initialization_default_config(self):
        """Test initialization with default config."""
        panel = MemoryControlPanel()
        assert panel.config is not None
        assert panel.config.redis_host == "127.0.0.1"
        assert panel._redis_status is None
        assert panel._short_term is None
        assert panel._long_term is None

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = ControlPanelConfig(redis_host="custom-host", redis_port=6380)
        panel = MemoryControlPanel(config=config)
        assert panel.config.redis_host == "custom-host"
        assert panel.config.redis_port == 6380


class TestMemoryControlPanelStatus:
    """Test status() method."""

    @patch("attune.memory.control_panel._check_redis_running")
    def test_status_redis_running(self, mock_check):
        """Test status when Redis is running."""
        mock_check.return_value = True
        panel = MemoryControlPanel()
        status = panel.status()

        assert "timestamp" in status
        assert status["redis"]["status"] == "running"
        assert status["redis"]["host"] == "127.0.0.1"
        assert status["redis"]["port"] == 6379

    @patch("attune.memory.control_panel._check_redis_running")
    def test_status_redis_stopped(self, mock_check):
        """Test status when Redis is stopped."""
        mock_check.return_value = False
        panel = MemoryControlPanel()
        status = panel.status()

        assert status["redis"]["status"] == "stopped"

    @patch("attune.memory.control_panel._check_redis_running")
    def test_status_long_term_not_initialized(self, mock_check, tmp_path):
        """Test status when long-term storage not initialized."""
        mock_check.return_value = False
        config = ControlPanelConfig(storage_dir=str(tmp_path / "nonexistent"))
        panel = MemoryControlPanel(config=config)
        status = panel.status()

        assert status["long_term"]["status"] == "not_initialized"

    @patch("attune.memory.control_panel._check_redis_running")
    def test_status_long_term_available(self, mock_check, tmp_path):
        """Test status when long-term storage is available."""
        mock_check.return_value = False
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        config = ControlPanelConfig(storage_dir=str(storage_dir))
        panel = MemoryControlPanel(config=config)
        status = panel.status()

        assert status["long_term"]["status"] == "available"


class TestMemoryControlPanelPatternCount:
    """Test _count_patterns() method."""

    def test_count_patterns_no_storage(self, tmp_path):
        """Test pattern counting when storage doesn't exist."""
        config = ControlPanelConfig(storage_dir=str(tmp_path / "nonexistent"))
        panel = MemoryControlPanel(config=config)
        count = panel._count_patterns()
        assert count == 0

    def test_count_patterns_empty_storage(self, tmp_path):
        """Test pattern counting with empty storage."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        config = ControlPanelConfig(storage_dir=str(storage_dir))
        panel = MemoryControlPanel(config=config)
        count = panel._count_patterns()
        assert count == 0

    def test_count_patterns_with_files(self, tmp_path):
        """Test pattern counting with pattern files."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        # Create some pattern files
        (storage_dir / "pattern1.json").write_text("{}")
        (storage_dir / "pattern2.json").write_text("{}")
        (storage_dir / "pattern3.json").write_text("{}")

        config = ControlPanelConfig(storage_dir=str(storage_dir))
        panel = MemoryControlPanel(config=config)
        count = panel._count_patterns()
        assert count == 3


class TestMemoryControlPanelListPatterns:
    """Test list_patterns() method."""

    def test_list_patterns_invalid_classification(self):
        """Test list_patterns with invalid classification."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="Invalid classification"):
            panel.list_patterns(classification="INVALID")

    def test_list_patterns_invalid_limit_negative(self):
        """Test list_patterns with negative limit."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="limit must be positive"):
            panel.list_patterns(limit=-1)

    def test_list_patterns_invalid_limit_zero(self):
        """Test list_patterns with zero limit."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="limit must be positive"):
            panel.list_patterns(limit=0)

    def test_list_patterns_invalid_limit_too_large(self):
        """Test list_patterns with limit exceeding maximum."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="limit too large"):
            panel.list_patterns(limit=10001)


class TestMemoryControlPanelDeletePattern:
    """Test delete_pattern() method."""

    def test_delete_pattern_invalid_pattern_id(self):
        """Test delete_pattern with invalid pattern ID."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="Invalid pattern_id format"):
            panel.delete_pattern("../invalid")

    def test_delete_pattern_invalid_user_id(self):
        """Test delete_pattern with invalid user ID."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="Invalid user_id format"):
            panel.delete_pattern("pat_20260115123456_abc12345", user_id="admin;rm -rf /")


class TestMemoryControlPanelClearShortTerm:
    """Test clear_short_term() method."""

    def test_clear_short_term_invalid_agent_id(self):
        """Test clear_short_term with invalid agent ID."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="Invalid agent_id format"):
            panel.clear_short_term(agent_id="../admin")


class TestMemoryControlPanelExportPatterns:
    """Test export_patterns() method."""

    def test_export_patterns_invalid_path(self):
        """Test export_patterns with invalid file path."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="contains null bytes"):
            panel.export_patterns("test\x00.json")

    def test_export_patterns_system_directory(self, tmp_path):
        """Test export_patterns blocking system directory writes."""
        panel = MemoryControlPanel()
        # Test with a path that will be caught during validation
        # Use /sys which is more reliably blocked cross-platform
        try:
            panel.export_patterns("/sys/patterns.json")
            pytest.fail("Should have raised ValueError or PermissionError")
        except (ValueError, PermissionError, OSError):
            # Any of these errors is acceptable for blocking system writes
            pass

    def test_export_patterns_invalid_classification(self):
        """Test export_patterns with invalid classification."""
        panel = MemoryControlPanel()
        with pytest.raises(ValueError, match="Invalid classification"):
            panel.export_patterns("output.json", classification="INVALID")


class TestMemoryControlPanelHealthCheck:
    """Test health_check() method."""

    @patch("attune.memory.control_panel._check_redis_running")
    def test_health_check_all_healthy(self, mock_check, tmp_path):
        """Test health check when all systems are healthy."""
        mock_check.return_value = True
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        (storage_dir / "pattern1.json").write_text("{}")

        config = ControlPanelConfig(storage_dir=str(storage_dir))
        panel = MemoryControlPanel(config=config)

        # Mock get_statistics to return healthy stats
        with patch.object(panel, "get_statistics") as mock_stats:
            mock_stats.return_value = MemoryStats(
                redis_available=True,
                long_term_available=True,
                patterns_total=1,
                patterns_sensitive=0,
                patterns_encrypted=0,
            )
            health = panel.health_check()

        assert health["overall"] == "healthy"
        assert any(
            check["name"] == "redis" and check["status"] == "pass" for check in health["checks"]
        )

    @patch("attune.memory.control_panel._check_redis_running")
    def test_health_check_redis_not_running(self, mock_check):
        """Test health check when Redis is not running."""
        mock_check.return_value = False
        panel = MemoryControlPanel()

        with patch.object(panel, "get_statistics") as mock_stats:
            mock_stats.return_value = MemoryStats(redis_available=False)
            health = panel.health_check()

        assert health["overall"] == "degraded"
        assert any("Start Redis" in rec for rec in health["recommendations"])

    @patch("attune.memory.control_panel._check_redis_running")
    def test_health_check_unencrypted_sensitive_patterns(self, mock_check):
        """Test health check with unencrypted sensitive patterns."""
        mock_check.return_value = True
        panel = MemoryControlPanel()

        with patch.object(panel, "get_statistics") as mock_stats:
            mock_stats.return_value = MemoryStats(
                redis_available=True,
                long_term_available=True,
                patterns_sensitive=5,
                patterns_encrypted=2,  # Some not encrypted
            )
            health = panel.health_check()

        assert health["overall"] == "unhealthy"
        assert any("encryption" in rec.lower() for rec in health["recommendations"])


# =============================================================================
# Test CLI Print Functions
# =============================================================================


class TestPrintStatus:
    """Test print_status() function."""

    @patch("attune.memory.control_panel._check_redis_running")
    def test_print_status_output(self, mock_check, capsys):
        """Test print_status produces expected output."""
        mock_check.return_value = True
        panel = MemoryControlPanel()
        print_status(panel)

        captured = capsys.readouterr()
        assert "EMPATHY MEMORY STATUS" in captured.out
        assert "Redis:" in captured.out
        assert "Long-term Storage:" in captured.out


class TestPrintStats:
    """Test print_stats() function."""

    def test_print_stats_output(self, capsys):
        """Test print_stats produces expected output."""
        panel = MemoryControlPanel()

        with patch.object(panel, "get_statistics") as mock_stats:
            mock_stats.return_value = MemoryStats(
                redis_available=True,
                redis_keys_total=100,
                patterns_total=42,
                redis_ping_ms=1.5,
            )
            print_stats(panel)

        captured = capsys.readouterr()
        assert "EMPATHY MEMORY STATISTICS" in captured.out
        assert "Short-term Memory" in captured.out
        assert "Long-term Memory" in captured.out
        assert "Performance:" in captured.out


class TestPrintHealth:
    """Test print_health() function."""

    @patch("attune.memory.control_panel._check_redis_running")
    def test_print_health_output(self, mock_check, capsys):
        """Test print_health produces expected output."""
        mock_check.return_value = True
        panel = MemoryControlPanel()

        with patch.object(panel, "get_statistics") as mock_stats:
            mock_stats.return_value = MemoryStats(
                redis_available=True,
                long_term_available=True,
                patterns_total=1,
            )
            print_health(panel)

        captured = capsys.readouterr()
        assert "EMPATHY MEMORY HEALTH CHECK" in captured.out
        assert "Overall:" in captured.out
        assert "Checks:" in captured.out


# =============================================================================
# Test Regex Patterns
# =============================================================================


class TestPatternRegex:
    """Test pattern ID regex patterns."""

    def test_standard_pattern_regex_valid(self):
        """Test standard pattern ID regex matches valid patterns."""
        assert PATTERN_ID_REGEX.match("pat_20260115123456_abc12345") is not None
        assert PATTERN_ID_REGEX.match("pat_20251231235959_deadbeef1234") is not None

    def test_standard_pattern_regex_invalid(self):
        """Test standard pattern ID regex rejects invalid patterns."""
        assert PATTERN_ID_REGEX.match("invalid") is None
        assert PATTERN_ID_REGEX.match("pat_2026_abc") is None

    def test_alternative_pattern_regex_valid(self):
        """Test alternative pattern ID regex matches valid patterns."""
        assert PATTERN_ID_ALT_REGEX.match("abc") is not None
        assert PATTERN_ID_ALT_REGEX.match("test_pattern_123") is not None
        assert PATTERN_ID_ALT_REGEX.match("pattern-name") is not None

    def test_alternative_pattern_regex_invalid(self):
        """Test alternative pattern ID regex rejects invalid patterns."""
        assert PATTERN_ID_ALT_REGEX.match("ab") is None  # Too short
        assert PATTERN_ID_ALT_REGEX.match("123abc") is None  # Starts with digit
        assert PATTERN_ID_ALT_REGEX.match("a" * 65) is None  # Too long
