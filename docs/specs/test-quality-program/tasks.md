# Tasks: Test Quality Program
**Status:** living (ongoing program — continuous use; never one-shot "complete")
---

## Phase 3: Tasks

### Phase 3A — Bootstrap (one-time, gates the proof-of-concept)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Spec approval — merge requirements.md + design.md + tasks.md. | spec | todo | This PR. |
| 2 | Write rubric scoring script at `scripts/score_test_quality.py`. Inputs: a `coverage.xml` plus the customer-weight table. Outputs: `docs/specs/test-quality-program/rubric_cache.csv` sorted by score desc. | scripts | todo | Small Python file (~100 lines). Reuses stdlib `xml.etree` and the customer-weight table hard-coded with citations to design.md §Prioritization rubric. |
| 3 | Generate the first rubric pass. Run the script against the latest CI `coverage.xml` (or a fresh local `--cov-report=xml` run if no recent CI artifact). Commit `rubric_cache.csv`. | scripts | todo | First snapshot of the working set. |
| 4 | Cache rubric output as project memory so future sessions don't recompute. Memory file: top 20 modules + score + last_modified + customer_weight (no full CSV, just the working set pointer). | memory | todo | Memory entry per the auto-memory system. Type: `project`. |

### Phase 3B — First proof-of-concept (validates the playbook)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 5 | Surface top 3-5 candidate modules from rubric output. Surface to Patrick with a one-line summary of each (customer-weight, coverage gap, risk multiplier, suspected bug shape). | spec | todo | Output of task #3 informs the picks. |
| 6 | Pick one module for the first end-to-end loop. Document the choice and reasoning in a row in `docs/specs/test-quality-program/decisions.md` (append-only log, same shape as `ignored-tests/decisions.md`). | spec | todo | Patrick picks (or confirms). |
| 7 | Execute per-module loop steps (a)-(h) per design.md §Per-module loop on the chosen module. Each major step gets its own commit. | src + tests | todo | One PR for the module. Bugs surfaced trigger fix commits inline OR a sibling PR if scope demands (per design.md risk #5). |
| 8 | Ship: PR + CHANGELOG entry + `docs/COVERAGE_BUG_LOG.md` entry. Status moves to `active`. | release | todo | First entry under this spec in the bug log. Confirms the playbook is operational, not theoretical. |

### Phase 3C — Steady-state (long-running)

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 9+ | Per-module cycles, one per session. Each cycle: pick from working set → run loop → ship. Refresh rubric (`scripts/score_test_quality.py`) when output is >2 weeks stale or after any large refactor. | various | recurring | No closure condition. Each cycle's deliverable is a merged PR + log entry. |

### Phase 4 — Rubric refinement: usage signal

Three consecutive cycles on 2026-05-12 (cycles 12, 13, 14) surfaced
unused-or-silently-skipped modules as top rubric picks:

| PR | Module | Issue |
|----|--------|-------|
| #287 | `cli_commands/help_commands.py` | 16 silently-skipped tests via `pytest.importorskip("frontmatter")` |
| (n/a) | `workflows/test_lifecycle.py` + `test_maintenance_cli.py` | Orphan modules with zero inbound imports; source-marked "Removed" |
| #289 | `workflows/test_runner_helpers.py` | Dead defensive `try/except` block (the 2% coverage gap was unreachable code) |

The current score formula `weight × coverage_gap × risk_multiplier`
ranks modules by "user value × untested surface" — exactly right for
healthy code but wrong for dead/skipped code. The program needs a
**usage signal** to deprioritize orphan modules.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 10 | Add inbound-import count to `scripts/score_test_quality.py`. For each module, count distinct importing files outside its own package (`grep -rln "from attune.<module> " src/` or `grep -rln "import attune.<module>" src/`). Output a new `inbound_imports` column in `rubric_cache.csv`. | scripts | done | Stdlib only; ~30 lines of Python. No behavior change to the score yet — this task just measures. |
| 11 | Add a usage-discount factor to the score formula. Proposed: `score = weight × gap × risk × min(1.0, inbound_imports / N)` where `N` is tunable (start with 5). Document the threshold choice in `design.md §Prioritization rubric`. | scripts + design.md | done | Apply to `rubric_cache.csv` and verify the three modules flagged above drop off the top of the working set. |
| 12 | Update playbook in `design.md §Per-module loop` with the "diagnostic for the rubric" pattern from CLAUDE.md: when a picked module has surprisingly low `covered_pct` AND a non-trivial test file exists, grep for `pytest.importorskip` BEFORE writing tests. If a test file gates the module on an `importorskip("X")` and X isn't in `[dev]`, the fix is one line in pyproject.toml. | design.md | done | One-paragraph addition; not a full phase. |

Closes once tasks 10-12 ship and the next rubric refresh shows the
flagged modules no longer in the top 20.

### Phase 5 — Mutation-driven module rewrites

Some modules pass the coverage rubric (high line coverage) yet fail
**mutation** testing — the coverage is padded. These don't fit the
one-module-one-PR loop and get their own sequenced sub-plans.

| # | Module | Survival | Plan | Status |
|---|--------|----------|------|--------|
| 13 | `models/auth_strategy.py` | 128/270 (~53%) | [auth-strategy-mutation-rewrite.md](./auth-strategy-mutation-rewrite.md) | planned — `get_recommended_mode` done ([#793](https://github.com/Smart-AI-Memory/attune-ai/pull/793)); 6 sub-slices remain |

When a future rubric/mutation cycle flags another padded module, add a
row here and author a sibling plan rather than forcing it through the
single-PR loop.

### Done-state for this spec

This spec is a **standing program**, not a one-shot deliverable.
Status milestones:

- **draft** → today. Requirements + design + bootstrap tasks
  not yet executed.
- **active** → after task #8 ships. The playbook is proven; the
  rubric is operational; subsequent cycles execute under "Phase
  3C" indefinitely.
- **closed** → only if the program is deliberately wound down
  (e.g., the codebase shrinks below a size where module-by-
  module work makes sense, or quality work moves to a different
  framework). Closure requires an explicit decision; no
  auto-close.

### Out-of-scope follow-ups (flagged, not committed)

- **`scaffolding` and `orchestrated_release_prep` deletion.**
  Both are deprecated past their scheduled removal version
  (`v5.2.0`-tagged, on v6.6.0). Surfaced as out-of-scope in
  `ignored-tests/decisions.md`. Candidate for a separate
  retirement spec. Not this program's work.
- **`config.py` exclusion audit.** Listed as an undocumented
  omit in `coverage-exclusion-policy/`. If the per-module loop
  reaches it before that spec resolves, hand off to the
  exclusion policy spec rather than processing here.
- **Test-suite reduction for its own sake.** Out of scope per
  requirements.md non-goals.
