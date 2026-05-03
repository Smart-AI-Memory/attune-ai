---
name: pr-test-workflows-may-not-auto-trigger-after-close-reopen-or
source: .claude/CLAUDE.md
summary: This template explains why GitHub Actions PR test workflows sometimes fail
  to auto-trigger after a PR is closed, reopened, or when a branch is reused, and
  provides a manual workaround using the GitHub CLI.
tags:
- testing
- git
type: faq
---

# FAQ: Why don't PR test workflows auto-trigger after close/reopen or branch reuse?

## Answer

When a PR branch is reused after a previous PR was merged, the `pull_request` trigger may not fire on subsequent pushes. This is a known GitHub Actions behavior that can silently skip CI runs without any visible error.

To reliably trigger the workflow manually, use:

```bash
gh workflow run tests.yml --ref <branch>
```

Replace `<branch>` with the name of your PR branch.

## Related Topics

- **Troubleshooting**: PR test workflows may not auto-trigger after close/reopen or branch reuse
