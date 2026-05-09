---
type: error
name: pypi-environment-requires-manual-approval-in-github-actions
confidence: Verified
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# Error: `pypi` environment requires manual approval in GitHub Actions

## Signature

`pypi` environment requires manual approval in GitHub Actions

## Root Cause

The `publish-pypi.yml` workflow uses `environment: pypi` which has a required reviewer gate. After the build job passes, the publish job appears to be "running" but is actually waiting for approval at the Actions run page. Go to the run URL, click "Review deployments", and approve. Without approval the job hangs indefinitely (not a PyPI timeout).

## Resolution

1. The `publish-pypi.yml` workflow uses `environment: pypi` which has a required reviewer gate

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `pypi` environment requires manual approval in GitHub Actions
