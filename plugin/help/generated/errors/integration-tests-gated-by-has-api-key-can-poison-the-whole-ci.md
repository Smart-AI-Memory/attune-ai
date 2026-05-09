---
type: error
name: integration-tests-gated-by-has-api-key-can-poison-the-whole-ci
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Error: Integration tests gated by `HAS_API_KEY` can
  poison the whole CI matrix when Anthropic's
  network is transiently unreachable

## Signature

AllProvidersFailedError: All fallback options exhausted. Last error: Connection error.

## Root Cause

PR #169 showed 7-15 test failures spread across most matrix jobs with identical signature `AllProvidersFailedError: All fallback options exhausted. Last error: Connection error.` All hits were in `tests/models/test_sonnet_opus_fallback.py`, which guards with `needs_api_key = pytest.mark.skipif(not HAS_API_KEY, ...)` and makes real API calls when the key is set. When the CI runner's network to `api.anthropic.com` flakes, every platform that has the key configured fails identically — making it look like a code regression. Diagnosis signal: the same test IDs fail across all OS/Python combinations with the *same* error string, and no unit tests fail. Proper fix: mock the executor at the HTTP boundary, or add `@pytest.mark.integration` and exclude from the default `-m "not integration"` selector in `tests.yml`. Short-circuit rule: if CI "failures" all share the exact error string and live only in files with a network-gated skip, treat as infrastructure flake, not code regression.

## Resolution

1. PR #169 showed 7-15 test failures spread across most matrix jobs with identical signature `AllProvidersFailedError: All fallback options exhausted. Last error: Connection error.` All hits were in `tests/models/test_sonnet_opus_fallback.py`, which guards with `needs_api_key = pytest.mark.skipif(not HAS_API_KEY, ...)` and makes real API calls when the key is set

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
