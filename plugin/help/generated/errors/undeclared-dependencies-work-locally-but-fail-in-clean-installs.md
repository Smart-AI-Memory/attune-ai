---
confidence: Verified
name: undeclared-dependencies-work-locally-but-fail-in-clean-installs
source: CLAUDE.md Lessons Learned
summary: This template explains how to identify and fix the issue of undeclared dependencies
  that function in local development environments but fail in clean installations,
  emphasizing the importance of explicitly declaring all directly imported packages
  in `pyproject.toml` rather than relying on transitive dependencies.
tags:
- testing
- imports
type: error
---

# Error: Undeclared Dependencies Work Locally but Fail in Clean Installs

## Signature

Undeclared dependencies appear to work in local development environments but cause import errors or failures in clean installs.

## Root Cause

`jinja2` was imported by `test_generator/` and `scaffolding/` but never declared in `pyproject.toml` core dependencies. It worked locally because other packages pulled it in transitively. Transitive availability is not guaranteed — it can disappear silently when dependency trees change, making this a fragile and difficult-to-debug failure mode.

## Resolution

Before importing any library, verify it is explicitly declared in `pyproject.toml`:

```bash
grep "jinja2" pyproject.toml
```

If the library is missing, add it to the appropriate dependency section:

```toml
[project]
dependencies = [
  "jinja2>=3.0",
]
```

> **Rule:** Never rely on transitive dependencies for packages your code imports directly. If you import it, declare it.

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

- Warning: Avoid undeclared dependencies that work locally but fail in clean installs
- Tip: Best practice for explicit dependency declaration
- Task: Update test mocks and assertions
