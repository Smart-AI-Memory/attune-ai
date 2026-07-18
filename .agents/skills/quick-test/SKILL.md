---
name: quick-test
description: Run tests on recently changed files
---
# quick-test

Fast feedback loop — run tests related to recently
changed files only.

## Context (pre-computed)

```bash
git diff --name-only HEAD 2>/dev/null
git diff --name-only --cached 2>/dev/null
```

## Instructions

1. Look at the changed files from the context above
2. For each changed `.py` file in `src/`, find the
   corresponding test file:
   - `src/attune/foo/bar.py` → `tests/unit/foo/test_bar.py`
   - `src/attune/foo.py` → `tests/unit/test_foo.py`
3. Run only those test files:

```bash
uv run pytest <test_files> -x -q --tb=short
```

4. If no matching test files exist, say so and offer
   to generate them with `/testing gen`
5. Report pass/fail summary
