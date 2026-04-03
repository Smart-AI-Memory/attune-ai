---
type: quickstart
name: task-logging-observability
tags: [logging, observability, python, monitoring]
source: developer-guidance
---

# Quickstart: Add logging to my module

Five steps to go from `print()` to production-ready
logging.

## 1. Create a module-level logger

```python
import logging

logger = logging.getLogger(__name__)
```

Place this after your imports, before any functions. The
`__name__` argument gives the logger your module's dotted
path (e.g., `myapp.utils`), so you can control its level
independently.

## 2. Configure output at the entry point

In your `main.py` or application entry point, add:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
```

Call this once, before any other code runs. Do not call
it inside library modules -- only at the top-level entry
point.

## 3. Add log calls at key points

```python
def process_file(path: str) -> dict:
    """Process a file and return results."""
    logger.info("Processing %s", path)

    try:
        data = load(path)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        raise

    logger.debug("Loaded %d records from %s", len(data), path)
    result = transform(data)
    logger.info("Completed %s: %d results", path, len(result))
    return result
```

Use `%s` formatting, not f-strings. The `%s` version
skips string formatting when the log level is disabled.

## 4. Include context in every log call

```python
logger.info(
    "Workflow started: name=%s files=%d",
    workflow_name,
    file_count,
)
```

Without context, a log line like `"Workflow started"` is
useless when you have hundreds of them. Always include
identifiers: names, counts, paths, IDs.

## 5. Verify no secrets in output

Check that you are not logging passwords, tokens, or PII:

```python
# Bad -- logs the actual token
logger.info("Authenticated with token=%s", token)

# Good -- logs only that authentication succeeded
logger.info("Authenticated as %s", username)
```

Run `/security` to scan your module for secrets that
might be leaking into log output.

## Verify

Run `/code-quality` on your file to check for:

- f-string formatting in log calls
- Missing logging in exception handlers
- `print()` statements that should be log calls

## Want to learn more?

- "Walk me through the full setup" -- see the **task**
  template for choosing a library, configuring format,
  and adding correlation IDs
- "Show me all the configuration options" -- see the
  **reference** template for dictConfig, structlog,
  rotation, and PII scrubbing
- "Why does this matter?" -- see the **concept** template
  for the observability triangle and log level guidance

## Related Topics

- **Concept**: Logging and observability -- structured
  logging vs printf debugging, log levels, and the
  observability triangle
- **Task**: Logging and observability -- complete setup
  guide for a Python module
- **Reference**: Logging and observability -- full
  configuration catalog, common mistakes, and patterns
