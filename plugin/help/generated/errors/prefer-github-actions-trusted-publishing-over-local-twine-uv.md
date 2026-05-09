---
type: error
name: prefer-github-actions-trusted-publishing-over-local-twine-uv
confidence: Verified
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# Error: Prefer GitHub Actions trusted publishing over local `twine`/`uv
  publish`

## Signature

Prefer GitHub Actions trusted publishing over local `twine`/`uv
  publish`

## Root Cause

Local PyPI uploads can fail due to SSL cert mismatches (VPN/proxy intercepting `upload.pypi.org`) or 504 Gateway Timeouts on large wheels (~8MB). The repo has a trusted publishing workflow at `.github/workflows/publish-pypi.yml` that uses OIDC — no tokens needed. Trigger with `gh workflow run publish-pypi.yml --ref main`. This runs on GitHub's infrastructure, bypassing local network issues entirely.

## Resolution

1. Local PyPI uploads can fail due to SSL cert mismatches (VPN/proxy intercepting `upload.pypi.org`) or 504 Gateway Timeouts on large wheels (~8MB)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Prefer GitHub Actions trusted publishing over local `twine`/`uv
  publish`
