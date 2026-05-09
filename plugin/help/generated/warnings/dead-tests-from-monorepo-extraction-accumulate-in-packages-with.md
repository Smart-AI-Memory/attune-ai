---
type: warning
name: dead-tests-from-monorepo-extraction-accumulate-in-packages-with
confidence: Verified
tags: [ci, testing, security, git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Dead tests from monorepo extraction accumulate
  in packages with no CI

## Condition

attune-help shipped `test_plugin_config.py` (15 tests) and parts of `test_plugin_references.py` from attune-ai's monorepo split

## Risk

Local test runs passed anyway because `_all_skill_bodies()` globbed an empty directory — the parametrized tests just silently produced zero cases

## Mitigation

1. attune-help shipped `test_plugin_config.py` (15 tests) and parts of `test_plugin_references.py` from attune-ai's monorepo split

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Dead tests from monorepo extraction accumulate
  in packages with no CI
