---
type: error
name: combine-two-unreleased-changelog-drafts-into-one-version-when
confidence: Verified
tags: [git, packaging]
source: .claude/CLAUDE.md
---

# Error: Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI

## Signature

Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI

## Root Cause

attune-help had both 0.7.0 and 0.8.0 marked "— Unreleased" in CHANGELOG, but only 0.7.0 was actually on PyPI; 0.8.0 was a draft that had accumulated dev-branch changes. Schema additions that warranted a 0.9.0 bump collided with the 0.8.0 draft. Cleanest resolution: rename the 0.8.0 section to 0.9.0 with today's date, append the new additions, note "supersedes 0.8.0 draft" in the changelog header, and skip tagging 0.8.0 entirely. Tags that were never pushed don't need deletion — they never existed. Avoids the "which version got what" confusion that two adjacent unreleased sections create.

## Resolution

1. attune-help had both 0.7.0 and 0.8.0 marked "— Unreleased" in CHANGELOG, but only 0.7.0 was actually on PyPI; 0.8.0 was a draft that had accumulated dev-branch changes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI
