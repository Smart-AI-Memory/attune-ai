---
type: warning
name: undeclared-dependencies-work-locally-but-fail-in-clean-installs
confidence: Verified
tags: [testing, imports]
source: CLAUDE.md Lessons Learned
---

# Warning: Undeclared dependencies work locally but fail in clean
  installs

## Condition

`jinja2` was imported by `test_generator/` and `scaffolding/` but never listed in `pyproject.toml` core deps

## Risk

Ignoring this guidance may cause: Undeclared dependencies work locally but fail in clean
  installs

## Mitigation

1. Always grep `pyproject.toml` for any library before importing it — transitive availability is not guaranteed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Undeclared dependencies work locally but fail in clean
  installs
