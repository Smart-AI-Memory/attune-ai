---
type: task
name: task-logging-observability
tags: [logging, observability, python, monitoring]
source: developer-guidance
---

# Task: Set up logging for a Python module

Add structured, production-ready logging to a Python
module. This guide walks you through choosing a library,
configuring output format, adding context, and avoiding
common pitfalls.

## Prerequisites

- A Python module that needs logging
- Familiarity with `import logging`

## Steps

### 1. Choose stdlib logging vs structlog

Both are good choices. Pick based on your needs:

| Factor | stdlib `logging` | `structlog` |
|---|---|---|
| Dependencies | None (built-in) | `pip install structlog` |
| Output format | Text by default, JSON with config | JSON/key-value by default |
| Context binding | Manual (pass values each call) | Built-in (`bind()` carries context) |
| Best for | Scripts, CLI tools, simple apps | Services, APIs, anything that needs filtering |
| Learning curve | Low | Medium |

**Rule of thumb:** If you are writing a library or CLI
tool, use stdlib `logging`. If you are writing a service
that handles requests, use `structlog`.

### 2. Create a per-module logger

Every module should have its own logger. This lets you
control log levels per module instead of globally.

**With stdlib logging:**

```python
import logging

logger = logging.getLogger(__name__)
```

**With structlog:**

```python
import structlog

logger = structlog.get_logger(__name__)
```

Place the logger at module level, after all imports. Do
not create loggers inside functions -- it defeats per-
module configuration.

### 3. Configure the log format

**For development (human-readable):**

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
```

**For production (JSON, machine-readable):**

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

root = logging.getLogger()
root.addHandler(handler)
root.setLevel(logging.INFO)
```

**With structlog (handles both automatically):**

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),  # dev
        # structlog.processors.JSONRenderer(),  # prod
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
```

### 4. Add context to your log calls

A log line without context is almost useless when you
have thousands of them. Always include identifiers that
let you trace a specific operation.

**Correlation IDs (request tracking):**

```python
import uuid

def handle_request(request):
    request_id = str(uuid.uuid4())[:8]
    logger.info(
        "Request started",
        request_id=request_id,
        path=request.path,
    )
    # Pass request_id to downstream functions
    result = process(request, request_id=request_id)
    logger.info(
        "Request completed",
        request_id=request_id,
        status=result.status,
    )
```

**With structlog's context binding:**

```python
log = logger.bind(request_id=request_id, user=user_id)
log.info("Request started")  # includes request_id + user
log.info("Processing file", filename=name)  # adds filename
```

### 5. Set appropriate log levels

Use this decision tree for each log call:

- Is it only useful during development? -- `DEBUG`
- Is it a normal, expected operation? -- `INFO`
- Is it unexpected but the system recovers? -- `WARNING`
- Did something fail that needs fixing? -- `ERROR`
- Is the entire system unusable? -- `CRITICAL`

**Example of good level choices:**

```python
logger.debug("Cache key computed: %s", cache_key)
logger.info("Workflow %s started with %d files", name, count)
logger.warning("Config file missing, using defaults")
logger.error("Failed to write output: %s", err)
logger.critical("Database connection pool exhausted")
```

### 6. Use lazy formatting

```python
# Good -- string formatting is skipped if level is disabled
logger.info("Processing file %s (%d bytes)", name, size)

# Bad -- f-string always evaluates, even at DEBUG level
logger.debug(f"Processing file {name} ({size} bytes)")
```

This matters in hot loops. The f-string version pays the
formatting cost even when `DEBUG` is disabled.

### 7. Review with tooling

Run `/code-quality` on your module to detect:

- f-string formatting in log calls (performance issue)
- Missing logging in exception handlers
- Inconsistent logger names

Run `/security` to find:

- PII or secrets in log output (passwords, tokens, emails)
- Log injection risks from unsanitized user input

## Verification

After adding logging:

- [ ] Every module has `logger = logging.getLogger(__name__)`
- [ ] Log levels match the decision tree above
- [ ] All log calls use `%s` formatting, not f-strings
- [ ] Context (IDs, paths, counts) is included in log calls
- [ ] No secrets or PII appear in log output
- [ ] Exception handlers log before catching or re-raising

## Want to learn more?

- "Why does logging matter?" -- see the **concept**
  template for principles and the observability triangle
- "Show me all the configuration options" -- see the
  **reference** template for dictConfig, rotation,
  correlation IDs, and more
- "I just need it working now" -- see the **quickstart**
  for a 5-step setup

## Related Topics

- **Concept**: Logging and observability -- structured
  logging vs printf debugging, log levels, and the
  observability triangle
- **Reference**: Logging and observability -- full
  configuration catalog, structlog setup, PII scrubbing,
  and common mistakes
- **Quickstart**: Logging and observability -- 5-step
  guide to add logging to your module
