"""Tests for empathy_llm_toolkit agent_factory decorators module.

Comprehensive test coverage for decorator functions.

Created: 2026-01-20
Coverage target: 80%+
"""

import asyncio
from unittest.mock import patch

import pytest

from attune.agent_factory.decorators import (
    graceful_degradation,
    log_performance,
    retry_on_failure,
    safe_agent_operation,
    validate_input,
    with_cost_tracking,
)

# =============================================================================
# safe_agent_operation Tests
# =============================================================================


class TestSafeAgentOperation:
    """Tests for safe_agent_operation decorator."""

    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test decorator with successful operation."""

        class TestAgent:
            name = "TestAgent"

            @safe_agent_operation("test_op")
            async def do_something(self, data):
                return {"result": data}

        agent = TestAgent()
        result = await agent.do_something("test_data")

        assert result == {"result": "test_data"}

    @pytest.mark.asyncio
    async def test_operation_failure_raises_agent_error(self):
        """Test that failures raise AgentOperationError."""
        from attune.config.agent_config import AgentOperationError

        class TestAgent:
            @safe_agent_operation("failing_op")
            async def fail_operation(self, data):
                raise ValueError("Test error")

        agent = TestAgent()

        with pytest.raises(AgentOperationError) as exc_info:
            await agent.fail_operation("data")

        assert "failing_op" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_uses_class_name_when_no_name_attribute(self):
        """Test fallback to class name when no name attribute."""

        class AgentWithoutName:
            @safe_agent_operation("test_op")
            async def operation(self):
                return "success"

        agent = AgentWithoutName()
        result = await agent.operation()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_adds_audit_entry_on_failure(self):
        """Test that audit entry is added on failure."""
        from attune.config.agent_config import AgentOperationError

        class TestAgent:
            name = "AuditedAgent"

            def __init__(self):
                self.audit_entries = []

            def add_audit_entry(self, state, action, details):
                self.audit_entries.append(
                    {
                        "state": state,
                        "action": action,
                        "details": details,
                    },
                )

            @safe_agent_operation("audited_op")
            async def operation_with_audit(self, state=None):
                raise RuntimeError("Test failure")

        agent = TestAgent()

        with pytest.raises(AgentOperationError):
            await agent.operation_with_audit(state={"user": "test"})

        assert len(agent.audit_entries) == 1
        assert agent.audit_entries[0]["action"] == "audited_op_error"
        assert "Test failure" in agent.audit_entries[0]["details"]["error"]

    @pytest.mark.asyncio
    async def test_extracts_state_from_args(self):
        """Test state extraction from positional args."""
        from attune.config.agent_config import AgentOperationError

        class TestAgent:
            name = "ArgAgent"
            audit_entries = []

            def add_audit_entry(self, state, action, details):
                self.audit_entries.append({"state": state})

            @safe_agent_operation("arg_op")
            async def operation(self, state_dict):
                raise ValueError("Error")

        agent = TestAgent()

        with pytest.raises(AgentOperationError):
            await agent.operation({"key": "value"})

        assert len(agent.audit_entries) == 1
        assert agent.audit_entries[0]["state"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_audit_entry_failure_is_silent(self):
        """Test that audit entry failures don't break the decorator."""
        from attune.config.agent_config import AgentOperationError

        class TestAgent:
            name = "BrokenAuditAgent"

            def add_audit_entry(self, state, action, details):
                raise Exception("Audit failed")

            @safe_agent_operation("broken_audit_op")
            async def operation(self):
                raise ValueError("Operation failed")

        agent = TestAgent()

        # Should still raise the original error, not audit error
        with pytest.raises(AgentOperationError):
            await agent.operation()


# =============================================================================
# retry_on_failure Tests
# =============================================================================


