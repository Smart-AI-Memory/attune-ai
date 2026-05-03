---
name: enforce-admins-required-reviews-blocks-solo-dev-merges
source: .claude/CLAUDE.md
summary: 'This template explains why the combination of `enforce_admins: true` and
  `required_approving_review_count: 1` prevents solo developers and administrators
  from merging their own pull requests, blocking self-approval, admin bypasses, and
  automated approvals, along with workarounds to resolve this restriction.'
tags:
- git
type: faq
---

# FAQ: Why Does `enforce_admins` + Required Reviews Block Solo-Dev Merges?

## Answer

When both `enforce_admins: true` and `required_approving_review_count: 1` are set on a branch protection rule, the following restrictions apply even to repository owners and administrators:

- **Self-approval is blocked.** GitHub prevents a pull request author from approving their own PR, returning the error: `Review cannot approve your own pull request`.
- **`--admin` merges are blocked.** The `enforce_admins` flag removes the administrator bypass, so force-merging via `--admin` will also fail.
- **Auto-approve workflows are blocked.** Any workflow using `GITHUB_TOKEN` to approve a PR cannot approve on behalf of the PR's author, so automated approval steps will silently fail or error out.

In short, this combination enforces a strict two-person review policy with no exceptions — including for solo developers, repo owners, and automation tokens acting as the PR author.

### Example Configuration That Causes This Behavior

```yaml
enforce_admins: true
required_approving_review_count: 1
```

### Common Workarounds

- **Use a dedicated bot account** with repository access to act as the approving reviewer, since it is a different user identity than the PR author.
- **Disable `enforce_admins`** if you need administrators to retain merge bypass privileges.
- **Reduce `required_approving_review_count` to `0`** if approval gating is not required for your workflow.

---

## Related Topics

- Branch protection rules overview
- Error: `Review cannot approve your own pull request`
- Using `GITHUB_TOKEN` in workflows
- Configuring required status checks for pull requests
