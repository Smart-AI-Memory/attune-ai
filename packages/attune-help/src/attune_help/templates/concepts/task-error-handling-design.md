---
type: concept
name: task-error-handling-design
tags: [error-handling, python, patterns]
source: developer-guidance
---

# Concept: Error handling design

## What

Error handling design is the practice of deciding, for
each failure point in your code, whether to catch an
exception, propagate it, or transform it. Good error
handling makes failures visible, debuggable, and
recoverable. Bad error handling hides bugs.

## Why

Swallowed exceptions are the most expensive kind of bug.
They produce no stack trace, no log entry, and no test
failure. The symptom shows up hours or days later as
corrupted state, silent data loss, or a user report that
"nothing happened." The cost of adding a proper handler
is minutes; the cost of debugging a swallowed error is
hours.

## The five strategies

| Strategy | When to use | Example | Anti-pattern |
|---|---|---|---|
| Catch and handle | You know how to recover | `except FileNotFoundError: return default` | Catching broadly and returning `None` |
| Catch and re-raise | You need to add context | `except ValueError as e: raise ConfigError(...) from e` | Re-raising without `from e` (loses chain) |
| Catch, log, re-raise | You need an audit trail | `except IOError as e: logger.error(...); raise` | Logging but not re-raising (swallows error) |
| Broad catch with justification | Failure is acceptable | `except Exception: # noqa: BLE001` with `# INTENTIONAL:` | Broad catch without a comment explaining why |
| Cleanup / finally | Resources must be released | `finally: conn.close()` | Putting cleanup in the `except` branch only |

## Key principles

- **Catch specific, propagate general.** If you do not
  know how to handle `Exception`, let it propagate. The
  caller might know.
- **Log before you handle.** Once you catch and return a
  fallback, the original error is gone unless you logged
  it first.
- **Chain with `from e`.** `raise NewError(...) from e`
  preserves the original traceback. Without it, the cause
  is lost.
- **Never use bare `except:`.** It catches
  `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit`,
  which should almost never be intercepted.
- **Exception hierarchies guide granularity.** Catch
  `ConnectionError` rather than `Exception` when you only
  want to handle network failures.

## The cost of swallowing errors

```python
# This silently eats every failure including bugs
try:
    deploy_to_production()
except Exception:
    pass  # "it works on my machine"
```

When `deploy_to_production()` raises `TypeError` due to a
code bug, this pattern hides it. The deployment appears to
succeed. The bug surfaces in production hours later.

## Want to learn more?

- "How do I design error handling for a new module?" --
  see the **task** template for a step-by-step guide
- "Show me all the patterns with code examples" -- see
  the **reference** template for a full pattern catalog
- Run `/code-quality` on your code to detect broad
  exception catches automatically
- Run `/security` to find error handling that masks
  security-relevant failures

## Related Topics

- **Task**: Error handling design -- step-by-step guide
  for adding error handling to a module
- **Reference**: Error handling design -- full pattern
  catalog with code examples
- **Quickstart**: Error handling design -- 5-step minimal
  guide for adding error handling to a function
