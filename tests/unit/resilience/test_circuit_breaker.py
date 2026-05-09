"""Tests for CircuitBreaker resilience pattern.

These tests cover:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure threshold triggering
- Reset timeout behavior
- Recovery in HALF_OPEN state
- Decorator usage
- Global registry
"""

import time

import pytest

from attune.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker,
)


@pytest.mark.unit
class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(name="test")

        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False

    def test_opens_after_failure_threshold(self):
        """Test circuit opens after failure threshold exceeded."""
        cb = CircuitBreaker(name="test_threshold", failure_threshold=3)

        for _ in range(3):
            cb.record_failure(Exception("test"))

        assert cb.state == CircuitState.OPEN
        assert cb.is_open is True

    def test_stays_closed_below_threshold(self):
        """Test circuit stays closed below failure threshold."""
        cb = CircuitBreaker(name="test_below", failure_threshold=5)

        for _ in range(4):
            cb.record_failure(Exception("test"))

        assert cb.state == CircuitState.CLOSED

    def test_success_resets_failure_count(self):
        """Test success in CLOSED state resets failure count."""
        cb = CircuitBreaker(name="test_reset", failure_threshold=3)

        cb.record_failure(Exception("test"))
        cb.record_failure(Exception("test"))
        cb.record_success()  # Reset
        cb.record_failure(Exception("test"))

        # Should still be closed (only 1 failure since reset)
        assert cb.state == CircuitState.CLOSED

    def test_transitions_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(name="test_halfopen", failure_threshold=1, reset_timeout=0.1)

        cb.record_failure(Exception("test"))
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        # Accessing state triggers transition check
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_successful_half_open_calls(self):
        """Test circuit closes after successful calls in HALF_OPEN."""
        cb = CircuitBreaker(
            name="test_recovery",
            failure_threshold=1,
            reset_timeout=0.1,
            half_open_max_calls=2,
        )

        # Open the circuit
        cb.record_failure(Exception("test"))
        time.sleep(0.15)

        # Should be HALF_OPEN now
        assert cb.state == CircuitState.HALF_OPEN

        # Successful calls in HALF_OPEN
        cb.record_success()
        cb.record_success()

        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        """Test circuit reopens on failure in HALF_OPEN state."""
        cb = CircuitBreaker(name="test_reopen", failure_threshold=1, reset_timeout=0.1)

        # Open the circuit
        cb.record_failure(Exception("test"))
        time.sleep(0.15)

        # Should be HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

        # Failure in HALF_OPEN reopens
        cb.record_failure(Exception("test"))

        assert cb.state == CircuitState.OPEN


@pytest.mark.unit
class TestCircuitBreakerExcludedExceptions:
    """Test excluded exceptions behavior."""

    def test_excluded_exception_does_not_count(self):
        """Test excluded exceptions don't increment failure count."""
        cb = CircuitBreaker(
            name="test_excluded",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )

        # ValueError is excluded
        cb.record_failure(ValueError("excluded"))
        cb.record_failure(ValueError("excluded"))
        cb.record_failure(ValueError("excluded"))

        # Should still be closed
        assert cb.state == CircuitState.CLOSED

    def test_non_excluded_exception_counts(self):
        """Test non-excluded exceptions increment failure count."""
        cb = CircuitBreaker(
            name="test_included",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )

        cb.record_failure(TypeError("included"))
        cb.record_failure(TypeError("included"))

        assert cb.state == CircuitState.OPEN


@pytest.mark.unit
class TestCircuitBreakerTimingMethods:
    """Test timing-related methods."""

    def test_get_time_until_reset_when_open(self):
        """Test get_time_until_reset returns positive value when OPEN."""
        cb = CircuitBreaker(name="test_time", failure_threshold=1, reset_timeout=60)

        cb.record_failure(Exception("test"))

        remaining = cb.get_time_until_reset()

        assert remaining > 0
        assert remaining <= 60

    def test_get_time_until_reset_when_closed(self):
        """Test get_time_until_reset returns 0 when CLOSED."""
        cb = CircuitBreaker(name="test_time_closed", failure_threshold=1)

        remaining = cb.get_time_until_reset()

        assert remaining == 0

    def test_manual_reset(self):
        """Test manual reset returns to CLOSED state."""
        cb = CircuitBreaker(name="test_manual_reset", failure_threshold=1)

        cb.record_failure(Exception("test"))
        assert cb.state == CircuitState.OPEN

        cb.reset()

        assert cb.state == CircuitState.CLOSED


