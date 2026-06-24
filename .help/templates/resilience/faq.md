---
type: faq
name: resilience-faq
feature: resilience
depth: faq
status: manual
---

# Resilience FAQ

## Which resilience pattern should I use?

`retry` for transient failures that usually succeed on a re-try;
`circuit_breaker` when a dependency is down and retrying just piles on;
`timeout` for calls that may hang; `fallback` when an alternate result
is acceptable; `HealthCheck` to aggregate component status. All are
imported from `attune.resilience`.

## Is the fallback API synchronous or asynchronous?

The `@fallback` decorator runs synchronously on a sync function.
`with_fallback(primary, fallbacks)` returns an **async** wrapper you must
await (e.g. `asyncio.run(...)`). `with_timeout(coro, seconds)` is also
async. The `@retry`, `@circuit_breaker`, and `@timeout` decorators work
on plain sync functions.

## How do I reset a tripped circuit breaker?

`get_circuit_breaker(name).reset()`, or wait `reset_timeout` for it to
probe in `HALF_OPEN`. A breaker trips `OPEN` after `failure_threshold`
consecutive failures and raises `CircuitOpenError` while open. Inspect
it with `get_circuit_breaker(name).get_stats()` (keys: `name`, `state`,
`failure_count`, `success_count`, `time_until_reset`).

## How do I stop retrying on non-transient errors?

Pass `retryable_exceptions=(SomeError, ...)` to `@retry` so only those
exceptions retry. Left at the default (`None`), retry treats all
exceptions as retryable — including programming errors.

## How do I register a health check?

`register` is a **decorator**: apply `@hc.register("name")` over a check
function that returns a bool/dict, then call `run_all_sync()` (or the
async `run_all()`) to get a `SystemHealth`. It is not a
`register(name, fn)` two-argument call.

## Where is the source?

All resilience source lives under `src/attune/resilience/` — one module
per pattern (`retry`, `circuit_breaker`, `timeout`, `fallback`,
`health`).

**Tags:** `resilience`, `fault-tolerance`, `retry`, `circuit-breaker`,
`reliability`
