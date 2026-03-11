# Output Formatting Preferences

**Created:** 2026-01-26
**Source:** Session evaluation

---

## JSON to Table Translation

When given raw JSON or dict output (e.g., from workflows, audits, APIs), translate to readable markdown tables.

### Format

```markdown
## Summary
**Score:** X/100 | **Files:** Y | **Issues:** Z

### Issues by Priority
| Priority | Count |
|----------|-------|
| High     | X     |
| Medium   | Y     |
| Low      | Z     |

### Details
| File | Line | Issue |
|------|------|-------|
| [file.py:123](path#L123) | Pattern description |
```

### Key Elements

1. **Summary stats first** - Score, counts, totals at top
2. **Clickable file links** - Use `[file.py:123](path#L123)` format
3. **Group by priority** - High > Medium > Low
4. **Distinguish actionable vs false positives** - Separate "Fixed" from "Not Fixed - False Positive"

---

## Audit Result Reporting

When reporting on code analysis/audit results:

1. Lead with the score/health indicator
2. Show breakdown by severity
3. List actionable items first
4. Explain why false positives are false positives
5. End with clear summary of what was/wasn't fixed

### Example Structure

```markdown
## Audit Results

**Score:** 95/100 (Excellent)

### Fixed (X issues)
- [file.py:123](path#L123) - Description of fix

### Not Fixed - False Positives (Y issues)
| Pattern | Why Not a Problem |
|---------|-------------------|
| `dirs[:]` | Required for os.walk |
| `list(set)` | Intentional API design |
```
