---
type: faq
name: integration-tests-gated-by-has-api-key-can-poison-the-whole-ci
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about integration tests gated by HAS_API_KEY can poison the whole CI matrix when Anthropic's network is transiently unreachable?

## Answer

PR #169 showed 7-15 test failures spread across most matrix jobs with identical signature `AllProvidersFailedError: All fallback options exhausted. Last error: Connection error.` All hits were in `tests/models/test_sonnet_opus_fallback.py`, which guards with `needs_api_key = pytest.mark.skipif(not HAS_API_KEY, ...)` and makes real API calls when the key is set. When the CI runner's network to `api.anthropic.com` flakes, every platform that has the key configured fails identically — making it look like a code regression.

```
 All hits were in
```

## Related Topics
- **Error**: Detailed error: Integration tests gated by `HAS_API_KEY` can
  poison the whole CI matrix when Anthropic's
  network is transiently unreachable
