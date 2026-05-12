# Design: Coverage Exclusion Policy

**Status**: complete (2026-05-12)

---

## Phase 2: Design

### Approach

Three small artifacts, each landing as its own commit:

1. **The policy itself**, expressed inline in `pyproject.toml`'s
   `[tool.coverage.run]` block as a comment header. Lives where
   it applies; no indirection.
2. **Audit + resolution** for the 3 currently-undocumented
   entries. Each entry gets either a documented reason matching a
   Phase 1 category OR removed from the omit list (covered by new
   tests in a follow-up).
3. **Enforcement script** at `scripts/check_coverage_omits.py`
   that fails if any production-code omit entry lacks a `#`
   comment. Optional pre-commit hook integration.

### Artifact 1 — Inline policy comment in `pyproject.toml`

Add a comment block immediately above the `omit = [` opening
bracket:

```toml
[tool.coverage.run]
source = ["attune", "attune_software"]

# Coverage exclusion policy (docs/specs/coverage-exclusion-policy):
# Every production-code entry below MUST have an inline `#` comment
# stating the reason. Reason should fit one of the categories in
# requirements.md (interactive CLI, infrastructure server, live
# service required, deprecated, optional adapter, standalone script,
# example/demo, justified-other). Meta-excludes (test discovery
# patterns, build artifacts, third-party paths) do not need comments.
# Enforced by scripts/check_coverage_omits.py.
omit = [
    "*/tests/*",
    ...
]
```

### Artifact 2 — Audit resolution

The 3 currently-undocumented production-code entries:

| Entry | Proposed action |
|---|---|
| `*/hooks/scripts/help_freshness_nudge.py` | **Document** — Category 6 (standalone script). Comment: `# Standalone hook script (runs as subprocess via Claude Code hook, not importable via pytest)`. |
| `*/meta_workflows/cli_commands/agent_commands.py` | **Investigate first.** If interactive CLI like sibling files in the same directory → Category 1, document. If not interactive, consider whether it should be covered. |
| `*/attune/config.py` | **Investigate first.** This is suspicious — `config.py` is usually core production code that *should* have coverage. Possible reasons it's excluded: legacy decision, broken tests, env-var-dependent loader. Read the file before deciding category vs. coverage. |

The audit step is the value here, not the documentation per se.
Each undocumented entry is a *question being deferred*. Surfacing
the question is the point.

### Artifact 3 — Enforcement script

`scripts/check_coverage_omits.py`: line-based TOML inspection that
walks the `[tool.coverage.run] omit = [...]` block and reports any
entry that (a) is not in the meta-exclude allowlist and (b) has no
inline `#` comment. Exits 0 if clean, 1 with offender list
otherwise.

Meta-exclude allowlist (no comment needed): `*/tests/*`,
`*/test_*.py`, `*/__pycache__/*`, `*/site-packages/*`.

Optional pre-commit hook entry (in `.pre-commit-config.yaml`):
local hook running `python scripts/check_coverage_omits.py` only
when `pyproject.toml` changes.

### Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Documenting `attune/config.py` as excluded when it should actually have coverage. | Phase B explicitly investigates this entry before documenting. |
| 2 | The enforcement script's TOML parsing is line-based and brittle (won't handle alternate formatting). | Acceptable for v1 — pyproject.toml's structure here is stable. Migrate to `tomllib` parsing if formatting changes. |
| 3 | Future contributors won't know about the policy. | The inline comment in `pyproject.toml` is the primary documentation; the spec is the secondary reference. Pre-commit hook is the active enforcement. |
| 4 | "Justified-other" category becomes a dumping ground. | Spec's wording requires longer reason text for that category. Code review enforcement. |

### Decisions to make at execution time

- **D1.** `agent_commands.py` — interactive CLI or testable code? Read the file in Phase B.
- **D2.** `attune/config.py` — investigate the original reason for exclusion. Likely candidates for action: (a) document as a category-fit, (b) remove from omit list and write tests, (c) split the file so the testable parts are covered and the env-var-dependent loader is excluded.
- **D3.** Pre-commit hook integration — add now or defer to a follow-up? Light-touch suggests now (one extra file in `.pre-commit-config.yaml`).