class TestRetryOnFailure:
    """Tests for retry_on_failure decorator."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful operation on first attempt."""

        @retry_on_failure(max_attempts=3)
        async def successful_operation():
            return "success"

        result = await successful_operation()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self):
        """Test retry with eventual success."""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.01)
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = await flaky_operation()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_all_attempts_fail(self):
        """Test when all retry attempts fail."""

        @retry_on_failure(max_attempts=3, delay=0.01)
        async def always_fails():
            raise ValueError("Permanent failure")

        with pytest.raises(ValueError, match="Permanent failure"):
            await always_fails()

    @pytest.mark.asyncio
    async def test_only_catches_specified_exceptions(self):
        """Test that only specified exceptions are caught."""

        @retry_on_failure(max_attempts=3, exceptions=(ValueError,), delay=0.01)
        async def raises_type_error():
            raise TypeError("Unexpected error")

        # TypeError should not be caught
        with pytest.raises(TypeError):
            await raises_type_error()

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        call_times = []

        @retry_on_failure(max_attempts=3, delay=0.1, backoff=2.0)
        async def track_timing():
            call_times.append(asyncio.get_event_loop().time())
            raise ValueError("Retry")

        with pytest.raises(ValueError):
            await track_timing()

        assert len(call_times) == 3
        # Check delays increased (approximately)
        if len(call_times) >= 2:
            first_delay = call_times[1] - call_times[0]
            assert first_delay >= 0.08  # Allow some tolerance


# =============================================================================
# log_performance Tests
# =============================================================================


class _ScriptedClock:
    """Stand-in for the ``time`` module returning exact, scripted readings.

    Substituted for ``attune.agent_factory.decorators.time`` so elapsed
    durations are decided by the test rather than measured from a real
    clock on a loaded CI runner. Each reading list is consumed in order
    and its final value repeats.

    Args:
        monotonic_readings: Successive ``time.monotonic()`` return values.
        wall_readings: Successive ``time.time()`` return values. Defaults
            to ``monotonic_readings``. Set these apart to simulate a
            wall-clock adjustment during the decorated call.
    """

    def __init__(
        self,
        monotonic_readings: list[float],
        wall_readings: list[float] | None = None,
    ) -> None:
        self._monotonic = list(monotonic_readings)
        self._wall = list(monotonic_readings if wall_readings is None else wall_readings)

    @staticmethod
    def _next(readings: list[float]) -> float:
        """Pop the next reading, repeating the last one once exhausted."""
        return readings.pop(0) if len(readings) > 1 else readings[0]

    def monotonic(self) -> float:
        """Return the next scripted monotonic reading."""
        return self._next(self._monotonic)

    def time(self) -> float:
        """Return the next scripted wall-clock reading."""
        return self._next(self._wall)


class TestLogPerformance:
    """Tests for log_performance decorator."""

    @pytest.mark.asyncio
    async def test_fast_operation_no_warning(self, monkeypatch):
        """Test fast operation doesn't log warning."""
        monkeypatch.setattr(
            "attune.agent_factory.decorators.time",
            _ScriptedClock([100.0, 100.1]),
        )

        @log_performance(threshold_seconds=1.0)
        async def fast_operation():
            return "quick"

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            result = await fast_operation()

            assert result == "quick"
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_slow_operation_logs_warning(self, monkeypatch):
        """Test slow operation logs warning."""
        monkeypatch.setattr(
            "attune.agent_factory.decorators.time",
            _ScriptedClock([100.0, 105.0]),
        )

        @log_performance(threshold_seconds=1.0)
        async def slow_operation():
            return "slow"

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            result = await slow_operation()

            assert result == "slow"
            mock_logger.warning.assert_called_once()
            assert "Slow operation" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_backward_wall_clock_jump_still_logs_warning(self, monkeypatch):
        """A backward wall-clock jump must not suppress the slow-operation warning.

        Regression guard for the monotonic fix: the operation really takes
        5s, but the wall clock is set back 1s mid-call. Measuring with
        ``time.time()`` yields a negative elapsed and silently skips the
        warning; ``time.monotonic()`` is unaffected.
        """
        monkeypatch.setattr(
            "attune.agent_factory.decorators.time",
            _ScriptedClock(
                monotonic_readings=[100.0, 105.0],
                wall_readings=[1_000_000.0, 999_999.0],
            ),
        )

        @log_performance(threshold_seconds=1.0)
        async def slow_operation():
            return "slow"

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            result = await slow_operation()

            assert result == "slow"
            mock_logger.warning.assert_called_once()
            assert "Slow operation" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_forward_wall_clock_jump_logs_no_false_warning(self, monkeypatch):
        """A forward wall-clock jump must not fabricate a slow-operation warning.

        Regression guard for the monotonic fix: the operation takes 0.1s,
        but the wall clock jumps forward 500s mid-call. Measuring with
        ``time.time()`` reports a spurious 500s and warns; ``time.monotonic()``
        is unaffected.
        """
        monkeypatch.setattr(
            "attune.agent_factory.decorators.time",
            _ScriptedClock(
                monotonic_readings=[100.0, 100.1],
                wall_readings=[1_000_000.0, 1_000_500.0],
            ),
        )

        @log_performance(threshold_seconds=1.0)
        async def fast_operation():
            return "quick"

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            result = await fast_operation()

            assert result == "quick"
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_real_sleep_over_threshold_logs_warning(self):
        """End-to-end check against the real clock, with a 15x margin.

        The deterministic tests above pin the comparison logic; this one
        confirms the decorator reads a clock that advances with real time.
        The margin is wide enough to absorb a loaded runner and the ~15.6ms
        monotonic granularity on Windows -- do not narrow it.
        """

        @log_performance(threshold_seconds=0.01)
        async def slow_operation():
            await asyncio.sleep(0.15)
            return "slow"

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            result = await slow_operation()

            assert result == "slow"
            mock_logger.warning.assert_called_once()
            assert "Slow operation" in str(mock_logger.warning.call_args)


