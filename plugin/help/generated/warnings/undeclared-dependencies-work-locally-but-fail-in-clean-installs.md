---
confidence: Verified
name: undeclared-dependencies-work-locally-but-fail-in-clean-installs
source: CLAUDE.md Lessons Learned
summary: This template explains the risk of using undeclared dependencies that work
  in local development environments but fail in clean installs, and provides mitigation
  steps to ensure all imported packages are explicitly declared in the project configuration.
tags:
- testing
- imports
type: warning
---

# Warning: Undeclared Dependencies Work Locally But Fail in Clean Installs

## Condition

`jinja2` is imported by `test_generator/` and `scaffolding/` but is not listed as a core dependency in `pyproject.toml`.

## Risk

Undeclared dependencies may be available in local environments due to transitive installation by other packages. However, they will be absent in clean installs, causing import errors and broken builds that are difficult to reproduce and diagnose.

## Mitigation

1. Before importing any library, verify it is explicitly declared in `pyproject.toml`. Do not rely on transitive availability — a package present in your local environment may not be installed in CI or fresh developer setups.
2. Add `jinja2` to the `[project] dependencies` list in `pyproject.toml` if it is a direct runtime requirement, or to the appropriate optional/dev dependency group if it is only used during development or testing.
3. Periodically audit imports across the codebase with a tool such as `deptry` or `pipdeptree` to catch undeclared dependencies before they reach production.

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned).

## Related Topics

- [Diagnostic: Undeclared Dependencies Work Locally But Fail in Clean Installs](#)
