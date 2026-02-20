---
name: security-audit
description: "Scan code for security vulnerabilities — eval/exec, path traversal, hardcoded secrets, injection risks"
triggers:
  - security
  - vulnerability
  - audit
  - scan
  - eval
  - secrets
  - injection
  - cve
---

## Socratic Scoping

Before running, ask:

1. **Scope**: "Which path should I scan?" Default to the
   project root if the user says "everything."
2. **Focus**: "Any specific concern — secrets, injection,
   dependencies, or a full sweep?"

## Execution

Call the `security_audit` MCP tool with the scoped path:

```
security_audit(path="<user-specified path>")
```

## Output Format

Present results as a table grouped by severity:

```markdown
## Security Audit Results

**Score:** X/100 | **Files Scanned:** Y | **Issues:** Z

### Critical
| File | Line | Issue | CWE |
|------|------|-------|-----|

### High
| File | Line | Issue | CWE |
|------|------|-------|-----|

### Medium / Low
| File | Line | Issue | CWE |
|------|------|-------|-----|
```

Use clickable file links: `[file.py:123](path#L123)`

## What It Checks

- `eval()` and `exec()` usage (CWE-95)
- Path traversal vulnerabilities (CWE-22)
- Hardcoded secrets and API keys
- SQL injection patterns (CWE-89)
- Command injection risks (CWE-78)
- Broad exception handling that masks errors
- Missing input validation

## Follow-Up

After presenting results, offer:

- "Want me to fix the critical issues?"
- "Should I generate security tests for the flagged
  files?"
- "Want a deeper scan of a specific directory?"
