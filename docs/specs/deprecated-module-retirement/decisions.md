# Per-module retirement decisions

Append-only log. One section per module as it's retired. See
`requirements.md`, `design.md`, `tasks.md` for the framework.

---

## Pre-execution decisions (recorded 2026-05-09)

### D1 — `examples/orchestration/basic_usage.py`: **rewrite**

Decision: rewrite the example against `ReleasePrepTeamWorkflow` from
`attune.agents.release` rather than delete it. The example carries
narrative value beyond the deprecated symbol it imports; orchestration
basics deserve a live, working demo using the current API.

Action at execution time: replace the import on line 23 and update
the body of the example to call `ReleasePrepTeamWorkflow` with its
current constructor signature. Verify the example runs end-to-end
before commit.

### D2 — CHANGELOG version bucket: **v7.0.0**

Decision: hold the removal until the v7.0.0 release. Rationale: v7.0.0
will also publish the 100% test coverage milestone — coupling the
breaking removal with the coverage announcement gives a single, clean
release narrative ("we hit 100% coverage; in the process we cleaned
out two long-deprecated modules") rather than two unrelated
breaking-change discussions in adjacent minor releases.

Implication for sequencing: the spec still executes when ready — the
file deletions and pyproject edits don't have to wait — but the
CHANGELOG entry slots under v7.0.0 and the release isn't cut until
the coverage push completes. If the coverage work surfaces additional
retirement candidates, those can land in the same v7.0.0 bucket.

### G1 — Formal deprecation date for `attune.scaffolding`: **2026-02-21**

Established via git history:

- **Module first introduced**: 2026-02-01 in commit `fafd4321`
  ("feat: Migrate empathy-framework to attune-ai") — at this point
  it was an active CLI surface, not deprecated.
- **Deprecation notice added**: 2026-02-21 in commit `3833d5d6`
  ("refactor: config decoupling, CLI deprecation, /plan brainstorm
  (#60)"). This is the commit that introduced the
  `_emit_cli_deprecation("attune.scaffolding", "attune workflow run")`
  call in `__main__.py`.

So `attune.scaffolding` will have been formally deprecated for
**~10 months by an estimated v7.0.0 release** (Feb 2026 → est. late
2026). That's a defensibly long warn period for a CLI-only surface
that already prints the deprecation notice on every invocation.

CHANGELOG entry should read approximately:

> **Removed** — `attune.scaffolding` package and its CLI surface
> (`python -m attune.scaffolding`). Deprecated since v… (2026-02-21,
> commit 3833d5d6); replaced by `attune workflow run`. Migration:
> use `attune workflow run <workflow-name>`.

(Fill in the version number from the v6.x history that contained
commit 3833d5d6 when writing the final entry.)

---

## Execution log

### Commit 1 (2026-05-09) — `attune.workflows.orchestrated_release_prep`

Branch: `retire-deprecated-modules-v7`. Commit: `41a6dc99`.

- Deleted `src/attune/workflows/orchestrated_release_prep.py` (637 lines).
- Edited `src/attune/workflows/__init__.py` per design.md (5 sites
  removed: TYPE_CHECKING import, two lazy-map entries, two `__all__`
  entries; one tombstone comment added).
- Applied D1 to `examples/orchestration/basic_usage.py`: rewrote
  Examples 1/2/8 against `ReleasePrepTeamWorkflow`.
- Side cleanup: removed broken Example 3 (`test_coverage_boost`
  was already deleted in a prior release; the import was dead).
- Side cleanup: trimmed three test classes from
  `tests/unit/test_coverage_batch6.py` (the file now covers only
  research_synthesis); removed `test_orchestrated_release_prep_warns`
  and the lazy-import preservation assertion from
  `tests/unit/workflows/test_workflow_consolidation.py`.
- Side cleanup: removed stale docstring reference in
  `src/attune/agents/release/release_prep_team.py:362`.

Verification: 14,103 passed, 0 failed under `-n auto` (baseline 14,110;
delta of -7 matches the deleted deprecated tests). `import
attune.workflows.orchestrated_release_prep` raises ModuleNotFoundError;
attribute access on `attune.workflows.OrchestratedReleasePrepWorkflow`
raises AttributeError; `from attune.workflows import
ReleasePrepTeamWorkflow` succeeds and is identity-equal to the
canonical `attune.agents.release.ReleasePrepTeamWorkflow`.

### Commit 2 (2026-05-09) — `attune.scaffolding`

Branch: `retire-deprecated-modules-v7`. Commit: `18d5e9b0`.

- Deleted `src/attune/scaffolding/` (9 files, 2,254 lines including
  jinja2 templates).
- Edited `pyproject.toml`: removed source-exclusion entry, BLE001
  per-file override, and three coverage-omit entries (cli.py,
  __main__.py, __init__.py).
- Edited `docs/reference/cli-reference.md`: removed the
  `python -m attune.scaffolding` row from the "Module Entry Points"
  table.

Verification: 14,103 passed, 0 failed (no change from Commit 1
baseline — nothing in tests depended on this package). `import
attune.scaffolding` raises ModuleNotFoundError. `import attune` and
`import attune.workflows` continue to succeed.

Note: `ruff check` (run as part of verification) reported 101
errors across the repo — pre-existing, unrelated to this work.
Ruff's auto-fix mode is configured in pyproject.toml such that
`ruff check` auto-modifies files; the resulting modifications to
~17 example/* files were reverted before committing (out of scope).

### Spec status: **done**

Both commits landed on branch `retire-deprecated-modules-v7`. CHANGELOG
entry added under v7.0.0. `docs/COVERAGE_BUG_LOG.md` updated with new
Class 5 ("deprecated production code outliving its tests") and a
session-49f entry covering both removals. Branch not pushed —
awaiting user review.
