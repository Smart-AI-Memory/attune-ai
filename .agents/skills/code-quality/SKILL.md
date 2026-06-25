---
name: code-quality
description: "Code review to find quality issues, style violations, and code smells. Triggers on: review, code review, quality, lint, code smell, analyze code."
---
# Code Quality

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="code-quality", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Code Quality** — Reviews your code for style issues, likely bugs, and structural problems in one pass.

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

## Help

After presenting results, call:

```
help_lookup(topic="code-quality", mode="workflow_help")
```

If templates are returned, offer: "I have tips about
code quality reviews — want to see them?"

## Follow-Up

After presenting results, offer:

- "Want me to fix these issues?"
- "Should I generate tests for the risky areas?"
- "Want to run a security-focused deep scan?"
