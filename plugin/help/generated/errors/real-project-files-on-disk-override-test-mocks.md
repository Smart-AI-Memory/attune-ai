---
type: error
name: real-project-files-on-disk-override-test-mocks
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Real project files on disk override test mocks

## Signature

Real project files on disk override test mocks

## Root Cause

Tests that mock `_get_raw_suggestions()` at the definition site still get real suggestions from `_get_spec_suggestions()` which reads actual `.claude/plans/` files.

## Resolution

1. mock at the *import site* in the consuming module (`attune.voice.formatter.get_next_steps` not `attune.voice.next_steps.get_next_steps`), or use `monkeypatch.chdir(tmp_path)` to isolate from the real filesystem

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Real project files on disk override test mocks
- Task: Update test mocks and assertions
