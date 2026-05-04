---
type: task
feature: resilience
depth: task
generated_at: 2026-05-04T02:42:08.720688+00:00
source_hash: ac7fa86c6fc160b49ba191ab5eb87d2a363ce5215faf5399776e3d9bd9112df7
status: generated
---

# Work with resilience

Use resilience patterns when you need to protect your application from failures with circuit breakers, retries, timeouts, fallbacks, or health monitoring.

## Prerequisites

- Access to the project source code
- Python environment with the attune package installed
- Understanding of fault tolerance concepts (circuit breakers, retries, fallbacks)

## Add circuit breaker protection

1. **Import the circuit breaker decorator:**
   ```python
   from attune.resilience import circuit_breaker
   ```

2. **Wrap your function with the decorator:**
   ```python
   @circuit_breaker(name="api_call", failure_threshold=3, reset_timeout=30.0)
   def call_external_api():
       # Your external API call here
       response = requests.get("https://api.example.com/data")
       return response.json()
   ```

3. **Handle circuit open exceptions:**
   ```python
   from attune.resilience import CircuitOpenError

   try:
       result = call_external_api()
   except CircuitOpenError as e:
       print(f"Circuit breaker is open, trying again in {e.reset_time} seconds")
   ```

## Implement retry logic

1. **Add the retry decorator to functions that might fail transiently:**
   ```python
   from attune.resilience import retry

   @retry(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)
   def unstable_operation():
       # Operation that might fail due to network issues
       return requests.get("https://unreliable-service.com/data")
   ```

2. **Configure which exceptions trigger retries:**
   ```python
   @retry(
       max_attempts=5,
       retryable_exceptions=(requests.ConnectionError, requests.Timeout)
   )
   def network_operation():
       return requests.get("https://service.com", timeout=10)
   ```

## Set up fallback behavior

1. **Use the fallback decorator for graceful degradation:**
   ```python
   from attune.resilience import fallback

   def get_from_cache():
       return {"data": "cached_value"}

   def get_default():
       return {"data": "default_value"}

   @fallback(get_from_cache, get_default, default={"data": "fallback"})
   def get_user_data():
       # Primary data source that might fail
       return requests.get("https://user-service.com/data").json()
   ```

2. **Chain multiple fallbacks programmatically:**
   ```python
   from attune.resilience import with_fallback

   robust_function = with_fallback(
       primary=get_from_database,
       fallbacks=[get_from_cache, get_from_file],
       default={"empty": True}
   )
   ```

## Monitor system health

1. **Register health checks for your components:**
   ```python
   from attune.resilience import get_health_check

   health = get_health_check()

   @health.register("database", timeout=5.0, critical=True)
   async def check_database():
       # Your database connectivity check
       await db.execute("SELECT 1")
       return "Database is healthy"
   ```

2. **Run health checks to get system status:**
   ```python
   system_health = await health.run_all()

   if system_health.status == HealthStatus.HEALTHY:
       print("All systems operational")
   else:
       print(f"System issues detected: {system_health.checks}")
   ```

## Add timeouts to prevent hanging

1. **Wrap functions that might run too long:**
   ```python
   from attune.resilience import timeout

   @timeout(seconds=30.0, error_message="Processing took too long")
   def long_running_task():
       # Task that should complete within 30 seconds
       process_large_dataset()
   ```

2. **Use timeout with async operations:**
   ```python
   from attune.resilience import with_timeout

   async def fetch_data():
       result = await with_timeout(
           slow_async_operation(),
           seconds=10.0,
           fallback_value={"timeout": True}
       )
       return result
   ```

## Verify your implementation

1. **Test circuit breaker behavior:**
   - Trigger failures to open the circuit
   - Verify the circuit opens after reaching the failure threshold
   - Confirm the circuit resets after the timeout period

2. **Validate retry patterns:**
   - Simulate transient failures to test retry logic
   - Check that non-retryable exceptions fail immediately
   - Verify backoff delays increase between attempts

3. **Check fallback execution:**
   - Force primary function failures to test fallback chain
   - Ensure each fallback runs in sequence when the previous fails
   - Confirm default values return when all fallbacks fail

4. **Monitor health check results:**
   - Run `health.run_all()` and inspect the returned `SystemHealth` object
   - Verify critical checks affect overall system status
   - Check that health check timeouts work correctly

Your resilience patterns are working when functions gracefully handle failures, recover automatically when possible, and provide meaningful feedback about system health.
