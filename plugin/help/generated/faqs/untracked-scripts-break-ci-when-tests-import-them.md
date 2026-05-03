---
name: untracked-scripts-break-ci-when-tests-import-them
source: .claude/CLAUDE.md
summary: This template explains how to resolve `ModuleNotFoundError` in CI by ensuring
  all script files imported by tests are committed to version control, and provides
  methods to prevent the issue in the future.
tags:
- ci
- testing
- imports
- git
- claude-code
type: faq
---

# FAQ: Why Do I Get `ModuleNotFoundError` When Tests Import a Script?

## Answer

If a test file imports from a script that exists locally but has never been committed to version control, CI will fail with a `ModuleNotFoundError` on every platform — because the file simply isn't there.

**Example:** `test_sync_agents_skills.py` imported from `scripts/sync_agents_skills.py`, which existed locally but was never committed. This caused CI failures across all 12 platforms.

### How to Fix

Before pushing, verify that every file referenced by your tests is tracked by Git:

```bash
git status
```

Look for any **untracked files** (listed under `Untracked files:`) that your tests depend on. Stage and commit them before pushing:

```bash
git add scripts/sync_agents_skills.py
git commit -m "Track sync_agents_skills script required by tests"
git push
```

### How to Prevent This

- Run `git status` before every push to catch untracked files early.
- Consider adding a pre-push Git hook that warns when test imports reference untracked files.
- In CI, use `git status --porcelain` to assert a clean working tree as part of your pipeline checks.

---

## Related Topics

- [Understanding `ModuleNotFoundError` in Python](https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError)
- **Root cause:** Untracked scripts break CI when tests import them
- **See also:** Managing Git-tracked dependencies in test suites
