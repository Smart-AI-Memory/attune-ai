---
name: code-quality
description: "Code review and bug prediction to find quality issues, style violations, and likely bugs. Triggers on: review, quality, code review, analyze, lint, bugs, predict, code smell."
argument-hint: "<path or directory to review>"
---

# Code Quality

## Scoping

Before running, ask:

1. **Scope**: "Which files or directory should I review?"
2. **Depth**: "Quick scan, thorough, or deep review?"
   - Quick: code_review only
   - Thorough: code_review + bug_predict combined
   - Deep: deep_review (security + quality + test gaps)

## Execution

**Quick scan:**

```
code_review(path="<user-specified path>")
```

**Thorough analysis:**

```
code_review(path="<user-specified path>")
bug_predict(path="<user-specified path>")
```

Merge and deduplicate results from both tools.

**Deep review** (multi-pass: security, quality, test gaps):

```
deep_review(path="<user-specified path>")
```

## Output Format

```markdown
## Code Quality Report

**Health:** X/100 | **Files:** Y | **Issues:** Z

### Issues by Category
| Category | Count | Severity |
|----------|-------|----------|
| Style | X | Low |
| Correctness | Y | High |
| Security | Z | Critical |
| Predicted Bugs | W | Medium |

### Details
| File | Line | Issue | Source |
|------|------|-------|--------|

### Predicted Bug Risks
| File | Pattern | Confidence |
|------|---------|------------|
```

## Follow-Up

After presenting results, offer:

- "Want me to fix these issues?"
- "Should I generate tests for the risky areas?"
- "Want to run a security-focused deep scan?"
