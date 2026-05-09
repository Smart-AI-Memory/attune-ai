---
type: error
name: local-telemetry-trackers-need-an-autouse-conftest-fixture
confidence: Verified
tags: [testing, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Local-telemetry trackers need an autouse
  conftest fixture disabling them, not just a
  `tmp_path` default

## Signature

Local-telemetry trackers need an autouse
  conftest fixture disabling them, not just a
  `tmp_path` default

## Root Cause

a new `HelpTracker` class with the default path `~/.attune/telemetry/` got exercised through its real consumer (MCP handler `_handle_help_lookup`) during routine tests and polluted the user's actual JSONL with 11 test-fixture events. `tmp_path` only helps when the test constructs the tracker directly; tests that reach the tracker via production code paths bypass the fixture. Fix pattern: module-level opt-out env var (e.g. `ATTUNE_HELP_TELEMETRY=0`) plus an `autouse=True, scope="function"` fixture in the top-level `conftest.py` that sets it. Tracker-specific tests then re-enable via `monkeypatch.delenv` in their own module. Build any new `~/.attune/...` writer this way from commit one.

## Resolution

1. a new `HelpTracker` class with the default path `~/.attune/telemetry/` got exercised through its real consumer (MCP handler `_handle_help_lookup`) during routine tests and polluted the user's actual JSONL with 11 test-fixture events

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Local-telemetry trackers need an autouse
  conftest fixture disabling them, not just a
  `tmp_path` default
- Task: Update test mocks and assertions
