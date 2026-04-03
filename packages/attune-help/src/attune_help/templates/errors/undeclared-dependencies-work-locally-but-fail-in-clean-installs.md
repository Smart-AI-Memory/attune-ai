---
type: error
name: undeclared-dependencies-work-locally-but-fail-in-clean-installs
confidence: Verified
tags: [testing, imports]
source: CLAUDE.md Lessons Learned
---

# Error: Undeclared dependencies work locally but fail in clean
  installs

## Signature

Undeclared dependencies work locally but fail in clean
  installs

## Root Cause

`jinja2` was imported by `test_generator/` and `scaffolding/` but never listed in `pyproject.toml` core deps. It worked because other packages pulled it in transitively. Always grep `pyproject.toml` for any library before importing it — transitive availability is not guaranteed.
<!-- attune-lessons-end -->

## Resolution

1. Always grep `pyproject.toml` for any library before importing it — transitive availability is not guaranteed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Undeclared dependencies work locally but fail in clean
  installs
- Tip: Best practice: Undeclared dependencies work locally but fail in clean
  installs
- Task: Update test mocks and assertions
