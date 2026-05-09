---
type: faq
name: prefer-github-actions-trusted-publishing-over-local-twine-uv
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What is the best practice for prefer GitHub Actions trusted publishing over local twine/uv publish?

## Answer

Local PyPI uploads can fail due to SSL cert mismatches (VPN/proxy intercepting `upload.pypi.org`) or 504 Gateway Timeouts on large wheels (~8MB). The repo has a trusted publishing workflow at `.github/workflows/publish-pypi.yml` that uses OIDC — no tokens needed.

```
upload.pypi.org
```

## Related Topics
- **Error**: Detailed error: Prefer GitHub Actions trusted publishing over local `twine`/`uv
  publish`
