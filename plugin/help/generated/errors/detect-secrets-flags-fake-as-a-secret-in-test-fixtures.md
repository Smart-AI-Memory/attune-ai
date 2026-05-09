---
type: error
name: detect-secrets-flags-fake-as-a-secret-in-test-fixtures
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: `detect-secrets` flags `"fake"` as a secret in test
  fixtures

## Signature

`detect-secrets` flags `"fake"` as a secret in test
  fixtures

## Root Cause

The `Secret Keyword` heuristic matches any string assigned to a key that looks like a credential variable, including the obvious placeholder `"fake"` in `patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"})`. Add `# pragma: allowlist secret` on the same line to silence it. This is the same pattern as the existing `# pragma: allowlist secret` lessons but the trigger string is non-obvious — even a 4-char placeholder fires it.

## Resolution

1. Add `# pragma: allowlist secret` on the same line to silence it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
