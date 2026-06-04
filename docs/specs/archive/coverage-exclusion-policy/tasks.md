# Tasks: Coverage Exclusion Policy
**Status:** complete (2026-05-12)
---

## Phase 3: Tasks

### Phase 3A — Establish the policy + audit

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Add inline policy comment to `pyproject.toml` `[tool.coverage.run]` block. | pyproject.toml | done | This commit. |
| 2 | Audit all current `omit` entries for documentation. | docs | done | 64 total: 4 meta-excludes (no comment needed), 57 documented, **3 production-code entries undocumented** (see decisions.md). |
| 3 | Write `scripts/check_coverage_omits.py` enforcement script. | scripts | **done** | Shipped in Phase 3C (task #7). |

### Phase 3B — Resolve the 3 undocumented entries

Each is its own commit. Investigate before documenting.

| # | Entry | Status | Notes |
|---|-------|--------|-------|
| 4 | `*/hooks/scripts/help_freshness_nudge.py` | **done** | Documented in PR #212 (`68b4bb1c`) as "Standalone hook script (not importable via pytest)". Category 6. Verified 2026-05-12. |
| 5 | `*/meta_workflows/cli_commands/agent_commands.py` | **done** | Documented in PR #212 (`68b4bb1c`) as "Interactive agent CLI (requires live Claude agent loop)". Category 1, matches sibling-file wording. Verified 2026-05-12. |
| 6 | `*/attune/config.py` | **done** | Documented in PR #212 (`68b4bb1c`) as "Shadowed by attune/config/ package — unreachable import". Verified empirically (Category 8): `import attune.config` resolves to the package's `__init__.py`, not the .py file. Out-of-scope follow-up: this is dead code at the import layer; deletion should be tracked under `deprecated-module-retirement` rather than carry a permanent exclusion. See decisions.md. |

### Phase 3C — Add enforcement

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | Add `scripts/check_coverage_omits.py` (per design.md Artifact 3). | scripts | **done** | Line-based scanner; allowlists 4 meta-excludes; reports each offender with line number. Exit 0/1/2. Also normalized the 3 PR-#212 entries to inline comments to match the dominant convention (57 other entries use inline; design.md mandates inline). |
| 8 | Add pre-commit hook entry in `.pre-commit-config.yaml`. | .pre-commit-config.yaml | **done** | Local hook `check-coverage-omits`, runs on changes to `pyproject.toml` only. |
| 9 | Verify the enforcement script catches a deliberately-undocumented entry. | manual | **done** | Stripped the inline comment from `*/attune/config.py` temporarily; script reported "pyproject.toml:711: */attune/config.py" and exited 1. Comment restored; script exits 0. |

### Phase 3D — Spec close

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 10 | All 3 undocumented entries from Phase 3B resolved (documented or removed). | manual | **done** | 100% compliance (60/60 production-code entries). |
| 11 | `python scripts/check_coverage_omits.py` exits 0 on a clean tree. | manual | **done** | Verified 2026-05-12. |
| 12 | Mark spec status `complete` in all 4 .md files. | docs | **done** | This commit. |

### Failure-to-deliver path

If Phase 3B reveals that `attune/config.py` actually deserves coverage but writing tests would be a multi-day effort:

1. Mark task #6 as **deferred** with the blocker named.
2. Document the entry temporarily as Category 8 (justified-other) with the longer reason text: "*Currently uncovered pending refactor in spec X / issue Y. Tracked exclusion, not a permanent decision.*"
3. Continue with Phase 3C (enforcement script still has value).
4. Mark spec status as **partial** until config.py resolves.

The policy itself is delivered in Phase 3A; enforcement is delivered in Phase 3C; full audit resolution is the **complete** state.
