---
name: codeql-alerts-dismissible-in-bulk-via-gh-api
source: .claude/CLAUDE.md
summary: This template covers how to use GitHub CLI (`gh api`) to programmatically
  dismiss multiple CodeQL alerts in bulk by making PATCH requests with valid dismissal
  reasons and optional comments for audit trails.
tags:
- testing
type: faq
---

# FAQ: How Do I Dismiss CodeQL Alerts in Bulk Using `gh api`?

## Answer

You can dismiss multiple CodeQL alerts programmatically using the GitHub CLI (`gh api`) with a `PATCH` request. Each dismissal requires a valid reason and an optional comment for traceability.

**Valid dismissal reasons:**

- `false positive`
- `won't fix`
- `used in tests`

**Command syntax:**

```bash
gh api repos/OWNER/REPO/code-scanning/alerts/ID \
  -X PATCH \
  -f state=dismissed \
  -f dismissed_reason="false positive" \
  -f dismissed_comment="Explain why this alert is being dismissed"
```

**To dismiss alerts in bulk**, iterate over a list of alert IDs and run the command for each one. Replace `OWNER`, `REPO`, `ID`, and the `dismissed_reason` value as appropriate.

> **Note:** Always provide a meaningful `dismissed_comment` to keep an audit trail of why each alert was suppressed.

## Related Topics

- [Code scanning alerts API reference](https://docs.github.com/en/rest/code-scanning)
- [Managing code scanning alerts with the GitHub CLI](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts)
