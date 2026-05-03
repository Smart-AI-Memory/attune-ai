---
name: repo-merge-policy-may-restrict-merge-strategies
source: .claude/CLAUDE.md
summary: This template explains how to resolve GitHub CLI merge command failures caused
  by repository merge policy restrictions and instructs developers to use the allowed
  squash merge strategy instead.
tags:
- git
type: faq
---

# FAQ: Repository Merge Policy Restricts Merge Strategies

## Answer

When running `gh pr merge --merge`, you may encounter the following error:

> Merge method merge commits are not allowed.

This occurs because the repository is configured to allow only squash merges. Attempting to use a disallowed merge strategy will cause the command to fail.

## How to Fix

Use the `--squash` flag instead of `--merge` when merging pull requests in this repository:

```bash
gh pr merge --squash
```

If you are unsure which merge strategies the repository permits, check the repository's **Settings → General → Pull Requests** section to see which merge methods are enabled.

## Related Topics

- **Error:** `Detailed error: Repo merge policy may restrict merge strategies`
- [GitHub CLI: `gh pr merge` documentation](https://cli.github.com/manual/gh_pr_merge)
- Configuring allowed merge strategies in repository settings