# =============================================================================
# validate_input Tests
# =============================================================================


class TestValidateInput:
    """Tests for validate_input decorator."""

    @pytest.mark.asyncio
    async def test_valid_input_passes(self):
        """Test valid input passes validation."""

        class TestAgent:
            @validate_input(["name", "value"])
            async def process(self, input_data):
                return input_data

        agent = TestAgent()
        result = await agent.process({"name": "test", "value": 123})

        assert result == {"name": "test", "value": 123}

    @pytest.mark.asyncio
    async def test_missing_field_raises_error(self):
        """Test missing field raises ValueError."""

        class TestAgent:
            @validate_input(["name", "value"])
            async def process(self, input_data):
                return input_data

        agent = TestAgent()

        with pytest.raises(ValueError, match="Missing required fields"):
            await agent.process({"name": "test"})

    @pytest.mark.asyncio
    async def test_non_dict_input_raises_error(self):
        """Test non-dict input raises ValueError."""

        class TestAgent:
            @validate_input(["field"])
            async def process(self, input_data):
                return input_data

        agent = TestAgent()

        with pytest.raises(ValueError, match="Input must be a dict"):
            await agent.process("not a dict")

    @pytest.mark.asyncio
    async def test_empty_required_fields(self):
        """Test with empty required fields list."""

        class TestAgent:
            @validate_input([])
            async def process(self, input_data):
                return input_data

        agent = TestAgent()
        result = await agent.process({})

        assert result == {}


# =============================================================================
# with_cost_tracking Tests
# =============================================================================


class TestWithCostTracking:
    """Tests for with_cost_tracking decorator."""

    @pytest.mark.asyncio
    async def test_cost_tracking_with_metadata(self):
        """Test cost tracking extracts metadata."""

        class TestAgent:
            tracked_costs = []

            def _track_cost(self, operation_id, operation_type, model, tokens):
                self.tracked_costs.append(
                    {
                        "operation_type": operation_type,
                        "model": model,
                        "tokens": tokens,
                    },
                )

            @with_cost_tracking(operation_type="research")
            async def research(self, query):
                return {
                    "content": "result",
                    "metadata": {
                        "tokens_used": 100,
                        "model": "claude-3-sonnet",
                    },
                }

        agent = TestAgent()
        result = await agent.research("test query")

        assert result["content"] == "result"
        assert len(agent.tracked_costs) == 1
        assert agent.tracked_costs[0]["operation_type"] == "research"
        assert agent.tracked_costs[0]["tokens"] == 100

    @pytest.mark.asyncio
    async def test_cost_tracking_without_metadata(self):
        """Test cost tracking with result without metadata."""

        class TestAgent:
            tracked_costs = []

            def _track_cost(self, **kwargs):
                self.tracked_costs.append(kwargs)

            @with_cost_tracking(operation_type="test")
            async def operation(self):
                return {"content": "result"}

        agent = TestAgent()
        result = await agent.operation()

        assert result == {"content": "result"}
        # Still tracks with default values
        assert len(agent.tracked_costs) == 1
        assert agent.tracked_costs[0]["tokens"] == 0
        assert agent.tracked_costs[0]["model"] == "unknown"

    @pytest.mark.asyncio
    async def test_cost_tracking_non_dict_result(self):
        """Test cost tracking with non-dict result."""

        class TestAgent:
            tracked_costs = []

            def _track_cost(self, **kwargs):
                self.tracked_costs.append(kwargs)

            @with_cost_tracking(operation_type="test")
            async def operation(self):
                return "string result"

        agent = TestAgent()
        result = await agent.operation()

        assert result == "string result"
        # No tracking for non-dict result
        assert len(agent.tracked_costs) == 0

    @pytest.mark.asyncio
    async def test_cost_tracking_without_track_method(self):
        """Test when agent doesn't have _track_cost method."""

        class TestAgent:
            @with_cost_tracking(operation_type="test")
            async def operation(self):
                return {
                    "content": "result",
                    "metadata": {"tokens_used": 50},
                }

        agent = TestAgent()
        result = await agent.operation()

        # Should complete without error even without _track_cost
        assert result["content"] == "result"


