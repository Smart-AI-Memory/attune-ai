# Design: Deprecated Module Retirement

**Status**: draft

---

## Phase 2: Design

### Approach

Two independent removals, sequenced as **two commits** (not one). Each
removal is small and self-contained; bundling them would obscure
bisect signal if either breaks something downstream.

Order: **`orchestrated_release_prep` first, `attune.scaffolding`
second.** Rationale: the first has known re-export sites that must be
edited in lockstep; the second is a leaf package with no internal
callers and is therefore lower-risk. Land the trickier one first while
attention is fresh.

### Module 1: `attune.workflows.orchestrated_release_prep`

**Files to delete:**

- `src/attune/workflows/orchestrated_release_prep.py`

**Files to edit:**

- `src/attune/workflows/__init__.py`
  - Line 76: remove
    `from .orchestrated_release_prep import OrchestratedReleasePrepWorkflow, ReleaseReadinessReport`
    (this is inside a `TYPE_CHECKING` or eager block — confirm before
    editing).
  - Line 157: remove `".orchestrated_release_prep",` from the lazy-import
    submodule list.
  - Line 160: remove the `"ReleaseReadinessReport": (".orchestrated_release_prep", "ReleaseReadinessReport"),`
    entry from the lazy-export map.
  - Verify nothing else in the file references either symbol.
- `examples/orchestration/basic_usage.py`
  - Line 23: `from attune.workflows.orchestrated_release_prep import OrchestratedReleasePrepWorkflow`
  - Decision: rewrite this example against `ReleasePrepTeamWorkflow`,
    or delete the example if it duplicates an existing one. Read the
    full file before deciding — an example that's only kept alive by
    a deprecated module is itself a candidate for removal.

**Symbols removed from public API:** `OrchestratedReleasePrepWorkflow`,
`ReleaseReadinessReport`, `QualityGate` (whatever else the module
exports — confirm by reading the file's `__all__` if defined).

**Replacement is already shipped:**
`attune.agents.release.ReleasePrepTeamWorkflow` (file at
`src/attune/agents/release/release_prep_team.py:359`, tested at
`tests/unit/agents/test_release_prep_team.py`). The dataclasses
(`QualityGate`, `ReleaseReadinessReport`) are duplicated in
`src/attune/agents/release/release_models.py`.

### Module 2: `attune.scaffolding`

**Files to delete (entire subtree):**

- `src/attune/scaffolding/__init__.py`
- `src/attune/scaffolding/__main__.py`
- `src/attune/scaffolding/cli.py`
- `src/attune/scaffolding/methodologies/pattern_compose.py`
- `src/attune/scaffolding/README.md`
- (any other files under `src/attune/scaffolding/` after a final
  `find src/attune/scaffolding -type f` check)

**Files to edit:**

- `pyproject.toml` — remove the per-path lint/coverage entries for
  `scaffolding/`:
  - The `"scaffolding/"` entry in the source-exclusion block (where it
    appears alongside `benchmarks/` and `workflow_patterns/`).
  - `"scaffolding/**/*.py" = ["BLE001"]` in the per-file-ignores block.
  - `*/scaffolding/cli.py` and `*/scaffolding/__main__.py` in the
    coverage-omit block (`pyproject.toml:630-631` per audit).
- Search for `"scaffolding"` and `attune.scaffolding` across the repo
  one more time before commit; clean up any docs hits.

**No replacement to wire in.** Users of `python -m attune.scaffolding`
already see the deprecation notice pointing at `attune workflow run`.
After removal, the failure mode shifts from "warning + still works" to
"ModuleNotFoundError." That's the intended terminal state.

### Verification strategy

Per-removal checklist (run after each commit, before pushing):

1. `pytest tests/unit/ -n auto` — green; count ≥ 14,110 (current
   baseline from ignored-tests spec).
2. `python -c "import attune; import attune.workflows; import attune.workflows as w; print(dir(w))"`
   — no AttributeError; the lazy-export machinery still works for the
   names we *kept*.
3. `git grep -n "orchestrated_release_prep\|attune\.scaffolding"` —
   returns only intentional references (CHANGELOG, this spec, possibly
   the deprecation utility itself).
4. **Cross-repo grep**:
   `grep -rn "attune\.scaffolding\|attune\.workflows\.orchestrated_release_prep\|OrchestratedReleasePrepWorkflow" ~/attune-author ~/attune-docs ~/attune-gui ~/attune-gui-plugin ~/attune-help ~/attune-lite ~/attune-rag ~/attune-ai-action --include="*.py" --include="*.md" --include="*.toml"`
   — must return no hits. (Pre-spec check on 2026-05-09 already returned
   nothing; re-confirm before each commit because sibling repos move
   independently.)

### Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | A test outside `tests/unit/` (e.g. `tests/integration/`) imports the deprecated paths and only fails when integration tests run. | Before removing each module, run `git grep -rn` on its full module path across `tests/` (all subdirs, not just `tests/unit/`). |
| 2 | The lazy-import map in `workflows/__init__.py` has a fallback path that swallows ImportError silently, so removing the entry could mask a real bug elsewhere. | Read the full `__init__.py` first; verify the lazy machinery raises on miss for unknown names. |
| 3 | An external PyPI consumer breaks on the next release. | This is the intended behavior; the CHANGELOG entry is the contract. Include the migration snippet verbatim. |
| 4 | Dropping `"scaffolding"` from `pyproject.toml` per-path overrides surfaces previously-suppressed lint failures elsewhere if the same path glob matched anything outside the deleted package. | Re-run `ruff check` after the pyproject edits. The path globs are scoped to `scaffolding/**/*.py`, so this should be a no-op once the directory is gone. |
| 5 | The `_emit_cli_deprecation` utility might have only one caller (this one). After removal it becomes dead code. | Out of scope per non-goals, but worth a one-line note in CHANGELOG: "If `_emit_cli_deprecation` becomes unused, candidate for follow-up cleanup." |

### Decisions to make at execution time

- **D1.** Rewrite `examples/orchestration/basic_usage.py` against
  `ReleasePrepTeamWorkflow`, or delete it? Decide after reading the
  file and checking whether `examples/agents/release/` already has an
  equivalent.
- **D2.** Should the CHANGELOG entry live under v6.7.0 or wait for
  v7.0.0? Major-version arguments: this is a public-API breaking
  removal. Minor-version arguments: both modules have warned for many
  versions already; the project's deprecation policy treats the warn
  period as the breaking-change buffer. Default: v6.7.0 unless other
  pending breaks suggest a v7.0 rollup.
