---
name: codeql-py-clear-text-logging-sensitive-data-traces-data-flow
source: .claude/CLAUDE.md
summary: This template explains why CodeQL's clear-text logging rule flags variables
  that contain sensitive data in their data flow history even when the actual logged
  values aren't secrets, and provides guidance on refactoring code to use dedicated
  audit loggers instead.
tags:
- security
type: faq
---

# FAQ: Why Does CodeQL Flag `py/clear-text-logging-sensitive-data` Even When No Secret Values Are Logged?

## Answer

CodeQL's `py/clear-text-logging-sensitive-data` rule uses data flow analysis, not literal pattern matching. This means it can flag a variable like `user_id` in a log message inside `security.py` even when only a count or metadata is logged — not the secret value itself — because the variable passed through a security-sensitive method at some point in its flow.

**How to fix:**

- Use format strings that omit user identifiers entirely (for example, log the operation result rather than the identity performing it).
- Move audit correlation to the dedicated audit logger, which is designed to handle sensitive context safely.

```python
# Instead of this:
logger.info("Processed %s secrets for user %s", count, user_id)

# Prefer this:
logger.info("Processed %s secrets", count)
audit_logger.record(user_id=user_id, action="secret_processed", count=count)
```

## Related Topics

- **Rule reference:** CodeQL query [`py/clear-text-logging-sensitive-data`](https://codeql.github.com/codeql-query-help/python/py-clear-text-logging-sensitive-data/)
- **Concept:** Data flow analysis vs. literal secret detection
- **See also:** Configuring the audit logger for sensitive context
