---
type: warning
name: detect-secrets-flags-fake-as-a-secret-in-test-fixtures
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: `detect-secrets` flags `"fake"` as a secret in test
  fixtures

## Condition

The `Secret Keyword` heuristic matches any string assigned to a key that looks like a credential variable, including the obvious placeholder `"fake"` in `patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"})`

## Risk

Ignoring this guidance may cause: `detect-secrets` flags `"fake"` as a secret in test
  fixtures

## Mitigation

1. Add `# pragma: allowlist secret` on the same line to silence it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `detect-secrets` flags `"fake"` as a secret in test
  fixtures
