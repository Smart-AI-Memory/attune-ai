---
type: warning
name: combine-two-unreleased-changelog-drafts-into-one-version-when
confidence: Verified
tags: [git, packaging]
source: .claude/CLAUDE.md
---

# Warning: Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI

## Condition

attune-help had both 0.7.0 and 0.8.0 marked "— Unreleased" in CHANGELOG, but only 0.7.0 was actually on PyPI; 0.8.0 was a draft that had accumulated dev-branch changes

## Risk

Ignoring this guidance may cause: Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI

## Mitigation

1. Avoids the "which version got what" confusion that two adjacent unreleased sections create

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI
