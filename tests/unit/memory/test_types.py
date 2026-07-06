"""Tests for memory types module.

Covers:
- AccessTier enum
- TTLStrategy enum
- RedisConfig dataclass
- RedisMetrics dataclass
- PaginatedResult dataclass
- TimeWindowQuery dataclass
- AgentCredentials dataclass
- StagedPattern dataclass
- ConflictContext dataclass
- SecurityError exception

Copyright 2025 Smart AI Memory, LLC
"""

from datetime import datetime

import pytest

from attune.memory.types import (
    AccessTier,
    AgentCredentials,
    ConflictContext,
    PaginatedResult,
    RedisConfig,
    RedisMetrics,
    SecurityError,
    StagedPattern,
    TimeWindowQuery,
    TTLStrategy,
)

# =============================================================================
# ACCESS TIER
# =============================================================================


class TestAccessTier:
    """Test AccessTier enum."""

    def test_tier_values(self):
        """Test tier values are ordered correctly."""
        assert AccessTier.OBSERVER.value == 1
        assert AccessTier.CONTRIBUTOR.value == 2
        assert AccessTier.VALIDATOR.value == 3
        assert AccessTier.STEWARD.value == 4

    def test_tier_comparison(self):
        """Test tiers can be compared by value."""
        assert AccessTier.OBSERVER.value < AccessTier.CONTRIBUTOR.value
        assert AccessTier.CONTRIBUTOR.value < AccessTier.VALIDATOR.value
        assert AccessTier.VALIDATOR.value < AccessTier.STEWARD.value


# =============================================================================
# TTL STRATEGY
# =============================================================================


class TestTTLStrategy:
    """Test TTLStrategy enum."""

    def test_strategy_values(self):
        """Test TTL values are correct."""
        assert TTLStrategy.WORKING_RESULTS.value == 3600  # 1 hour
        assert TTLStrategy.STAGED_PATTERNS.value == 86400  # 24 hours
        assert TTLStrategy.SESSION.value == 1800  # 30 minutes
        assert TTLStrategy.STREAM_ENTRY.value == 86400 * 7  # 7 days
        assert TTLStrategy.CONFLICT_CONTEXT.value == 604800  # 7 days


# =============================================================================
# REDIS CONFIG
# =============================================================================