@pytest.mark.unit
class TestCircuitBreakerStats:
    """Test statistics methods."""

    def test_get_stats_returns_dict(self):
        """Test get_stats returns statistics dictionary."""
        cb = CircuitBreaker(name="test_stats", failure_threshold=5)

        cb.record_failure(Exception("test"))
        cb.record_failure(Exception("test"))
        cb.record_success()

        stats = cb.get_stats()

        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert stats["state"] == "closed"


@pytest.mark.unit
class TestCircuitBreakerDecorator:
    """Test circuit_breaker decorator."""

    def test_decorator_wraps_sync_function(self):
        """Test decorator works with sync functions."""
        call_count = 0

        @circuit_breaker(name="test_sync_dec", failure_threshold=3)
        def my_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = my_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_wraps_async_function(self):
        """Test decorator works with async functions."""
        call_count = 0

        @circuit_breaker(name="test_async_dec", failure_threshold=3)
        async def my_async_func():
            nonlocal call_count
            call_count += 1
            return "async success"

        result = await my_async_func()

        assert result == "async success"
        assert call_count == 1

    def test_decorator_raises_circuit_open_error(self):
        """Test decorator raises CircuitOpenError when open."""

        @circuit_breaker(name="test_open_dec", failure_threshold=1, reset_timeout=60)
        def failing_func():
            raise ValueError("always fails")

        # Trigger circuit open
        with pytest.raises(ValueError):
            failing_func()

        # Next call should raise CircuitOpenError
        with pytest.raises(CircuitOpenError):
            failing_func()

    def test_decorator_with_fallback(self):
        """Test decorator calls fallback when circuit open."""

        def fallback_func():
            return "fallback result"

        @circuit_breaker(
            name="test_fallback_dec",
            failure_threshold=1,
            reset_timeout=60,
            fallback=fallback_func,
        )
        def failing_func():
            raise ValueError("always fails")

        # Trigger circuit open
        with pytest.raises(ValueError):
            failing_func()

        # Next call should use fallback
        result = failing_func()

        assert result == "fallback result"


@pytest.mark.unit
class TestCircuitBreakerRegistry:
    """Test global circuit breaker registry."""

    def test_get_circuit_breaker_returns_same_instance(self):
        """Test get_circuit_breaker returns same instance by name."""

        # Create circuit breaker via decorator
        @circuit_breaker(name="registry_test", failure_threshold=5)
        def test_func():
            return "test"

        test_func()

        # Get from registry
        cb = get_circuit_breaker("registry_test")

        assert cb is not None
        assert cb.name == "registry_test"

    def test_get_nonexistent_returns_none(self):
        """Test get_circuit_breaker returns None for unknown name."""
        cb = get_circuit_breaker("nonexistent_circuit")

        assert cb is None


@pytest.mark.unit
class TestCircuitOpenError:
    """Test CircuitOpenError exception."""

    def test_error_contains_name_and_reset_time(self):
        """Test error contains circuit name and reset time."""
        error = CircuitOpenError("test_circuit", 30.5)

        assert "test_circuit" in str(error)
        assert error.name == "test_circuit"
        assert error.reset_time == 30.5


