---
type: faq
name: codeql-py-clear-text-logging-sensitive-data-traces-data-flow
tags: [security]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about codeQL py/clear-text-logging-sensitive-data traces data flow, not literal secrets?

## Answer

CodeQL flagged `user_id` in a log message inside `security.py` even though only the count of secrets was logged (not secret values). It traces any variable that flows through a security-sensitive method.

**How to fix:**
- use `%s` formatting without user identifiers, or move audit correlation to the dedicated audit logger which is designed for that purpose

```
 in a log message inside
```

## Related Topics
- **Error**: Detailed error: CodeQL `py/clear-text-logging-sensitive-data` traces data flow,
  not literal secrets
