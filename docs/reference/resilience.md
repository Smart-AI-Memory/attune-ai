# Resilience

## Reference

| Symbol | Kind | Purpose |
|--------|------|---------|
| `retry(max_attempts=3, backoff_factor=2.0, initial_delay=1.0, max_delay=60.0, jitter=True, retryable_exceptions=None, on_retry=None)` | decorator | Retry with backoff. |
| `RetryConfig(...)` / `retry_with_backoff(func, *a, config=None)` | class / fn | Retry config + imperative runner. |
| `circuit_breaker(name=None, failure_threshold=5, reset_timeout=60.0, half_open_max_calls=3, ...)` | decorator | Circuit breaker. |
| `CircuitBreaker(name, ...)` / `get_circuit_breaker(name)` | class / fn | Breaker object + registry lookup. |
| `CircuitState` | enum | `CLOSED` / `OPEN` / `HALF_OPEN`. |
| `CircuitOpenError` | exception | Raised when the breaker is open. |
| `timeout(seconds, error_message=None, fallback=None)` | decorator | Bound a call. |
| `with_timeout(coro, seconds, fallback_value=None)` | async fn | Bound a coroutine. |
| `ResilienceTimeoutError` | exception | Raised on overrun. |
| `fallback(*fns, default=None, log_failures=True)` | decorator (sync) | Try alternates. |
| `with_fallback(primary, fallbacks, default=None)` | fn → **async** wrapper | Programmatic fallback chain. |
| `Fallback(name, functions, default_value=None)` | class | `add` / `execute`. |
| `HealthCheck(version="unknown")` | class | `register(name, timeout=10.0, critical=False)` **decorator**, `run_all` (async), `run_all_sync`. |
| `HealthStatus` / `SystemHealth` | enum / class | `HEALTHY`/`DEGRADED`/`UNHEALTHY`/`UNKNOWN`; aggregate result. |

<!-- attune-generated: source_hash=5cb46b75c64a21b6c79cd5a1c06a09a397f1048bd4e927af38e5c62d97a332d6 feature=resilience kind=reference generated_at=2026-06-24 -->