@pytest.mark.unit
class TestCircuitBreakerCoverageGaps:
    """Tests filling specific coverage gaps in circuit_breaker.py."""

    def test_should_reset_returns_true_when_no_failure_time(self):
        """`_should_reset` returns True if no failure has been recorded yet (line 92)."""
        cb = CircuitBreaker(name="x")
        # _last_failure_time is None by default
        assert cb._should_reset() is True

    def test_record_success_in_open_state_no_op(self):
        """record_success() while OPEN (timeout not elapsed) is a no-op (branch 124->exit)."""
        cb = CircuitBreaker(name="open_no_op", failure_threshold=1, reset_timeout=999.0)
        # Force OPEN state by recording a failure
        cb.record_failure(RuntimeError("boom"))
        assert cb._state == CircuitState.OPEN
        prior_success = cb._success_count
        prior_state = cb._state

        # state property would not flip because reset_timeout is huge
        cb.record_success()

        # No state change, no counter movement
        assert cb._state == prior_state
        assert cb._success_count == prior_success

    def test_record_failure_in_open_state_no_transition(self):
        """record_failure() while already OPEN does not re-trigger transition (branch 142->exit)."""
        cb = CircuitBreaker(name="open_no_trans", failure_threshold=1, reset_timeout=999.0)
        cb.record_failure(RuntimeError("first"))
        assert cb._state == CircuitState.OPEN

        # Recording another failure while OPEN — already OPEN, no further transition.
        cb.record_failure(RuntimeError("second"))
        assert cb._state == CircuitState.OPEN
        # failure_count keeps incrementing
        assert cb._failure_count >= 2

    def test_decorator_with_excluded_exceptions_provided(self):
        """Calling decorator with excluded_exceptions skips the None-default branch (214->217)."""

        # Use a unique name to avoid registry collision
        @circuit_breaker(
            name="cov_excluded",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )
        def func_raises_value():
            raise ValueError("excluded")

        # ValueError should not count as a failure → circuit stays closed
        for _ in range(5):
            with pytest.raises(ValueError):
                func_raises_value()

        cb = get_circuit_breaker("cov_excluded")
        assert cb is not None
        assert cb.is_closed

    def test_decorator_reuses_existing_breaker_for_same_name(self):
        """Re-decorating with the same name returns the cached breaker (branch 222->231)."""

        @circuit_breaker(name="reused_name", failure_threshold=99)
        def f1():
            return "f1"

        cb_first = get_circuit_breaker("reused_name")

        # Decorating a second function with the SAME name reuses the breaker
        @circuit_breaker(name="reused_name", failure_threshold=1)  # different threshold
        def f2():
            return "f2"

        cb_second = get_circuit_breaker("reused_name")

        # Same instance — registry was hit, not re-created
        assert cb_first is cb_second
        # Original threshold preserved (cached breaker wasn't reconfigured)
        assert cb_first.failure_threshold == 99

    @pytest.mark.asyncio
    async def test_async_circuit_open_uses_async_fallback(self):
        """Async wrapper with circuit OPEN awaits an async fallback (lines 237-241)."""
        async_fallback_called = []

        async def async_fallback(*args, **kwargs):
            async_fallback_called.append(True)
            return "async-fallback"

        @circuit_breaker(
            name="async_fb_circuit",
            failure_threshold=1,
            reset_timeout=999.0,
            fallback=async_fallback,
        )
        async def flaky():
            raise RuntimeError("boom")

        # Trip the circuit
        with pytest.raises(RuntimeError):
            await flaky()

        cb = get_circuit_breaker("async_fb_circuit")
        assert cb is not None and cb.is_open

        # Now circuit is OPEN — fallback should fire
        result = await flaky()
        assert result == "async-fallback"
        assert async_fallback_called

    @pytest.mark.asyncio
    async def test_async_circuit_open_uses_sync_fallback(self):
        """Async wrapper with a sync fallback calls it directly (line 242)."""

        def sync_fallback(*args, **kwargs):
            return "sync-fallback"

        @circuit_breaker(
            name="async_sync_fb_circuit",
            failure_threshold=1,
            reset_timeout=999.0,
            fallback=sync_fallback,
        )
        async def flaky():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await flaky()

        cb = get_circuit_breaker("async_sync_fb_circuit")
        assert cb is not None and cb.is_open

        result = await flaky()
        assert result == "sync-fallback"

    @pytest.mark.asyncio
    async def test_async_circuit_open_no_fallback_raises(self):
        """Async wrapper with circuit OPEN and no fallback raises CircuitOpenError (line 243)."""

        @circuit_breaker(
            name="async_no_fb_circuit",
            failure_threshold=1,
            reset_timeout=999.0,
        )
        async def flaky():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await flaky()

        with pytest.raises(CircuitOpenError):
            await flaky()

    @pytest.mark.asyncio
    async def test_async_records_failure_and_reraises(self):
        """Async wrapper records failure and re-raises original exception (lines 249-251)."""

        @circuit_breaker(name="async_fail_record", failure_threshold=99)
        async def flaky():
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            await flaky()

        cb = get_circuit_breaker("async_fail_record")
        assert cb is not None
        assert cb._failure_count == 1
