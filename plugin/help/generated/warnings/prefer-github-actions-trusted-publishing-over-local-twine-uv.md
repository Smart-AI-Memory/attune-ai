---
type: warning
name: prefer-github-actions-trusted-publishing-over-local-twine-uv
confidence: Verified
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# Warning: Prefer GitHub Actions trusted publishing over local `twine`/`uv
  publish`

## Condition

Local PyPI uploads can fail due to SSL cert mismatches (VPN/proxy intercepting `upload.pypi.org`) or 504 Gateway Timeouts on large wheels (~8MB)

## Risk

Local PyPI uploads can fail due to SSL cert mismatches (VPN/proxy intercepting `upload.pypi.org`) or 504 Gateway Timeouts on large wheels (~8MB)

## Mitigation

1. Local PyPI uploads can fail due to SSL cert mismatches (VPN/proxy intercepting `upload.pypi.org`) or 504 Gateway Timeouts on large wheels (~8MB)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Prefer GitHub Actions trusted publishing over local `twine`/`uv
  publish`
