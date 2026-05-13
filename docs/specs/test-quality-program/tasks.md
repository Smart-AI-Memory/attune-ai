# Tasks: Test Quality Program
**Status:** approved
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
