---
type: error
name: dead-tests-from-monorepo-extraction-accumulate-in-packages-with
confidence: Verified
tags: [ci, testing, security, git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Dead tests from monorepo extraction accumulate
  in packages with no CI

## Signature

Dead tests from monorepo extraction accumulate
  in packages with no CI

## Root Cause

attune-help shipped `test_plugin_config.py` (15 tests) and parts of `test_plugin_references.py` from attune-ai's monorepo split. They validated a `plugin/` directory layout that exists in attune-ai but was never created in attune-help. Local test runs passed anyway because `_all_skill_bodies()` globbed an empty directory — the parametrized tests just silently produced zero cases. Enabling CI was the accountability mechanism that surfaced 15 errors + 4 failures at once. Pattern: when extracting a package, grep the new repo's `tests/` for any path reference that doesn't exist in the new layout and either create the expected files or delete the test. And: the first green CI run on a newly-audited package is almost never a one-push event — budget for 2-3 fix commits.

## Resolution

1. attune-help shipped `test_plugin_config.py` (15 tests) and parts of `test_plugin_references.py` from attune-ai's monorepo split

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Dead tests from monorepo extraction accumulate
  in packages with no CI
- Tip: Best practice: Dead tests from monorepo extraction accumulate
  in packages with no CI
- Task: Update test mocks and assertions
