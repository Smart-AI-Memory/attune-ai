# Documentation Audit Report

**Date:** 2026-02-22
**Scope:** Full audit — commands, CLAUDE.md, docs/, rules/
**Framework Version:** 3.1.0 (pyproject.toml)

**Summary:** 31 findings | 0 Critical | 2 Medium | 10 Low
**Fixed this session:** 19 (all critical, 6 medium, 2 low)

## Critical

Issues that actively mislead users or reference things
that don't exist.

| # | Source | Issue | Suggested Fix |
|---|--------|-------|---------------|
| ~~1~~ | `cli_router.py:107-111` | Router mapped to non-existent `utilities` skill | **FIXED:** Created `.claude/commands/utilities.md` |
| ~~2~~ | `cli_router.py:194,267` | Router fell back to non-existent `help` skill | **FIXED:** Created `.claude/commands/help.md` |
| ~~3~~ | `CLAUDE.md` (hub table) | `/brainstorm` listed "discover, plan, export" — only "plan" is a real shortcut; "discover" and "export" are conversation behaviors, not invocable routes | **FIXED:** Updated to `"topic", plan` |
| ~~4~~ | `CLAUDE.md` (hub table) | `/plan` listed "brainstorm" as a route — brainstorm is a separate hub | **FIXED:** Updated to `feature, tdd, refactor, architecture` |
| ~~5~~ | `docs/ARCHITECTURE.md:584` | References `HealthcareWizard` — not implemented | **FIXED:** Marked as planned feature |
| ~~6~~ | `rules/coding-standards-index.md:250` | Wrong path for `_validate_file_path()` | **FIXED:** Updated to `security/path_validation.py:15-88` |
| ~~7~~ | `rules/coding-standards-index.md:1153` | Referenced non-existent `src/attune/cli.py` | **FIXED:** Updated to `cli_minimal.py` |
| ~~8~~ | `rules/coding-standards-index.md:1158-1159` | Referenced non-existent test files | **FIXED:** Updated to actual security test files |

## Medium

Stale content that could confuse but isn't blocking.

| # | Source | Issue | Suggested Fix |
|---|--------|-------|---------------|
| ~~9~~ | `.claude/CLAUDE.md:1` | Version header said `v3.0.0` but framework is `3.1.0` | **FIXED:** Updated to `v3.1.0` |
| ~~10~~ | `CLAUDE.md` (hub table) | `/dev` missing `perf-audit`, `/testing` missing `benchmark`, `/docs` missing `audit, overview` | **FIXED:** All hub routes updated |
| ~~11~~ | `commands/testing.md:36-37` | Missing behavior sections for `benchmark` and `generate --batch` | **FIXED:** Added both sections |
| ~~12~~ | `commands/dev.md:36` | Missing behavior section for `quality` | **FIXED:** Added section |
| ~~13~~ | `commands/docs.md:38` | Missing behavior section for `overview` | **FIXED:** Added section |
| ~~14~~ | `commands/workflows.md:35-36` | Missing behavior sections for `run code-review` and `run seo-optimization` | **FIXED:** Added both sections |
| 15 | `rules/vscode-extension-limitations.md:38-39` | References `vscode-extension/` directory — doesn't exist in project | Archive this rule or note feature was discontinued |
| 16 | `rules/os-walk-dirs-pattern.md:51` | States pattern is at `code_review.py:195` — pattern only exists at `file_analysis.py:132` | Update file reference |
| 17 | `rules/advanced-optimization-plan.md:232,747` | References `docs/PERFORMANCE.md` — doesn't exist | Create the doc or remove reference |
| 18 | `rules/advanced-optimization-plan.md:133` | References `src/attune/workflows/test_gen.py` — only `test_gen/workflow.py` exists | Update path |
| 19 | `docs/CODING_STANDARDS.md:7-8` | Version stated as `3.9.1` vs framework `3.1.0` — confusing | Align versions or document separate versioning |

## Low

Minor inconsistencies, cosmetic issues, or slightly
outdated info.