# =============================================================================
# graceful_degradation Tests
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful_degradation decorator."""

    @pytest.mark.asyncio
    async def test_successful_operation_returns_result(self):
        """Test successful operation returns actual result."""

        @graceful_degradation(fallback_value=[])
        async def operation():
            return [1, 2, 3]

        result = await operation()
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_failure_returns_fallback(self):
        """Test failure returns fallback value."""

        @graceful_degradation(fallback_value="default")
        async def failing_operation():
            raise ValueError("Error")

        result = await failing_operation()
        assert result == "default"

    @pytest.mark.asyncio
    async def test_none_fallback(self):
        """Test None as fallback value."""

        @graceful_degradation(fallback_value=None)
        async def operation():
            raise RuntimeError("Error")

        result = await operation()
        assert result is None

    @pytest.mark.asyncio
    async def test_logs_with_specified_level(self):
        """Test logging with specified log level."""

        @graceful_degradation(fallback_value=[], log_level="error")
        async def operation():
            raise ValueError("Test error")

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            await operation()
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_warning_by_default(self):
        """Test warning log level by default."""

        @graceful_degradation(fallback_value=[])
        async def operation():
            raise ValueError("Test error")

        with patch("attune.agent_factory.decorators.logger") as mock_logger:
            await operation()
            mock_logger.warning.assert_called_once()


# =============================================================================
# Decorator Combination Tests
# =============================================================================


class TestDecoratorCombinations:
    """Tests for combining multiple decorators."""

    @pytest.mark.asyncio
    async def test_retry_with_graceful_degradation(self):
        """Test retry followed by graceful degradation."""
        call_count = 0

        @graceful_degradation(fallback_value="fallback")
        @retry_on_failure(max_attempts=2, delay=0.01)
        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        result = await operation()

        assert result == "fallback"
        assert call_count == 2  # Retried twice then fell back

    @pytest.mark.asyncio
    async def test_validate_with_cost_tracking(self):
        """Test validation with cost tracking."""

        class TestAgent:
            costs = []

            def _track_cost(self, **kwargs):
                self.costs.append(kwargs)

            @with_cost_tracking(operation_type="validated")
            @validate_input(["query"])
            async def process(self, input_data):
                return {
                    "content": input_data["query"],
                    "metadata": {"tokens_used": 10},
                }

        agent = TestAgent()
        result = await agent.process({"query": "test"})

        assert result["content"] == "test"
        assert len(agent.costs) == 1


class TestAuditEntryNonDictArg:
    """Cover line 73->76 branch: args[0] is not a dict → state stays empty."""

    @pytest.mark.asyncio
    async def test_non_dict_first_arg_yields_empty_state(self):
        from attune.agent_factory.decorators import safe_agent_operation
        from attune.config.agent_config import AgentOperationError

        class TestAgent:
            name = "NonDictAgent"
            audit_entries = []

            def add_audit_entry(self, state, action, details):
                self.audit_entries.append({"state": state, "action": action})

            @safe_agent_operation("non_dict_op")
            async def operation(self, value):
                raise ValueError("Boom")

        agent = TestAgent()
        with pytest.raises(AgentOperationError):
            await agent.operation("just-a-string")  # not dict, not state kw

        assert len(agent.audit_entries) == 1
        assert agent.audit_entries[0]["state"] == {}
