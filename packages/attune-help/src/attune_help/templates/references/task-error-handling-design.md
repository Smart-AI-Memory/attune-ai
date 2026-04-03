---
type: reference
name: task-error-handling-design
tags: [error-handling, python, patterns]
source: developer-guidance
---

# Reference: Error handling patterns

Complete catalog of Python error handling patterns with
code examples, anti-patterns, and tooling guidance.

## Pattern catalog

### Specific catch

Catch one or more named exceptions and handle them
directly.

```python
# Good -- specific, logged, recoverable
try:
    config = yaml.safe_load(path.read_text())
except FileNotFoundError:
    logger.info("No config file at %s, using defaults", path)
    config = DEFAULT_CONFIG
except yaml.YAMLError as e:
    logger.error("Malformed config at %s: %s", path, e)
    raise
```

**When to use:** You know exactly which exceptions can
occur and how to recover from each one.

**Anti-pattern:**

```python
# Bad -- catches too broadly, hides bugs
try:
    config = yaml.safe_load(path.read_text())
except Exception:
    config = {}
```

### Re-raise with chaining

Catch an exception, wrap it in a domain-specific type,
and re-raise with `from e` to preserve the original
traceback.

```python
try:
    conn = psycopg2.connect(dsn)
except psycopg2.OperationalError as e:
    raise DatabaseConnectionError(
        f"Cannot connect to {host}:{port}"
    ) from e
```

**When to use:** The caller should not depend on the
implementation's exception types (e.g., hiding a
database driver behind an abstraction).

**Anti-pattern:**

```python
# Bad -- loses the original traceback
try:
    conn = psycopg2.connect(dsn)
except psycopg2.OperationalError:
    raise DatabaseConnectionError("connection failed")
```

### Catch, log, re-raise

Log the error for observability, then re-raise so the
caller still sees the failure.

```python
try:
    result = external_api.call(payload)
except TimeoutError as e:
    logger.exception("API call timed out: %s", e)
    raise
```

**When to use:** You need an audit trail but cannot
recover locally.

**Anti-pattern:**

```python
# Bad -- logs but swallows the error
try:
    result = external_api.call(payload)
except TimeoutError as e:
    logger.error("API timed out: %s", e)
    return None  # caller never knows it failed
```

### Broad catch with justification

Catch `Exception` when the operation is genuinely
optional and failure should not crash the application.

```python
try:
    import optional_analytics
    optional_analytics.track(event)
except Exception:  # noqa: BLE001
    # INTENTIONAL: Analytics is optional. The main
    # workflow must not fail because tracking is down.
    logger.warning("Analytics tracking failed")
```

**When to use:**

| Scenario | Example |
|---|---|
| Optional features | Plugin loading, telemetry, analytics |
| Cleanup / teardown | `__del__`, `__exit__`, `close()` |
| Version detection | `importlib.metadata.version()` fallback |
| Startup resilience | App must start even if one subsystem fails |

**Requirements:**

1. Add `# noqa: BLE001` to suppress ruff
2. Add `# INTENTIONAL:` comment explaining why
3. Log with `logger.warning()` or `logger.exception()`
4. Document in the function's docstring

**Anti-pattern:**

```python
# Bad -- no justification, no logging
try:
    do_something()
except Exception:
    pass
```

### Cleanup with finally

Release resources regardless of whether the operation
succeeded.

```python
lock = threading.Lock()
lock.acquire()
try:
    update_shared_state()
except ValueError as e:
    logger.error("Invalid state update: %s", e)
    raise
finally:
    lock.release()
```

**When to use:** Files, connections, locks, or temporary
resources that must be released.

**Prefer context managers when available:**

```python
# Better -- automatic cleanup
with open(path) as f:
    data = json.load(f)
```

### Custom exceptions

Define domain exceptions to provide clear error messages
and enable callers to catch specific failure modes.

```python
class WorkflowError(Exception):
    """Base exception for workflow failures."""

class StageTimeoutError(WorkflowError):
    """A workflow stage exceeded its time limit."""

class ValidationError(WorkflowError):
    """Input validation failed before execution."""
```

**When to use:** Your module is a library or abstraction
layer consumed by other code. Custom exceptions let
callers distinguish your failures from stdlib errors.

**Anti-pattern:** Creating a custom exception for every
possible error. Only define custom types when callers
need to distinguish them.

## Anti-patterns summary

| Anti-pattern | Problem | Fix |
|---|---|---|
| Bare `except:` | Catches `KeyboardInterrupt`, `SystemExit` | Name the exception |
| `except Exception: pass` | Silently hides all errors | Log and justify, or catch specifically |
| `except Exception: return None` | Caller cannot distinguish failure from success | Raise or return a sentinel that the caller checks |
| Re-raise without `from e` | Original traceback lost | Add `from e` to chain exceptions |
| Logging without re-raising | Error is observed but caller continues blindly | Re-raise after logging, or handle and recover |
| `except Exception` without `# noqa: BLE001` | Fails ruff lint in CI | Add noqa comment and INTENTIONAL explanation |

## Ruff BLE001 rule

Ruff's BLE001 rule flags `except Exception:` and bare
`except:` clauses. It is enforced by the
`ruff-bare-exception-check` pre-commit hook.

**To suppress for a justified broad catch:**

```python
except Exception:  # noqa: BLE001
    # INTENTIONAL: <reason>
```

**Do not suppress without the INTENTIONAL comment.** The
noqa suppresses the linter; the comment explains the
decision to future readers.

## Logging patterns

| Method | When to use | Includes traceback? |
|---|---|---|
| `logger.exception("msg")` | Inside an `except` block when you want the full traceback | Yes |
| `logger.error("msg: %s", e)` | When you want the error message but not the full traceback | No |
| `logger.warning("msg")` | For expected or recoverable failures | No |
| `logger.info("msg")` | For informational fallbacks (cache miss, default used) | No |

**Tip:** Use `logger.exception()` instead of
`logger.error()` when debugging is more important than
log brevity. The traceback is invaluable for diagnosing
production issues.

## Want to learn more?

- "Why do these patterns matter?" -- see the **concept**
  template for design principles
- "Walk me through adding error handling to a module" --
  see the **task** template for a step-by-step guide
- Run `/code-quality` to scan your code for exception
  handling issues automatically
- Run `/security` to find error handling that might mask
  security vulnerabilities

## Related Topics

- **Concept**: Error handling design -- principles of
  catching vs propagating and the cost of swallowing
  errors
- **Task**: Error handling design -- step-by-step guide
  for designing error handling in a module
- **Quickstart**: Error handling design -- 5-step minimal
  guide for a single function
