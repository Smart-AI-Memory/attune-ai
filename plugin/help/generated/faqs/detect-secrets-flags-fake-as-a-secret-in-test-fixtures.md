---
type: faq
name: detect-secrets-flags-fake-as-a-secret-in-test-fixtures
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about detect-secrets flags "fake" as a secret in test fixtures?

## Answer

The `Secret Keyword` heuristic matches any string assigned to a key that looks like a credential variable, including the obvious placeholder `"fake"` in `patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"})`. Add `# pragma: allowlist secret` on the same line to silence it.

```
Secret Keyword
```

## Related Topics
- **Error**: Detailed error: `detect-secrets` flags `"fake"` as a secret in test
  fixtures
