# Tasks — Workflow `path` Kwarg Unification

**Status**: complete — all 5 target workflows accept `path` (doc-orchestrator closed in #685) — verified 2026-06-08 spec triage

Five per-workflow migrations + one registry-simplification PR. Each
per-workflow PR is independent and shippable in any order; PR-5 is
gated on PRs 1–4 landing.

---

## Phase 0 — Pre-flight (one-time, before any per-workflow PR)

- [ ] **0.1** Grep `attune-author`, `attune-help`, `attune-rag`, `attune-software` (sibling packages) for keyword usage of the legacy names on these 5 workflows:
      ```
      git grep -nE "project_root=|src_path=|cwd=" ../attune-*/src/
      ```
      Document any hits in `decisions.md` — they need coordinated minor-version bumps.

- [ ] **0.2** Confirm the `claude_agent_sdk` `cwd=` parameter on `rag-code-gen` is the SDK working directory (not a scope target). If they're semantically distinct (likely), the migration to `path` is a layer above `cwd` — both can coexist with `path` being the user-facing alias.

---

## Phase 1 — Per-workflow migrations (each is its own PR)

### PR-1 — `health-check` + `orchestrated-health-check`

Shared source file: `src/attune/workflows/orchestrated_health_check.py`.

- [ ] **1.1** Update `execute()` signature: accept keyword-only `path: str | None = None`; keep `project_root` as deprecated alias.
- [ ] **1.2** Emit `DeprecationWarning` when `project_root=` is set without `path=`.
- [ ] **1.3** Update the existing "Map 'target' to 'project_root' for VSCode compat" block to map to `path` instead. Keep `target=` accepting.
- [ ] **1.4** Update class docstring's example to use `path=`. Note legacy alias in a one-line comment.
- [ ] **1.5** Add tests:
      - `test_execute_accepts_path_kwarg` — `execute(path=...)` works
      - `test_execute_legacy_project_root_warns` — `execute(project_root=...)` emits `DeprecationWarning` AND still runs
      - `test_execute_both_kwargs_path_wins` — `execute(path="a", project_root="b")` uses `"a"`, warns
      - `test_target_still_maps_to_path` — `execute(target=...)` still works (VSCode compat)
- [ ] **1.6** Update `PATH_ARG_REGISTRY` entry for both workflows: change `kwarg="project_root"` → `kwarg="path"`. Drift-guard test in `tests/unit/ops/test_path_support_registry.py` then validates the migration completed.

### PR-2 — `doc-orchestrator`

Source file: `src/attune/workflows/documentation_orchestrator.py`.

- [ ] **2.1** Update `execute()` body to read `kwargs.get("path") or kwargs.get("project_root")`, with `DeprecationWarning` on the latter.
- [ ] **2.2** Update class docstring example.
- [ ] **2.3** Add tests (same shape as 1.5 minus the `target` test).
- [ ] **2.4** Update `PATH_ARG_REGISTRY` entry.

### PR-3 — `test-audit`

Source file: `src/attune/workflows/test_audit/workflow.py`.

- [ ] **3.1** Update `execute()` body: accept `path` first, fall back to `src_path` with `DeprecationWarning`. Internal variable can stay `src_path` for code clarity — only the public kwarg name changes.
- [ ] **3.2** Update error message: `"path argument is required"` instead of `"src_path argument is required"`. Include `(was: src_path)` to bridge the rename in the immediate window.
- [ ] **3.3** Update class docstring example.
- [ ] **3.4** Add tests (same shape as PR-2's, plus the `required` case — `execute()` with no path returns `_error_result`).
- [ ] **3.5** Update `PATH_ARG_REGISTRY` entry: `kwarg="src_path"` → `kwarg="path"`; `required=True` stays.

### PR-4 — `rag-code-gen`

Source file: `src/attune/workflows/rag_code_gen.py`.

**Decision needed at PR-author time**: option C1 (add `path` as separate kwarg meaning "scope target") vs option C2 (treat `path` as an alias for `cwd`). Default to C1 if `cwd` is genuinely the SDK working-directory (not user-scope); confirm in Phase 0 task 0.2.

- [ ] **4.1** Update `execute()` body to accept both kwargs; map `path → cwd` internally for the SDK.
- [ ] **4.2** Update class docstring.
- [ ] **4.3** Add tests.
- [ ] **4.4** Update `PATH_ARG_REGISTRY` entry: `kwarg="cwd"` → `kwarg="path"`.

---

## Phase 2 — Registry simplification (PR-5)

Gated on PRs 1–4 all merged.

- [ ] **5.1** Verify all 19 workflows now accept `path`: run `pytest tests/unit/ops/test_path_support_registry.py -v` and confirm every parametrized `TestRegistryKwargMatchesSource::test_kwarg_appears_in_execute_source[*]` test asserts kwarg=`"path"`.
- [ ] **5.2** Collapse `PATH_ARG_REGISTRY: dict[str, PathArgSpec]` → `WORKFLOWS_ACCEPTING_PATH: frozenset[str]`. Drop the `PathArgSpec` dataclass entirely.
- [ ] **5.3** Update `tests/unit/ops/test_path_support_registry.py`:
      - Remove the parametrized kwarg-drift tests (now uniformly `path`)
      - Keep the coverage-drift test (every workflow in the registry, no orphans)
      - Keep the shape-invariant tests but drop `required` semantics
- [ ] **5.4** Remove the kwarg-remap logic in the ops runner (Phase 2.5 of `ops-runner-tier2`, if landed; otherwise no-op since runner doesn't read remap yet).
- [ ] **5.5** CHANGELOG entry under `Changed`: document the deprecation window (v6.8 → v7.0) and the new uniform `path` kwarg.
- [ ] **5.6** Update the `ops-runner-tier2` Phase 1.3 references in `docs/specs/` to point at the simplified registry.

---

## Phase 3 — Spec close

- [ ] **6.1** All 5 workflows accept `path`; tests green; CI green on merged commits.
- [ ] **6.2** `PATH_ARG_REGISTRY` simplified or deleted.
- [ ] **6.3** CHANGELOG documents the deprecation window.
- [ ] **6.4** Mark spec status `complete` in all three .md files.
- [ ] **6.5** Update parent spec (`ops-runner-tier2/`) tasks.md to note the simplification.

---

## Failure-to-deliver path

If a per-workflow PR (1–4) hits unexpected coupling that makes the migration risky:

1. Mark that PR's row as `deferred` with the blocker named in Notes.
2. Keep that workflow's entry in `PATH_ARG_REGISTRY` (`PathArgSpec(kwarg="<old>", ...)`).
3. PR-5 ships with a smaller-but-not-flat registry — still net positive (fewer aliased entries).
4. Spec status flips to `partial`; the unfinished workflow is documented in `decisions.md`.

The spec is **done** when at least 4 of the 5 workflows are migrated AND the registry has shrunk meaningfully.

---

## Sequencing inside Phase 1

All four PRs are independent. Suggested order (smallest first):

1. **PR-2 (`doc-orchestrator`)** — single workflow, no shared file, simplest case.
2. **PR-1 (`health-check` + `orchestrated-health-check`)** — two workflows sharing a file, pattern-confirms.
3. **PR-3 (`test-audit`)** — adds the `required` semantics case.
4. **PR-4 (`rag-code-gen`)** — has the semantic-clarification decision (C1 vs C2) so leave for last when the pattern is well-rehearsed.
5. **PR-5 (registry simplification)** — gated.

Total estimate: 4 × ~50 LoC migrations + ~30 LoC simplification = ~230 LoC over 5 small PRs.