class TestRedisConfig:
    """Test RedisConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RedisConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.use_mock is False
        assert config.ssl is False
        assert config.max_connections == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RedisConfig(
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            ssl=True,
            max_connections=50,
        )

        assert config.host == "redis.example.com"
        assert config.port == 6380
        assert config.db == 1
        assert config.password == "secret"
        assert config.ssl is True
        assert config.max_connections == 50

    def test_to_redis_kwargs_basic(self):
        """Test converting to redis.Redis kwargs."""
        config = RedisConfig()
        kwargs = config.to_redis_kwargs()

        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 6379
        assert kwargs["db"] == 0
        assert kwargs["decode_responses"] is True

    def test_to_redis_kwargs_with_ssl(self):
        """Test converting with SSL options."""
        config = RedisConfig(
            ssl=True,
            ssl_cert_reqs="required",
            ssl_ca_certs="/path/to/ca.crt",
        )
        kwargs = config.to_redis_kwargs()

        assert kwargs["ssl"] is True
        assert kwargs["ssl_cert_reqs"] == "required"
        assert kwargs["ssl_ca_certs"] == "/path/to/ca.crt"

    def test_security_settings_defaults(self):
        """Test security settings are enabled by default."""
        config = RedisConfig()

        assert config.pii_scrub_enabled is True
        assert config.secrets_detection_enabled is True


# =============================================================================
# REDIS METRICS
# =============================================================================


class TestRedisMetrics:
    """Test RedisMetrics dataclass."""

    def test_default_values(self):
        """Test default metric values."""
        metrics = RedisMetrics()

        assert metrics.operations_total == 0
        assert metrics.operations_success == 0
        assert metrics.operations_failed == 0
        assert metrics.latency_sum_ms == 0.0

    def test_record_operation_success(self):
        """Test recording successful operation."""
        metrics = RedisMetrics()

        metrics.record_operation("stash", latency_ms=5.0, success=True)

        assert metrics.operations_total == 1
        assert metrics.operations_success == 1
        assert metrics.operations_failed == 0
        assert metrics.stash_count == 1
        assert metrics.latency_sum_ms == 5.0
        assert metrics.latency_max_ms == 5.0

    def test_record_operation_failure(self):
        """Test recording failed operation."""
        metrics = RedisMetrics()

        metrics.record_operation("retrieve", latency_ms=10.0, success=False)

        assert metrics.operations_total == 1
        assert metrics.operations_success == 0
        assert metrics.operations_failed == 1
        assert metrics.retrieve_count == 1

    def test_latency_avg_calculation(self):
        """Test average latency calculation."""
        metrics = RedisMetrics()

        metrics.record_operation("stash", latency_ms=10.0)
        metrics.record_operation("stash", latency_ms=20.0)
        metrics.record_operation("stash", latency_ms=30.0)

        assert metrics.latency_avg_ms == 20.0

    def test_latency_avg_empty(self):
        """Test average latency with no operations."""
        metrics = RedisMetrics()

        assert metrics.latency_avg_ms == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = RedisMetrics()

        metrics.record_operation("stash", latency_ms=5.0, success=True)
        metrics.record_operation("stash", latency_ms=5.0, success=True)
        metrics.record_operation("stash", latency_ms=5.0, success=False)

        assert metrics.success_rate == pytest.approx(66.67, rel=0.1)

    def test_success_rate_empty(self):
        """Test success rate with no operations."""
        metrics = RedisMetrics()

        assert metrics.success_rate == 100.0

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = RedisMetrics()
        metrics.record_operation("stash", latency_ms=5.0)
        metrics.record_operation("retrieve", latency_ms=10.0)

        result = metrics.to_dict()

        assert "operations_total" in result
        assert "latency_avg_ms" in result
        assert "success_rate" in result
        assert "by_operation" in result
        assert "security" in result
        assert result["by_operation"]["stash"] == 1
        assert result["by_operation"]["retrieve"] == 1


# =============================================================================
# PAGINATED RESULT
# =============================================================================


class TestPaginatedResult:
    """Test PaginatedResult dataclass."""

    def test_basic_result(self):
        """Test basic paginated result."""
        result = PaginatedResult(
            items=["a", "b", "c"],
            cursor="abc123",
            has_more=True,
            total_scanned=100,
        )

        assert len(result.items) == 3
        assert result.cursor == "abc123"
        assert result.has_more is True
        assert result.total_scanned == 100

    def test_default_total_scanned(self):
        """Test default total_scanned is 0."""
        result = PaginatedResult(items=[], cursor="", has_more=False)

        assert result.total_scanned == 0


# =============================================================================
# TIME WINDOW QUERY
# =============================================================================


class TestTimeWindowQuery:
    """Test TimeWindowQuery dataclass."""

    def test_default_values(self):
        """Test default query values."""
        query = TimeWindowQuery()

        assert query.start_time is None
        assert query.end_time is None
        assert query.limit == 100
        assert query.offset == 0

    def test_start_score_infinite(self):
        """Test start score is -inf when no start_time."""
        query = TimeWindowQuery()

        assert query.start_score == float("-inf")

    def test_end_score_infinite(self):
        """Test end score is +inf when no end_time."""
        query = TimeWindowQuery()

        assert query.end_score == float("+inf")

    def test_start_score_from_datetime(self):
        """Test start score from datetime."""
        start = datetime(2026, 1, 26, 12, 0, 0)
        query = TimeWindowQuery(start_time=start)

        assert query.start_score == start.timestamp()

    def test_end_score_from_datetime(self):
        """Test end score from datetime."""
        end = datetime(2026, 1, 26, 18, 0, 0)
        query = TimeWindowQuery(end_time=end)

        assert query.end_score == end.timestamp()


# =============================================================================
# AGENT CREDENTIALS
# =============================================================================


class TestAgentCredentials:
    """Test AgentCredentials dataclass."""

    def test_basic_credentials(self):
        """Test basic credentials creation."""
        creds = AgentCredentials(
            agent_id="agent-001",
            tier=AccessTier.CONTRIBUTOR,
        )

        assert creds.agent_id == "agent-001"
        assert creds.tier == AccessTier.CONTRIBUTOR
        assert creds.roles == []

    def test_observer_permissions(self):
        """Test Observer tier permissions."""
        creds = AgentCredentials(agent_id="observer", tier=AccessTier.OBSERVER)

        assert creds.can_read() is True
        assert creds.can_stage() is False
        assert creds.can_validate() is False
        assert creds.can_administer() is False

    def test_contributor_permissions(self):
        """Test Contributor tier permissions."""
        creds = AgentCredentials(agent_id="contributor", tier=AccessTier.CONTRIBUTOR)

        assert creds.can_read() is True
        assert creds.can_stage() is True
        assert creds.can_validate() is False
        assert creds.can_administer() is False

    def test_validator_permissions(self):
        """Test Validator tier permissions."""
        creds = AgentCredentials(agent_id="validator", tier=AccessTier.VALIDATOR)

        assert creds.can_read() is True
        assert creds.can_stage() is True
        assert creds.can_validate() is True
        assert creds.can_administer() is False

    def test_steward_permissions(self):
        """Test Steward tier permissions."""
        creds = AgentCredentials(agent_id="steward", tier=AccessTier.STEWARD)

        assert creds.can_read() is True
        assert creds.can_stage() is True
        assert creds.can_validate() is True
        assert creds.can_administer() is True


# =============================================================================
# STAGED PATTERN
# =============================================================================


class TestStagedPattern:
    """Test StagedPattern dataclass."""

    def test_basic_pattern(self):
        """Test basic staged pattern creation."""
        pattern = StagedPattern(
            pattern_id="pat_001",
            agent_id="agent-001",
            pattern_type="algorithm",
            name="Sorting Algorithm",
            description="Efficient sorting implementation",
        )

        assert pattern.pattern_id == "pat_001"
        assert pattern.agent_id == "agent-001"
        assert pattern.pattern_type == "algorithm"
        assert pattern.confidence == 0.5  # default

    def test_validation_empty_pattern_id(self):
        """Test validation rejects empty pattern_id."""
        with pytest.raises(ValueError, match="pattern_id cannot be empty"):
            StagedPattern(
                pattern_id="",
                agent_id="agent",
                pattern_type="test",
                name="Test",
                description="Test",
            )

    def test_validation_empty_agent_id(self):
        """Test validation rejects empty agent_id."""
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            StagedPattern(
                pattern_id="pat_001",
                agent_id="  ",
                pattern_type="test",
                name="Test",
                description="Test",
            )

    def test_validation_confidence_range(self):
        """Test validation enforces confidence range."""
        with pytest.raises(ValueError, match="confidence must be between"):
            StagedPattern(
                pattern_id="pat_001",
                agent_id="agent",
                pattern_type="test",
                name="Test",
                description="Test",
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="confidence must be between"):
            StagedPattern(
                pattern_id="pat_001",
                agent_id="agent",
                pattern_type="test",
                name="Test",
                description="Test",
                confidence=-0.1,
            )

    def test_validation_context_type(self):
        """Test validation enforces context type."""
        with pytest.raises(TypeError, match="context must be dict"):
            StagedPattern(
                pattern_id="pat_001",
                agent_id="agent",
                pattern_type="test",
                name="Test",
                description="Test",
                context=["not", "a", "dict"],
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        pattern = StagedPattern(
            pattern_id="pat_001",
            agent_id="agent-001",
            pattern_type="algorithm",
            name="Test Pattern",
            description="Test description",
            code="def test(): pass",
            confidence=0.8,
            interests=["test", "example"],
        )

        result = pattern.to_dict()

        assert result["pattern_id"] == "pat_001"
        assert result["agent_id"] == "agent-001"
        assert result["confidence"] == 0.8
        assert "staged_at" in result

    def test_from_dict(self):
        """Test reconstruction from dictionary."""
        data = {
            "pattern_id": "pat_001",
            "agent_id": "agent-001",
            "pattern_type": "algorithm",
            "name": "Test Pattern",
            "description": "Test",
            "staged_at": "2026-01-26T12:00:00",
            "confidence": 0.9,
        }

        pattern = StagedPattern.from_dict(data)

        assert pattern.pattern_id == "pat_001"
        assert pattern.confidence == 0.9


# =============================================================================
# CONFLICT CONTEXT
# =============================================================================


class TestConflictContext:
    """Test ConflictContext dataclass."""

    def test_basic_context(self):
        """Test basic conflict context creation."""
        context = ConflictContext(
            conflict_id="conflict_001",
            positions={"agent1": "use approach A", "agent2": "use approach B"},
            interests={"agent1": ["speed"], "agent2": ["safety"]},
        )

        assert context.conflict_id == "conflict_001"
        assert context.resolved is False
        assert context.resolution is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        context = ConflictContext(
            conflict_id="conflict_001",
            positions={"agent1": "A"},
            interests={"agent1": ["speed"]},
            batna="fallback approach",
            resolved=True,
            resolution="Compromise reached",
        )

        result = context.to_dict()

        assert result["conflict_id"] == "conflict_001"
        assert result["resolved"] is True
        assert result["resolution"] == "Compromise reached"
        assert "created_at" in result

    def test_from_dict(self):
        """Test reconstruction from dictionary."""
        data = {
            "conflict_id": "conflict_001",
            "positions": {"agent1": "A"},
            "interests": {"agent1": ["speed"]},
            "created_at": "2026-01-26T12:00:00",
            "resolved": True,
            "resolution": "Done",
        }

        context = ConflictContext.from_dict(data)

        assert context.conflict_id == "conflict_001"
        assert context.resolved is True


# =============================================================================
# SECURITY ERROR
# =============================================================================


class TestSecurityError:
    """Test SecurityError exception."""

    def test_is_exception(self):
        """Test SecurityError is an Exception."""
        error = SecurityError("Secrets detected")

        assert isinstance(error, Exception)
        assert str(error) == "Secrets detected"

    def test_can_be_raised(self):
        """Test SecurityError can be raised and caught."""
        with pytest.raises(SecurityError, match="API key detected"):
            raise SecurityError("API key detected in data")
