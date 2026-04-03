---
type: task
name: task-error-handling-design
tags: [error-handling, python, patterns]
source: developer-guidance
---

# Task: Design error handling for a module

Add clear, debuggable error handling to a Python module.
This guide walks you through choosing exception
granularity, adding context, and documenting intentional
broad catches.

## Prerequisites

- A Python module with functions that can fail
- Familiarity with `try`/`except`/`finally`

## Steps

### 1. Map every failure point

Read through the module and list every operation that can
raise. Common sources:

| Operation | Likely exceptions |
|---|---|
| File I/O | `FileNotFoundError`, `PermissionError`, `OSError` |
| Network calls | `ConnectionError`, `TimeoutError`, `HTTPError` |
| JSON/YAML parsing | `json.JSONDecodeError`, `yaml.YAMLError` |
| Type conversions | `ValueError`, `TypeError` |
| Dict/list access | `KeyError`, `IndexError` |
| External libraries | Check the library's documented exceptions |

### 2. Choose the right granularity

For each failure point, decide which exception to catch.

**Rule of thumb:** Catch the most specific exception that
covers all the failure modes you want to handle.

```python
# Too broad -- catches bugs like TypeError
try:
    config = json.loads(raw_text)
except Exception:
    config = {}

# Right granularity -- catches only parse failures
try:
    config = json.loads(raw_text)
except json.JSONDecodeError as e:
    logger.warning("Invalid config JSON: %s", e)
    config = {}
```

### 3. Add context with `from e`

When re-raising as a different exception type, always
chain with `from e` so the original traceback is
preserved.

```python
try:
    value = int(user_input)
except ValueError as e:
    raise ConfigError(
        f"Expected integer for 'retries', got: "
        f"{user_input!r}"
    ) from e
```

Without `from e`, anyone debugging the `ConfigError` has
no idea what the original input was.

### 4. Log before handling

If you catch and recover (return a default, skip an
item), log the error first. Otherwise the failure is
invisible.

```python
try:
    data = load_from_cache(key)
except FileNotFoundError as e:
    logger.info("Cache miss for %s: %s", key, e)
    data = fetch_from_api(key)
```

Use `logger.exception()` instead of `logger.error()`
when you want the full traceback in the log.

### 5. Handle broad catches properly

Sometimes you genuinely need `except Exception`. This is
acceptable when:

- The operation is optional (plugins, optional features)
- You are in cleanup/teardown code
- You are detecting package versions with a fallback

When you do this, document it:

```python
try:
    optional_feature.init()
except Exception:  # noqa: BLE001
    # INTENTIONAL: Feature is optional. App must
    # start even if this fails.
    logger.warning("Optional feature init failed")
```

Both the `# INTENTIONAL:` comment and `# noqa: BLE001`
are required. The comment explains *why*; the noqa
suppresses the ruff linter rule.

### 6. Use `finally` for cleanup

Resources like files, connections, and locks must be
released regardless of success or failure.

```python
conn = acquire_connection()
try:
    result = conn.execute(query)
except DatabaseError as e:
    logger.error("Query failed: %s", e)
    raise
finally:
    conn.close()
```

Prefer context managers (`with` statements) when
available -- they handle `finally` automatically.

### 7. Review with tooling

Run `/code-quality` on your module to detect:

- Bare `except:` clauses (always a bug)
- Broad `except Exception:` without justification
- Missing logging in exception handlers

Run `/security` to find error handling that masks
security-relevant failures (e.g., catching path
validation errors silently).

## Verification

After adding error handling:

- [ ] Every `except` names a specific exception (or has
      `# INTENTIONAL:` + `# noqa: BLE001`)
- [ ] Every caught exception is logged before being
      handled or re-raised
- [ ] Re-raised exceptions use `from e` for chaining
- [ ] Cleanup code is in `finally` blocks or context
      managers
- [ ] No bare `except:` anywhere in the module

## Want to learn more?

- "Why does error handling design matter?" -- see the
  **concept** template for principles and trade-offs
- "Show me all the patterns in one place" -- see the
  **reference** template for the full catalog

## Related Topics

- **Concept**: Error handling design -- when to catch vs
  propagate, and the cost of swallowing errors
- **Reference**: Error handling design -- full pattern
  catalog with code examples and anti-patterns
- **Quickstart**: Error handling design -- 5-step minimal
  guide for a single function
