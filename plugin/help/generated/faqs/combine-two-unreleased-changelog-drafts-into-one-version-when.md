---
type: faq
name: combine-two-unreleased-changelog-drafts-into-one-version-when
tags: [git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about combine two unreleased CHANGELOG drafts into one version when neither has shipped to PyPI?

## Answer

attune-help had both 0.7.0 and 0.8.0 marked "— Unreleased" in CHANGELOG, but only 0.7.0 was actually on PyPI; 0.8.0 was a draft that had accumulated dev-branch changes. Schema additions that warranted a 0.9.0 bump collided with the 0.8.0 draft.

**How to fix:**
- Avoids the "which version got what" confusion that two adjacent unreleased sections create

## Related Topics
- **Error**: Detailed error: Combine two unreleased CHANGELOG drafts into one
  version when neither has shipped to PyPI
