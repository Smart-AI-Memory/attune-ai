---
description: Dependabot PRs Review & Merge Strategy: **Date:** 2026-01-26 **Status:** 9 open PRs pending review **Last Updated:** After immediate quality fixes (test env, Bl
---

# Dependabot PRs Review & Merge Strategy

**Date:** 2026-01-26
**Status:** 9 open PRs pending review
**Last Updated:** After immediate quality fixes (test env, Black formatting)

---

## Overview

9 Dependabot PRs are open for dependency updates. All have CI failures, but these are likely due to:
1. PRs not rebased with latest main (missing .env.test, Black formatting)
2. The same 7 test failures we saw in main (API key configuration)

**Recommendation:** Rebase and merge in batches after verifying CI passes.

---

## PR Summary

### Group 1: GitHub Actions Updates (Safe - Low Risk)

| PR | Title | Risk | Notes |
|----|-------|------|-------|
| #15 | actions/setup-python: 5 → 6 | LOW | Minor version bump |
| #14 | actions/upload-artifact: 4 → 6 | LOW | Major version, check breaking changes |
| #12 | actions/labeler: 5 → 6 | LOW | Minor version bump |

**Merge strategy:** Batch merge, monitor CI

**Breaking changes to check:**
- `upload-artifact@6`: [Check release notes](https://github.com/actions/upload-artifact/releases/tag/v6.0.0)

### Group 2: Dev Container Update (Safe - Dev Only)

| PR | Title | Risk | Notes |
|----|-------|------|-------|
| #13 | devcontainers/python: 3.11 → 3.13 | LOW | Dev environment only |

**Merge strategy:** Merge individually, test dev container

**Notes:** Updates Python version in dev container (doesn't affect production)

### Group 3: Python Dependencies (Review Required)

| PR | Title | Risk | Notes |
|----|-------|------|-------|
| #31 | Dev dependencies (5 updates) | MEDIUM | Batch update, review changes |
| #21 | structlog: <25 → <26 | LOW | Logging library |
| #20 | mkdocstrings: <1.0 → <2.0 | MEDIUM | Major version (docs only) |
| #19 | lsprotocol: <2024 → <2026 | LOW | LSP library |
| #17 | openai: <2.0 → <3.0 | HIGH | Major version, check breaking changes |

**Merge strategy:** Test individually, especially #17 and #20

**Breaking changes to check:**
- `openai@3.0`: [Check migration guide](https://github.com/openai/openai-python/releases)
- `mkdocstrings@2.0`: [Check changelog](https://github.com/mkdocstrings/mkdocstrings/releases)

---

## Merge Process

### Step 1: Rebase with Main

Each PR needs to be rebased with current main to pick up:
- `.env.test` (fixes test failures)
- Black formatting changes
- Any other recent fixes

```bash
# For each PR
gh pr checkout <number>
git fetch origin main
git rebase origin/main
git push --force-with-lease
```

### Step 2: Verify CI Passes

After rebase, wait for CI to complete. Expected results:
- ✅ Tests: 5274 passed, 7 failed (API key config - expected)
- ✅ Linting: Should pass with Black formatting
- ✅ Security: Should pass (no new vulnerabilities)

### Step 3: Merge Priority Order

**Phase 1 (This Week):**
1. PR #15 - setup-python (lowest risk)
2. PR #12 - labeler (lowest risk)
3. PR #21 - structlog (low risk, logging)
4. PR #19 - lsprotocol (low risk, LSP)

**Phase 2 (After Phase 1 Validated):**
5. PR #13 - devcontainers (dev only)
6. PR #31 - dev-dependencies (test in dev env first)

**Phase 3 (Requires Testing):**
7. PR #14 - upload-artifact v6 (check breaking changes)
8. PR #20 - mkdocstrings v2.0 (major version, docs)
9. PR #17 - openai v3.0 (major version, TEST THOROUGHLY)

---

## Breaking Changes to Investigate

### openai v3.0 (PR #17)

**Impact:** HIGH - LLM provider library

**Check:**
1. API changes in client initialization
2. Response format changes
3. Streaming changes
4. Error handling changes

**Test locations:**
- `tests/unit/models/test_empathy_executor_new.py`
- `src/attune/models/registry.py` (OpenAI models)
- Any workflows using OpenAI provider

**Manual test:**
```bash
# After merging PR #17
export OPENAI_API_KEY="your-key"
python -c "from attune.models import get_model; print(get_model('openai', 'cheap'))"
```

### mkdocstrings v2.0 (PR #20)

**Impact:** MEDIUM - Documentation generation

**Check:**
1. Configuration format changes
2. Python handler compatibility
3. Template changes

**Test:**
```bash
# After merging PR #20
mkdocs build
# Check docs render correctly
```

### actions/upload-artifact v6 (PR #14)

**Impact:** MEDIUM - CI artifact storage

**Check:**
1. Retention policy changes
2. API changes
3. Artifact merging behavior

**Verify:** CI still publishes artifacts correctly after merge

---

## Auto-Merge Configuration (Optional)

Once we're confident in Dependabot PRs, we can enable auto-merge for safe updates:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5

    # Auto-approve and merge minor/patch updates
    auto-merge: true
    auto-merge-strategy: "squash"

    # Only for specific safe packages
    labels:
      - "dependencies"
      - "automerge"
```

**Recommendation:** Enable auto-merge ONLY after Phase 1-3 complete successfully.

---

## CI Failure Analysis

Current CI failures on Dependabot PRs:

1. **Pre-commit checks** - Likely fixed by Black formatting on main
2. **Tests failing** - 7 failures related to API keys (expected, fixed by .env.test)
3. **Lint failures** - Fixed by Black formatting
4. **Pattern analysis** - May need rebase

**Expected after rebase:** Only the 7 API key test failures (acceptable)

---

## Manual Verification Checklist

Before merging each PR:

- [ ] PR rebased with latest main
- [ ] CI shows expected failures only (7 API key tests)
- [ ] No new ruff/black violations
- [ ] No new security issues
- [ ] Dependencies resolve without conflicts
- [ ] Breaking changes documented (if major version)

---

## Rollback Plan

If a merge causes issues:

```bash
# Revert the merge commit
git revert <merge-commit-sha>
git push origin main

# Or reset if not pushed to main yet
git reset --hard HEAD~1
```

---

## Timeline Recommendation

**This Week:**
- Day 1: Rebase all PRs with current main
- Day 2: Merge Phase 1 PRs (4 PRs - lowest risk)
- Day 3: Monitor production, merge Phase 2 if stable

**Next Week:**
- Test openai v3.0 and mkdocstrings v2.0 locally
- Merge Phase 3 PRs after validation

---

## Commands Reference

```bash
# List all Dependabot PRs
gh pr list --author "app/dependabot"

# Rebase a PR
gh pr checkout <number>
git rebase origin/main
git push --force-with-lease

# Check CI status
gh pr checks <number>

# Merge with squash
gh pr merge <number> --squash --auto

# Close without merging
gh pr close <number> --comment "Superseded by newer version"
```

---

## Related Documentation

- Project dependency policy: `pyproject.toml`
- CI configuration: `.github/workflows/`
- Dependabot config: `.github/dependabot.yml`
- Security policy: `SECURITY.md`

---

**Status:** Ready for Phase 1 merge after rebase
**Next Action:** Rebase PRs #15, #12, #21, #19 with main
**Owner:** TBD
