---
type: faq
name: github-actions-environment-deployment-approvals-can-be-self
tags: [ci, git, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about gitHub Actions environment deployment approvals can be self-approved via gh api when current_user_can_approve: true** — no need to visit the web UI for routine releases on repos you own. Sequence: `` RUN=<run-id> ENV_ID=$(gh api repos/OWNER/REPO/actions/runs/$RUN/pending_deployments \ --jq '.[0].environment.id') gh api repos/OWNER/REPO/actions/runs/$RUN/pending_deployments \ -X POST -F "environment_ids[]=$ENV_ID" -F state=approved \ -F comment="release notes here" ` Check current_user_can_approve first via the same pending_deployments endpoint. Useful for the pypi` environment gate on attune-rag / attune-help / attune-ai publishes when the CLI user is the repo owner. Supersedes the older "go to the Actions run page and click Review deployments" pattern for the common solo-owner case. - **PR scope after commits have already landed: expand the existing PR, don't split?

## Answer

when new commits are made on a branch with an open PR that covers a different-but-related decision, and the new work has already materialized externally (shipped release, new artifact), the correct move is to update the PR title/body to cover both and merge — not to rewind history and split. Splitting requires force-push (destructive per branch protection rules) for zero review benefit if the code is already published.

## Related Topics
- **Error**: Detailed error: GitHub Actions environment deployment approvals can
  be self-approved via `gh api` when
  `current_user_can_approve: true`** — no need to visit
  the web UI for routine releases on repos you own.
  Sequence:
  ```
  RUN=<run-id>
  ENV_ID=$(gh api repos/OWNER/REPO/actions/runs/$RUN/pending_deployments \
    --jq '.[0].environment.id')
  gh api repos/OWNER/REPO/actions/runs/$RUN/pending_deployments \
    -X POST -F "environment_ids[]=$ENV_ID" -F state=approved \
    -F comment="release notes here"
  ```
  Check `current_user_can_approve` first via the same
  pending_deployments endpoint. Useful for the `pypi`
  environment gate on attune-rag / attune-help /
  attune-ai publishes when the CLI user is the repo
  owner. Supersedes the older "go to the Actions run
  page and click Review deployments" pattern for the
  common solo-owner case.

- **PR scope after commits have already landed: expand
  the existing PR, don't split
