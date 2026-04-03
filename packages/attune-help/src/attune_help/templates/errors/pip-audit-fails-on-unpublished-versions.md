---
type: error
name: pip-audit-fails-on-unpublished-versions
confidence: Verified
tags: [ci, packaging]
source: .claude/CLAUDE.md
---

# Error: `pip-audit` fails on unpublished versions

## Signature

`pip-audit` fails on unpublished versions

## Root Cause

`pip-audit --strict` with a local editable install (`pip install -e .`) fails if the version in `pyproject.toml` doesn't exist on PyPI yet. The error is `Dependency not found on PyPI and could not be audited: attune-ai (5.0.0)`. This self-resolves after publishing. Not a blocking CI failure for version bump PRs.

## Resolution

1. `pip-audit --strict` with a local editable install (`pip install -e .`) fails if the version in `pyproject.toml` doesn't exist on PyPI yet

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
