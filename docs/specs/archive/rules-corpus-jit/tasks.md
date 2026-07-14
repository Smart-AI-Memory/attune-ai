# Rules-Corpus JIT — Tasks

- [x] **T1 — Relocations + deletion.** `advanced-optimization-plan.md`
  → `docs/archive/planning/`, `debugging.md` +
  `vscode-extension-limitations.md` → `docs/archive/rules/`
  (provenance notes prepended); `markdown-formatting.md` deleted
  (duplicate of CLAUDE.md section).
- [x] **T2 — JIT-tail moves.** Five D1 files moved to
  `.claude/rules-tail/attune/`; body cross-refs repointed.
- [x] **T3 — paths-scope the six D1 scoped rules.** Frontmatter
  added with D1 globs; bodies unchanged.
- [x] **T4 — Resident INDEX.md.** 2,417 bytes; one trigger line per
  demoted rule; notes the reads-not-writes scoping caveat.
- [x] **T5 — Citation sweep.** 3 test docstrings +
  `docs/SECURITY_REVIEW.md`, `docs/reference/FAQ.md`,
  `docs/PERFORMANCE_OPTIMIZATION_ROADMAP.md` (7 refs) + rule-body
  cross-refs repointed. Residual matches verified
  history/generated-only (specs, archives, lessons,
  framework-docs, fixtures).
- [x] **T6 — Drift guard.**
  `tests/unit/rules/test_rules_residency_budget.py` — 4 tests:
  allowlist, ≤20KB budget, INDEX coverage of every demoted rule,
  scoped-glob liveness. Affected suites re-run: 59 passed.
- [x] **T7 — Receipt.** Eager rules bytes **116,590 → 12,851**
  (−89%; ≈26k tokens/session). Eager set = INDEX (2,417) +
  decision-routine (6,027) + xml-enhanced-prompts (2,920) +
  output-formatting (1,487).
- [ ] **T8 (local follow-up, not in PR) — R6 Redis layer.** Extend
  `~/.attune/memory/session_hydrate.py` to index
  `.claude/rules-tail/**` as `@layer:{rule}` pointers; commit to the
  memory repo; verify with an FT.SEARCH probe per the stopword
  lesson.
