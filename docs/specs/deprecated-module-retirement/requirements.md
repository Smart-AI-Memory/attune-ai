# Spec: Deprecated Module Retirement

**Status**: draft
**Origin**: Surfaced by `docs/specs/ignored-tests/` (decisions.md, 2026-05-09).
Both modules below were flagged as out-of-scope follow-ups when their
test files were retired.

---

## Phase 1: Requirements

### Why now

Two production modules in `attune-ai` are past their scheduled removal
date and were kept alive only by tests that have since been deleted.
With those tests gone, the modules now have **zero coverage** and zero
internal callers — they survive purely as legacy public API.

| Module | Deprecated in | Scheduled removal | Current version |
|---|---|---|---|
| `attune.workflows.orchestrated_release_prep` | v5.2.0 | v6.0 | **v6.6.0** (six minor versions overdue) |
| `attune.scaffolding` (CLI package) | (date TBD — see G1) | not formalized | **v6.6.0** |

`attune.scaffolding`'s `__main__.py` already emits a runtime deprecation
notice on every invocation (`_emit_cli_deprecation("attune.scaffolding",
"attune workflow run")`), and `pyproject.toml` excludes its CLI from
coverage measurement — the project has already abandoned the surface in
practice without a formal retirement.

### Scope

**In scope.**

1. Remove `src/attune/workflows/orchestrated_release_prep.py` and its
   re-exports.
2. Remove the `src/attune/scaffolding/` package and its CLI surface.
3. Update or remove example/demo code that references these modules.
4. Add a CHANGELOG entry under v6.7.0 (or whatever the next minor is)
   calling out the breaking removal with migration guidance.
5. Verify no sibling attune-* package imports either module.

**Out of scope.**

- The `ReleasePrepTeamWorkflow` replacement (already exists at
  `src/attune/agents/release/release_prep_team.py:359`, has live tests).
- Migrating any *future* deprecated modules — this spec covers exactly
  these two.
- Soft-removal via further deprecation warnings — both modules already
  warn; this spec performs the hard removal.

### Goals

- **G1.** Establish the formal deprecation date for `attune.scaffolding`
  by reading git history on `__main__.py`'s `_emit_cli_deprecation` call.
  Record it in CHANGELOG before removal.
- **G2.** Zero broken imports across `attune-ai`'s own source tree
  after removal: `pytest tests/unit/ -n auto` stays green.
- **G3.** Zero broken imports across the seven sibling repos
  (`attune-author`, `attune-docs`, `attune-gui`, `attune-gui-plugin`,
  `attune-help`, `attune-lite`, `attune-rag`, `attune-ai-action`).
  Verified via grep before commit.
- **G4.** CHANGELOG entry exists and names both removed modules with a
  one-line migration pointer for each.
- **G5.** No regression in the public lazy-import surface of
  `attune.workflows`. Removing two names from the lazy-export map
  should not break the `__getattr__` machinery.

### Non-goals

- Removing the deprecation **decorator/utility** itself
  (`attune._deprecation._emit_cli_deprecation`). Other modules may use
  it; this spec only retires its callers.
- Backporting the removal to a patch release — this is a minor-version
  bump (additive removal of a deprecated path).

---

## Public-API impact

`attune-ai` is a published PyPI package (currently v6.6.0). External
consumers may import from these paths even though they're deprecated.
After removal:

- `from attune.workflows.orchestrated_release_prep import OrchestratedReleasePrepWorkflow`
  → `ImportError`. Migration: use `attune workflow run release-prep`
  (CLI) or import `ReleasePrepTeamWorkflow` from
  `attune.agents.release`.
- `python -m attune.scaffolding create ...`
  → `ModuleNotFoundError`. Migration: `attune workflow run`.
- `from attune.scaffolding import ...` → `ImportError`. Migration:
  no Python-API replacement; the scaffolding surface was always a CLI.

The CHANGELOG entry must give each migration path verbatim.

### Release shape

Standard minor bump. The two removals are the headline of the release.
No coordinated changes needed in sibling repos (see G3 verification).
