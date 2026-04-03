---
type: reference
name: task-logging-observability
tags: [logging, observability, python, monitoring]
source: developer-guidance
---

# Reference: Logging and observability patterns

Complete catalog of Python logging configuration, structured
logging patterns, and common mistakes.

## stdlib logging configuration

### basicConfig (quick setup)

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

Good for scripts and CLI tools. Call once at the entry
point, before any logger is used.

### dictConfig (production setup)

```python
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
        "json": {
            "()": "your_app.logging.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "app.log",
            "maxBytes": 10_485_760,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
            "level": "INFO",
        },
    },
    "loggers": {
        "your_app": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
        },
        "third_party_lib": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

**When to use:** Any application with multiple modules,
log rotation needs, or different handlers for different
components.

### fileConfig

```python
import logging.config

logging.config.fileConfig("logging.ini")
```

Less flexible than dictConfig. Prefer dictConfig for new
projects.

## structlog setup

### Development configuration

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Production configuration (JSON output)

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Context binding

```python
logger = structlog.get_logger()

# Bind context that persists across calls
log = logger.bind(request_id="abc-123", user="alice")
log.info("started")   # includes request_id and user
log.info("step two")  # still includes request_id and user

# Add more context without losing existing bindings
log2 = log.bind(step="validation")
log2.info("validating input")
```

## All log levels with guidance

| Level | Numeric | When to use | Example | Production visibility |
|---|---|---|---|---|
| `DEBUG` | 10 | Internal state, variable values, control flow | `logger.debug("Parsed %d items from %s", count, path)` | Off by default |
| `INFO` | 20 | Normal operations: started, completed, loaded | `logger.info("Workflow completed in %.1fs", duration)` | On |
| `WARNING` | 30 | Unexpected but recoverable: retries, fallbacks, deprecations | `logger.warning("Rate limit hit, retrying in %ds", delay)` | On, may alert |
| `ERROR` | 40 | Failures requiring attention: exceptions, data loss | `logger.error("Failed to save: %s", err)` | On, alerts |
| `CRITICAL` | 50 | System-level failures: cannot start, cannot connect | `logger.critical("Cannot reach database")` | On, pages |

## Structured logging patterns

### Correlation IDs

Assign a unique ID at the entry point and pass it
through all downstream calls.

```python
import uuid

def handle_request(request):
    correlation_id = str(uuid.uuid4())[:8]

    # stdlib: pass manually
    logger.info("Request %s: started", correlation_id)

    # structlog: bind once
    log = logger.bind(correlation_id=correlation_id)
    log.info("Request started")
```

### Request context with structlog contextvars

```python
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

def middleware(request, call_next):
    clear_contextvars()
    bind_contextvars(
        request_id=request.headers.get("x-request-id", "unknown"),
        method=request.method,
        path=request.path,
    )
    return call_next(request)
```

All log calls in downstream code automatically include
the bound context variables.

### Timing operations

```python
import time

start = time.perf_counter()
result = expensive_operation()
duration = time.perf_counter() - start

logger.info(
    "Operation completed",
    duration_ms=round(duration * 1000, 1),
    result_count=len(result),
)
```

## PII scrubbing

Never log passwords, tokens, API keys, email addresses,
or other personally identifiable information.

**Pattern: scrub before logging**

```python
def scrub_pii(data: dict) -> dict:
    """Remove PII fields before logging."""
    sensitive_keys = {"password", "token", "secret", "email", "ssn"}
    return {
        k: "***REDACTED***" if k.lower() in sensitive_keys else v
        for k, v in data.items()
    }

logger.info("User data: %s", scrub_pii(user_data))
```

**Pattern: structlog processor**

```python
def scrub_sensitive_keys(logger, method_name, event_dict):
    """structlog processor to redact sensitive fields."""
    sensitive = {"password", "token", "secret", "email"}
    for key in sensitive:
        if key in event_dict:
            event_dict[key] = "***REDACTED***"
    return event_dict

structlog.configure(
    processors=[
        scrub_sensitive_keys,
        # ... other processors
    ],
)
```

Run `/security` to scan your codebase for PII that
might be leaking into log output.

## Log rotation

Prevent log files from consuming all disk space.

```python
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# Rotate by size (10 MB, keep 5 backups)
handler = RotatingFileHandler(
    "app.log",
    maxBytes=10_485_760,
    backupCount=5,
)

# Rotate by time (daily, keep 30 days)
handler = TimedRotatingFileHandler(
    "app.log",
    when="midnight",
    backupCount=30,
)
```

## Common mistakes

| Mistake | Why it is a problem | Fix |
|---|---|---|
| `logger.info(f"x={x}")` | f-string evaluates even when level is disabled; wastes CPU in hot paths | `logger.info("x=%s", x)` |
| `logger.debug(...)` inside a tight loop | Generates thousands of log lines, fills disk, slows execution | Move outside loop, or guard with `if logger.isEnabledFor(logging.DEBUG):` |
| Bare `except:` with no logging | Error is silently swallowed; impossible to debug | Log the exception, then handle or re-raise |
| `logging.getLogger()` without `__name__` | All modules share the root logger; cannot filter per module | `logging.getLogger(__name__)` |
| Logging secrets or tokens | Security breach if logs are stored or shipped to a log aggregator | Use a PII scrubbing processor or redact before logging |
| `print()` in production code | No levels, no handlers, no filtering, no rotation | Replace with `logger.info(...)` |
| Creating loggers inside functions | A new logger object is created on every call; defeats caching and per-module config | Create at module level |
| Using `logger.error()` when `logger.exception()` is needed | Loses the traceback; makes debugging much harder | Use `logger.exception()` inside `except` blocks when you want the traceback |
| Catching exceptions without logging | Failure is invisible; no evidence it happened | Always log before handling or re-raising |

## Format string reference

| Attribute | Format | Output example |
|---|---|---|
| Logger name | `%(name)s` | `my_app.utils` |
| Log level | `%(levelname)s` | `INFO` |
| Timestamp | `%(asctime)s` | `2026-04-02 14:30:00` |
| Message | `%(message)s` | `Workflow started` |
| Module | `%(module)s` | `utils` |
| Function | `%(funcName)s` | `process_file` |
| Line number | `%(lineno)d` | `42` |
| Process ID | `%(process)d` | `12345` |
| Thread name | `%(threadName)s` | `MainThread` |

## Want to learn more?

- "Why does logging matter?" -- see the **concept**
  template for principles and the observability triangle
- "Walk me through adding logging to a module" -- see
  the **task** template for a step-by-step guide
- "I just need it working now" -- see the **quickstart**
  for a 5-step setup
- Run `/code-quality` to scan for logging anti-patterns
  like f-string formatting and missing exception logging
- Run `/security` to find PII or secrets leaking into
  log output

## Related Topics

- **Concept**: Logging and observability -- structured
  logging vs printf debugging, log levels, and the
  observability triangle
- **Task**: Logging and observability -- step-by-step
  guide for setting up logging in a Python module
- **Quickstart**: Logging and observability -- 5-step
  guide to add logging to your module
