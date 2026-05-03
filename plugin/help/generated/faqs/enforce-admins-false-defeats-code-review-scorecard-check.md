---
name: enforce-admins-false-defeats-code-review-scorecard-check
source: .claude/CLAUDE.md
summary: 'This template explains why setting `enforce_admins: false` in GitHub branch
  protection undermines the OpenSSF Scorecard Code-Review check by allowing administrators
  to bypass required approval rules, and demonstrates how to fix it by enabling `enforce_admins:
  true`.'
tags:
- ci
type: faq
---

# FAQ: Why Does `enforce_admins: false` Defeat the Code-Review Scorecard Check?

## Answer

When `enforce_admins` is set to `false`, administrators can bypass branch protection rules entirely — even if `required_approving_review_count` is set to `1` or higher. Because admins can merge pull requests without obtaining the required approvals, the OpenSSF Scorecard Code-Review check detects these unreviewed changesets and penalizes your score accordingly (typically resulting in 0/10).

To enforce code review requirements for all contributors, including administrators, ensure your branch protection configuration includes both settings:

```yaml
required_approving_review_count: 1
enforce_admins: true
```

Setting `enforce_admins: true` ensures that branch protection rules apply to repository administrators, so all pull requests — regardless of who authors them — must receive the required number of approvals before merging.

## Related Topics

- **Error**: `enforce_admins: false` defeats the Code-Review Scorecard check
- [Configuring branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [OpenSSF Scorecard: Code-Review check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#code-review)
