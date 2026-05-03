---
name: deep-review-false-positives-verify-before-acting
source: .claude/CLAUDE.md
summary: This template covers how to identify, verify, and respond to inaccurate findings
  from deep review agents by manually validating reported issues against your actual
  codebase before taking corrective action.
tags:
- testing
type: faq
---

# FAQ: How Should I Handle Deep Review False Positives?

## Answer

Deep review agents can report inaccurate findings. For example, a quality pass might flag `summary_index.py` as having 0% test coverage and `test_runner_helpers.py` as missing docstrings — both of which can be incorrect. In the case above, `summary_index.py` had 25 tests located in `tests/memory/`, and all helper functions already had docstrings.

**Always verify agent findings against the actual codebase before taking action.**

Common false positives include:

- **Coverage reports** that miss tests located in non-standard or nested directories
- **Docstring checks** that fail to detect existing documentation due to formatting or parsing issues

### Steps to Verify Before Acting

1. Locate the files flagged by the agent.
2. Manually confirm the reported issue exists (for example, check test directories and inspect docstrings directly).
3. Only plan or apply fixes if the issue is confirmed.

**Example — checking test coverage manually:**

```bash
# Verify tests exist for a flagged module
find tests/ -name "*.py" | xargs grep -l "summary_index"
```

**Example — inspecting docstrings directly:**

```bash
# Check for docstrings in a flagged helper file
grep -n '"""' test_runner_helpers.py
```

## Key Takeaway

Agent-reported findings are a starting point, not a source of truth. Treat them as suggestions and validate each one before modifying your codebase.

## Related Topics

- [Understanding Deep Review Quality Passes](#)
- [Configuring Test Discovery Paths](#)
- [Docstring Linting and Formatting Standards](#)
