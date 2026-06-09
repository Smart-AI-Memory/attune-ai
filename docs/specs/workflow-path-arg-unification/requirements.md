# Spec: Workflow `path` Kwarg Unification

**Status**: complete (2026-06-08) — all 5 target workflows accept `path`;
doc-orchestrator closed in #685. Verified by spec triage 2026-06-09
(`PathArgSpec` present, `test_path_support_registry.py` green).
**Created**: 2026-05-13
**Origin**: Follow-up to [`ops-runner-tier2`](../ops-runner-tier2/) Phase 1 audit. The audit (PR #285) found 5 of 19 workflows use a kwarg name other than `path` (`project_root`, `src_path`, `cwd`). PR #294 shipped a three-way `PATH_ARG_REGISTRY` as the bridge solution. This spec is the long-term cleanup that simplifies the registry to a binary.

---

## Phase 1: Requirements

### Problem

The CLI's `attune workflow run --path` accepts a uniform path argument for every workflow. Under the hood, it becomes a `path=...` kwarg in `workflow.execute(**input_data)`. But 5 workflows consume the kwarg under different names:

| Workflow | Actual kwarg | Source file |
|---|---|---|
| `health-check` | `project_root` | `src/attune/workflows/orchestrated_health_check.py` |
| `orchestrated-health-check` | `project_root` | (same file as above) |
| `doc-orchestrator` | `project_root` | `src/attune/workflows/documentation_orchestrator.py` |
| `test-audit` | `src_path` (required) | `src/attune/workflows/test_audit/workflow.py` |
| `rag-code-gen` | `cwd` | `src/attune/workflows/rag_code_gen.py` |

The current bridge solution (`PATH_ARG_REGISTRY` in `src/attune/ops/data.py`) catalogs this inconsistency so the ops runner can remap kwargs before subprocess spawn. The registry works — but it's a workaround. The cleaner long-term fix is to make every workflow accept `path` directly.

### Why this is its own spec, not a delta on ops-runner-tier2

Ops-runner-tier2 needs to ship the scope picker with current workflow APIs intact. Fixing the workflows is a parallel cleanup that:

- Touches 5 workflow files + their tests
- Should preserve backward compatibility (existing callers using `project_root=` / `src_path=` / `cwd=` shouldn't break)
- Is independent of any ops-runner UI work
- Once shipped, simplifies `PATH_ARG_REGISTRY` to "everything is `path`" (the registry can then become a sanity-check `frozenset` rather than a kwarg-remap table)

### Goals

- **G1.** Every workflow's `execute()` accepts `path` as a kwarg with the same semantics as the workflows that already accept it.
- **G2.** Backward compatibility — existing direct API callers using the old kwarg names (`project_root=`, `src_path=`, `cwd=`) continue to work, with a `DeprecationWarning` for one minor release.
- **G3.** `PATH_ARG_REGISTRY` simplifies to a `frozenset[str]` of registered workflow names (drift-guard only); the kwarg-remap logic in the ops runner becomes dead code that can be removed.
- **G4.** Documentation in each workflow's docstring updates to show `path=` as the canonical example, with a one-line note about the legacy kwarg name.

### Non-goals

- **Not a rewrite.** Each workflow's `execute()` body keeps the same internal kwarg name where it makes sense (`project_root` is a clearer variable name for `health-check`'s scope; `src_path` is more accurate for `test-audit`). The contract change is at the function signature only.
- **Not changing semantics.** `path` means the same thing across all 19 workflows: "scope this run to this directory."
- **Not adding new validation.** The CLI's `_validate_file_path()` already runs before the kwarg lands in `execute()`. No additional check needed at the workflow level.
- **Not touching `PATH_ARG_REGISTRY` until ALL 5 workflows are migrated.** Premature deletion would leave the ops runner without the kwarg-remap fallback during a partial migration.

### Documented categories

The 5 workflows split into three migration patterns:

**Pattern A — Single-alias forward (3 workflows).**
- `health-check` / `orchestrated-health-check` — accept `path=` in execute(), forward to `project_root` internally.
- `doc-orchestrator` — same pattern (forward to `project_root`).

**Pattern B — Renamed kwarg with deprecation (1 workflow).**
- `test-audit` — accept `path=` as the new canonical name, keep `src_path=` accepting + emitting `DeprecationWarning`.

**Pattern C — Semantic clarification (1 workflow).**
- `rag-code-gen` — `cwd` is genuinely different from `path` (it's the SDK working directory, not a scope target). Two options:
  - C1: Add `path=` as a new kwarg meaning "scope to this directory," set `cwd=path` internally.
  - C2: Document that `path` and `cwd` are the same thing for this workflow, accept both.
  - **C1 recommended** — clearer semantics, matches the user-facing meaning.

### Public-API impact

- **Direct callers** (uncommon — most users go via CLI): old kwarg names trigger `DeprecationWarning` for one minor version, then become hard errors.
- **CLI users**: no change — they already use `--path` regardless of internal kwarg name.
- **Ops dashboard users**: no change — the runner's kwarg remap continues to work during migration, and the user-visible picker is unchanged.

### Stop-and-decide thresholds

- **If any workflow's internal logic depends on the variable name** beyond signature naming (e.g., a docstring inspection looks up `self.execute.__signature__.parameters["project_root"]`), pause and reconsider — may need a wrapper instead of a rename.
- **If the migration breaks downstream callers we don't control** (e.g., a sibling package like `attune-author` calls `health_check.execute(project_root=...)` directly), bump the deprecation window from "next minor" to "next major release."

---

## Acceptance criteria

The spec is **done** when:

1. All 5 workflows' `execute()` signatures accept `path` as a kwarg.
2. Direct API tests confirm both `path=` (new) and old kwarg names (with `DeprecationWarning`) work.
3. `PATH_ARG_REGISTRY` reduced to a flat `frozenset[str]` (drift-guard); the `PathArgSpec` dataclass and remap logic in the ops runner are deletable.
4. CHANGELOG entry under `Changed` documents the deprecation window.
5. No regressions in existing test coverage; full unit suite green.
