# Tasks: Coverage Exclusion Policy

**Status**: approved (Phase 3A done in this commit)

---

## Phase 3: Tasks

### Phase 3A — Establish the policy + audit

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Add inline policy comment to `pyproject.toml` `[tool.coverage.run]` block. | pyproject.toml | done | This commit. |
| 2 | Audit all current `omit` entries for documentation. | docs | done | 64 total: 4 meta-excludes (no comment needed), 57 documented, **3 production-code entries undocumented** (see decisions.md). |
| 3 | Write `scripts/check_coverage_omits.py` enforcement script. | scripts | todo | Phase 3B. |

### Phase 3B — Resolve the 3 undocumented entries

Each is its own commit. Investigate before documenting.

| # | Entry | Status | Notes |
|---|-------|--------|-------|
| 4 | `*/hooks/scripts/help_freshness_nudge.py` | todo | Likely Category 6 (standalone script). Confirm by reading the file's invocation pattern, then add `# Standalone hook script (runs as subprocess via Claude Code hook, not importable via pytest)` comment. |
| 5 | `*/meta_workflows/cli_commands/agent_commands.py` | todo | Read the file. Sibling files in same dir are excluded with reason `# Interactive analytics`, `# Interactive templates` etc. (Category 1). If `agent_commands.py` follows the same shape, document with matching comment. If it doesn't, decision: cover with tests vs. document a non-Category-1 reason. |
| 6 | `*/attune/config.py` | todo | **Highest-priority audit**. `config.py` is usually core production code; an undocumented exclusion here is a smell. Read the file. Three plausible outcomes: (a) it has env-var-dependent code that's not testable as-is → split file, cover the testable half, document the loader; (b) coverage was disabled during a refactor and never restored → write tests, remove from omit list; (c) the file is genuinely a thin re-export shim → document as Category 7-adjacent. |

### Phase 3C — Add enforcement

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | Add `scripts/check_coverage_omits.py` (per design.md Artifact 3). | scripts | todo | After Phase 3B so the script doesn't immediately fail on existing entries. |
| 8 | Add pre-commit hook entry in `.pre-commit-config.yaml`. | .pre-commit-config.yaml | todo | D3 decision. Lightweight; recommended now. |
| 9 | Verify the enforcement script catches a deliberately-undocumented entry. | manual | todo | Add a test omit entry without comment, run the script, confirm it fires. Remove the test entry. |

### Phase 3D — Spec close

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 10 | All 3 undocumented entries from Phase 3B resolved (documented or removed). | manual | todo | |
| 11 | `python scripts/check_coverage_omits.py` exits 0 on a clean tree. | manual | todo | |
| 12 | Mark spec status `complete` in all 4 .md files. | docs | todo | |

### Failure-to-deliver path

If Phase 3B reveals that `attune/config.py` actually deserves coverage but writing tests would be a multi-day effort:

1. Mark task #6 as **deferred** with the blocker named.
2. Document the entry temporarily as Category 8 (justified-other) with the longer reason text: "*Currently uncovered pending refactor in spec X / issue Y. Tracked exclusion, not a permanent decision.*"
3. Continue with Phase 3C (enforcement script still has value).
4. Mark spec status as **partial** until config.py resolves.

The policy itself is delivered in Phase 3A; enforcement is delivered in Phase 3C; full audit resolution is the **complete** state.
