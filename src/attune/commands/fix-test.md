---
name: fix-test
description: "Auto-diagnose and fix failing tests — identifies root causes and applies fixes."
argument-hint: "<test file or pattern>"
---

Auto-diagnose and fix failing tests for `$ARGUMENTS`.

If no test was specified, run `uv run pytest --tb=short -q`
first to find failures, then diagnose and fix each one.

Identify root causes (mock mismatches, assertion drift,
import errors), apply fixes, and re-run to verify — up to
3 attempts per test.