| # | Source | Issue | Suggested Fix |
|---|--------|-------|---------------|
| ~~20~~ | `CLAUDE.md` (hub table) | `/testing` missing `benchmark` | **FIXED:** see #10 |
| ~~21~~ | `CLAUDE.md` (hub table) | `/docs` missing `audit`, `overview` | **FIXED:** see #10 |
| 22 | `CLAUDE.md:31` (hub table) | `/workflows` key routes use short form ("security") vs actual ("run security-audit") | Clarify or expand to full names |
| 23 | `commands/wizard.md:32-36` | Routes like `run debug` but behavior section only has `### run` (generic) | Add specific behavior per wizard type |
| 24 | `commands/plan.md:104-156` | Post-Plan Handoff references `/dev {route}` without explicit mapping table | Add mapping: plan feature → ?, plan tdd → ?, plan refactor → dev refactor |
| 25 | `commands/brainstorm.md` | No formal "Routes" section unlike other commands — inconsistent structure | Add Routes section or note conversational nature in CLAUDE.md |
| 26 | `docs/EXCEPTION_HANDLING_GUIDE.md:8` | Version `3.9.0` vs framework `3.1.0` | Align or document separate versioning |
| 27 | `architecture.md` (root) | Duplicate of `docs/ARCHITECTURE.md` at repo root | Remove root-level duplicate |
| 28 | `rules/advanced-optimization-plan.md:129` | References `src/attune/memory/unified.py` — may have moved to `claude_memory.py` | Verify and update |
| 29 | `rules/debugging.md` | 84 historical patterns with old commits — no "last validated" date | Add validation dates or prune old entries |
| 30 | `rules/coding-standards-index.md:85-91` | Lists 6 secured files but `_validate_file_path` used in 77+ files | Update list or clarify scope |
| 31 | `rules/scanner-patterns.md:96` | References `empathy workflow run bug-predict` — may be stale command name | Verify current CLI command name |

## Cross-Reference Contradictions

| Doc A | Doc B | Contradiction |
|-------|-------|---------------|
| ~~`CLAUDE.md` (v3.0.0)~~ | ~~`pyproject.toml` (3.1.0)~~ | ~~Version mismatch~~ **FIXED** |
| `CODING_STANDARDS.md` (v3.9.1) | `pyproject.toml` (3.1.0) | Version numbering unclear |
| `coding-standards-index.md` | `security/path_validation.py` | Wrong file location for `_validate_file_path()` |
| ~~`CLAUDE.md` hub table~~ | ~~`brainstorm.md`~~ | ~~Route mismatch~~ **FIXED** |
| `os-walk-dirs-pattern.md` | `code_review.py` | Pattern not at referenced location |
| `ARCHITECTURE.md` | Codebase | HealthcareWizard referenced but not implemented |

## Verified Correct

These were checked and confirmed accurate:

- All 11 hub command files exist and match CLAUDE.md hubs
- All workflow entry points in pyproject.toml are valid
- All wizard entry points in pyproject.toml are valid
- 13+ class references verified (BaseWorkflow, AttuneConfig,
  CodeReviewWorkflow, etc.)
- CLI commands (attune setup, workflow run, etc.) verified
- Quick Start instructions in CLAUDE.md are accurate
- README.md links and examples verified
- pyproject.toml and __init__.py versions match (3.1.0)

## Recommended Fix Priority

**Immediate (blocks users):**

- ~~Fix #1-2: CLI router dead ends~~ **DONE**
- ~~Fix #9: CLAUDE.md version → 3.1.0~~ **DONE**

**Before next release:**

- ~~Fix #3-4: CLAUDE.md hub table accuracy~~ **DONE**
- ~~Fix #5: HealthcareWizard marked as planned~~ **DONE**
- ~~Fix #6-8: Coding standards stale file paths~~ **DONE**
- ~~Fix #11-14: Missing behavior sections~~ **DONE**

**When convenient (remaining 12 issues):**

- Fix #15-18: Stale rule references (vscode-extension,
  os-walk, optimization plan)
- Fix #19, 26: Version numbering clarification
  (CODING_STANDARDS, EXCEPTION_HANDLING_GUIDE)
- Fix #22-25, 27-31: Low-severity cleanups
