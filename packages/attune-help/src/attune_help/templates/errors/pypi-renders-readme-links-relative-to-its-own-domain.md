---
type: error
name: pypi-renders-readme-links-relative-to-its-own-domain
confidence: Verified
tags: [security, packaging, python]
source: .claude/CLAUDE.md
---

# Error: PyPI renders README links relative to its own domain

## Signature

PyPI renders README links relative to its own domain

## Root Cause

Relative links like `docs/ARCHITECTURE.md` become `https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md` which 404s. All links in README.md must use absolute GitHub URLs (`https://github.com/Smart-AI-Memory/attune-ai/blob/main/...`). This applies to LICENSE, SECURITY.md, CONTRIBUTING.md, and any docs/ path. Contributor-facing links (coding standards, contributing guide) are better removed from the PyPI README entirely — they add clutter and broken-link risk for users who will never contribute.

## Resolution

1. Relative links like `docs/ARCHITECTURE.md` become `https://pypi.org/project/attune-ai/docs/ARCHITECTURE.md` which 404s

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: PyPI renders README links relative to its own domain
- Tip: Best practice: PyPI renders README links relative to its own domain
