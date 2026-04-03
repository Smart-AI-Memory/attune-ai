---
type: quickstart
name: task-error-handling-design
tags: [error-handling, python, patterns]
source: developer-guidance
---

# Quickstart: Add error handling to a function

Five steps to go from no error handling to production-
ready exception management.

## 1. Identify what can fail

Look at every call in your function. File I/O, network
requests, parsing, and type conversions are the most
common failure points.

## 2. Catch specific exceptions

```python
try:
    data = json.loads(raw_input)
except json.JSONDecodeError as e:
    logger.error("Bad JSON input: %s", e)
    raise ValueError("Input must be valid JSON") from e
```

Never use bare `except:`. Always name the exception.

## 3. Log before you handle

```python
except FileNotFoundError as e:
    logger.warning("Config not found: %s", e)
    return default_config  # fallback is OK after logging
```

If you skip the log, the failure becomes invisible.

## 4. Chain with `from e`

```python
except KeyError as e:
    raise ConfigError(f"Missing key: {e}") from e
```

This preserves the original traceback in the chained
exception.

## 5. Clean up in `finally`

```python
resource = acquire()
try:
    use(resource)
finally:
    resource.release()
```

Or use a context manager: `with acquire() as resource:`

## Verify

Run `/code-quality` on your file to check for bare
`except:` clauses and unjustified broad catches.

## Want to learn more?

- "Walk me through the full process" -- see the **task**
  template for a complete module-level guide
- "Show me all the patterns" -- see the **reference**
  template for the full catalog with anti-patterns
- "Why does this matter?" -- see the **concept** template
  for design principles

## Related Topics

- **Concept**: Error handling design -- when to catch vs
  propagate, and the cost of swallowing errors
- **Task**: Error handling design -- designing error
  handling for a full module
- **Reference**: Error handling design -- all patterns
  with code examples and anti-patterns
