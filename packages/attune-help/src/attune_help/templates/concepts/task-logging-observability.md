---
type: concept
name: task-logging-observability
tags: [logging, observability, python, monitoring]
source: developer-guidance
---

# Concept: Logging and observability

## What

Logging is the practice of recording what your code does at
runtime so you can understand it later. Observability is the
broader discipline of making a system's internal state
visible from the outside. Good logging answers "what
happened and why?" without requiring you to reproduce the
problem.

## Why

A function that fails silently in production is worse than
one that fails loudly. Without logs, your only debugging
tool is "try to reproduce it locally" -- which works for
maybe 20% of production issues. The other 80% are
concurrency bugs, environment-specific failures, and data-
dependent edge cases that only show up under real traffic.

Logging is cheap to add and expensive to lack. The
developer who adds a log line spends seconds; the developer
who debugs without one spends hours.

## Structured logging vs printf debugging

| Approach | Output | Searchable? | Machine-readable? | When to use |
|---|---|---|---|---|
| `print()` | Unstructured text to stdout | No | No | Throwaway local debugging only |
| `logging.info("msg")` | Formatted text to handlers | Partially (grep) | No | Simple applications, scripts |
| `structlog.info("msg", user=uid)` | Key-value pairs (JSON) | Yes (field queries) | Yes | Production services, anything that needs filtering |

**Rule of thumb:** If the code will ever run outside your
terminal, use `logging` at minimum. If it handles requests
or runs as a service, use structured logging.

## Log levels and when to use each

| Level | When to use | Example | Audience |
|---|---|---|---|
| `DEBUG` | Detailed diagnostic info, only useful during development | `logger.debug("Cache lookup key=%s", key)` | Developers debugging locally |
| `INFO` | Normal operations worth recording | `logger.info("Workflow started", workflow=name)` | Operators monitoring health |
| `WARNING` | Something unexpected but recoverable | `logger.warning("Retry attempt %d", count)` | Operators and on-call |
| `ERROR` | Something failed and needs attention | `logger.error("Payment failed: %s", err)` | On-call, alerts |
| `CRITICAL` | System is unusable | `logger.critical("Database connection lost")` | On-call, pages |

**Common mistake:** Using `WARNING` for everything. If
everything is a warning, nothing is. Reserve `WARNING` for
situations where a human should investigate but the system
can continue.

## What to log vs what to metric

| Signal | Best for | Tool | Example |
|---|---|---|---|
| **Log** | Understanding individual events, debugging specific requests | logging / structlog | "User X uploaded file Y, took 3.2s" |
| **Metric** | Tracking aggregates over time, alerting on thresholds | prometheus, statsd | "Upload count: 1,423/hour, p99 latency: 2.1s" |
| **Trace** | Following a request across multiple services | opentelemetry | "Request ABC touched auth, upload, and storage services" |

**Rule of thumb:** Logs tell you *what happened*. Metrics
tell you *how often* and *how fast*. Traces tell you
*where the time went* across service boundaries.

## The observability triangle

Logs, metrics, and traces are complementary -- not
competing. Each answers different questions:

- **Logs**: "Why did this specific request fail?"
- **Metrics**: "Is the error rate increasing?"
- **Traces**: "Which service is the bottleneck?"

For most Python projects, start with logging. Add metrics
when you need dashboards and alerts. Add traces when you
have multiple services that talk to each other.

## Key principles

- **Log at boundaries.** Entry and exit points of
  functions, API handlers, and external calls are the
  highest-value places to log.
- **Include context.** A log line without a request ID,
  user ID, or file path is nearly useless when you have
  thousands of them.
- **Use lazy formatting.** Write `logger.info("x=%s", x)`
  not `logger.info(f"x={x}")`. The f-string evaluates
  even when the log level is disabled.
- **Never log secrets.** Passwords, tokens, and PII must
  be scrubbed before they reach any log handler.
- **Set the right level.** `DEBUG` for development noise,
  `INFO` for normal operations, `WARNING` for recoverable
  issues, `ERROR` for failures.

## Want to learn more?

- "How do I add logging to my module?" -- see the **task**
  template for a step-by-step guide
- "Show me all the configuration options and patterns" --
  see the **reference** template for the full catalog
- "I just need logging working right now" -- see the
  **quickstart** for a 5-step setup
- Run `/code-quality` to detect logging anti-patterns
  like f-string formatting in log calls
- Run `/security` to find PII or secrets that might be
  leaking into log output

## Related Topics

- **Task**: Logging and observability -- step-by-step
  guide for setting up logging in a Python module
- **Reference**: Logging and observability -- full
  configuration catalog, structured logging patterns,
  and common mistakes
- **Quickstart**: Logging and observability -- 5-step
  guide to add logging to your module
