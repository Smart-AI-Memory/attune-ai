# Tasks: Integration Coverage Program
**Status:** in progress (2026-06-09) — Phase 0 complete (see [phase0-findings.md](phase0-findings.md)): decision **GO, reframed** — revive the existing 351-test suite, don't build new infra. Phase 1 **complete**: rot pruned (#703), green subset wired to CI (#704), 16-failure backlog cleared + job promoted to the full no-auth suite (295 passed / 0 failed — see [phase1-triage.md](phase1-triage.md)). Nightly auth job shipped: `integration-auth.yml` (schedule + workflow_dispatch) runs the auth bucket — 6 `*_with_auth` files + 6 env-gated discovery_sweep files + `test_llm_integration.py` (33 tests) — with the real `ANTHROPIC_API_KEY` secret and `ATTUNE_MAX_BUDGET_USD=10`. First auth-bucket dispatch triaged in [auth-run-triage.md](auth-run-triage.md): repo `ANTHROPIC_API_KEY` secret invalid (owner fix), all 6 `*_with_auth` files rot (rewrite-or-retire pass pending), discovery_sweep passes suspicious until a valid key. Remaining: promote the no-auth CI job to a required check after a few weeks green.
---

## Phase 0 — Audit before design

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Spec approval — merge requirements.md + tasks.md. | spec | todo | This PR. |
| 2 | **0.1 Inventory existing integration tests.** Walk `tests/integration/` and produce a one-page summary at `docs/specs/integration-coverage/inventory.md`: file count, total LOC, last-modified-month histogram, fraction `xfail`-gated, fraction `importorskip`-gated, what subsystems are covered (workflows? memory? plugins? CLI?). | docs | todo | Stdlib-only walker. Don't run the tests yet — just count. |
| 3 | **0.2a Classify 30 days of bug findings.** Parse the last ~30 days of entries from `docs/COVERAGE_BUG_LOG.md`, `CHANGELOG.md` Internal sections, `.claude/CLAUDE.md` Lessons Learned additions, and merged-PR titles. For each entry assign one of: `unit-catchable`, `integration-catchable`, `process-catchable`, `uncatchable-cheaply`. Output: `docs/specs/integration-coverage/bug_catchability.csv` with columns `date, source, summary, category, rationale`. | docs + script | todo | First pass is manual; if the volume is high (>50 entries), write a quick script to extract structured metadata from the markdown sources. |
| 4 | **0.2b Distribution summary.** Append a one-paragraph summary to `decisions.md` reporting the category distribution and naming the top three specific bugs from each category. | decisions.md | todo | The shape of the distribution is the input to task #5. |
| 5 | **0.3 Cost model for top-impact mechanism.** Based on the distribution from #4, identify the one mechanism with highest impact-per-effort ratio. Estimate three costs: (a) initial setup hours, (b) per-cycle CI minute cost, (c) per-bug-find expected payoff. Write to `decisions.md`. | decisions.md | todo | Single page. If the math obviously doesn't work (e.g., uncatchable-cheaply dominates), this is where this spec closes. |
| 6 | **Phase 0 close decision.** Either: (a) mark Phase 0 done + open Phase 1 with the mechanism design as a follow-up commit, OR (b) close this spec as "no scalable mechanism justified" and document why. | spec | todo | The decision is binary by design — Phase 0 either greenlights or kills. |

---

## Phase 1+ — Deferred until Phase 0 lands

Design and implementation tasks are intentionally **not
specified here**. They will be added in a follow-up commit
after Phase 0's data justifies a specific mechanism. This
keeps the spec honest to the lesson:

> A spec's measurable premise should be probed in Phase 0
> BEFORE implementation. (CLAUDE.md, ~line 3260)

Pre-committing Phase 1 design before Phase 0 data lands is
exactly the trap the umbrella `test-quality-program` spec
also avoided.

---

## Done-state

This spec has two valid terminal states:

- **active** → after task #6 chooses (a). Phase 1+ is then
  designed and executed; cycles run under the new mechanism.
- **closed (out-of-scope)** → after task #6 chooses (b). The
  decision rationale stays in `decisions.md` for future
  reference, so when the question resurfaces the next reader
  can see why a framework wasn't built.
