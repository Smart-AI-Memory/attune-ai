---
type: quickstart
feature: code-quality
depth: quickstart
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f0f1e5876a5f83b83316fb690fa9aa652fd8f63b15844a89c384083fbac424f
status: generated
---

# Quickstart: code quality

Review code for style issues, likely bugs, and structural problems.

```python
from attune.workflows import CodeReviewWorkflow

workflow = CodeReviewWorkflow()
result = workflow.execute(path="src/auth/")
print(result)
```

This runs a comprehensive code review using four specialized subagents (security, quality, performance, and architecture reviewers) and returns a unified report with an overall health score.

## Expected output

```
Code Review Report

Summary:
Health Score: 78/100
The authentication module shows good overall structure with some quality concerns around error handling and a few minor security considerations.

Security:
✓ No critical vulnerabilities found
⚠ Consider using secrets module for token generation (src/auth/tokens.py:23)

Quality:
⚠ Broad exception handling masks errors (src/auth/login.py:45)
⚠ Mutable default argument (src/auth/session.py:67)

Performance:
✓ No significant bottlenecks identified

Architecture:
⚠ High coupling between auth modules (8 cross-imports)

Suggestions:
1. Replace generic exceptions with specific error types
2. Use immutable defaults in function signatures
3. Consider breaking auth module into smaller components
```

## Run a targeted review

```python
# Review just one file
result = workflow.execute(path="src/auth/login.py")

# Review with specific focus
result = workflow.execute(path="src/", focus="security")
```

**Next:** Run `attune help-docs use-code-quality` to learn about depth options (quick, standard, deep) and result interpretation.
