# Tasks: Integration Coverage Program
**Status:** parked (2026-07-13) — Phases 0–1 + task 7 shipped (#703/#704/#727 revival + CI job, surface inventory #768); auth job live on weekly cadence (#952, green 2026-07-13); remaining: tasks 8–10 (per-surface round-trips, nightly wiring, gate-forward rule) + no-auth job required-check promotion — no activity since 2026-06-11.
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

## Phase 2 — Live receipts per surface (added 2026-06-11)

**Born:** discipline-review chat, 2026-06-11 (improvement #3 of
6). Generalize the nightly-auth pattern: the most expensive
recurring bug class is mocked-green / live-broken — AMS behaviors
invisible to 100+ green mocked tests, the judge shim `max_turns`
trap, and (found 2026-06-11 during wrf T8) MCP workflow handlers
calling `.get()` on a `final_output` that had been a STRING since
the SDK migration: crash-or-dead for months, 16k tests silent.
The "one non-mocked round-trip per external-dep feature" lesson
exists but is not enforced as a gate; `integration-auth.yml`
proves the budget-capped nightly shape works.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 7 | **2.1 Surface inventory.** Enumerate externally-wired surfaces (MCP tools, dashboard run-path, CLI render-path, memory backends, RAG pipeline, plugin hooks) and for each record whether ANY non-mocked exercise exists (nightly, integration suite, or dogfood receipt). Output: a coverage table in this dir. | docs | **done** (2026-06-11) | Shipped: [surface-inventory.md](surface-inventory.md). Known-worst confirmed with nuance: the 20 memory/help/session MCP tools DO get real dispatch-chain exercise; the 21 workflow MCP tools have nothing past validation, no MCP tool has LIVE exercise, and the stdio handshake has zero automated coverage. attune_redis's 16 live AMS tests never run in CI. Gap ranking in the doc feeds task 8. |
| 8 | **2.2 One round-trip per uncovered surface.** For each gap, the smallest live exercise: e.g. an MCP smoke that calls each workflow tool against a tiny fixture and asserts response SHAPE (not content); a dashboard run-path probe; a CLI render probe on a recorded result. Budget-capped like the auth job; skip-gated locally. | tests | todo | Shape assertions, not content — these catch the str-vs-dict class, not flaky LLM variance. |
| 9 | **2.3 Wire to the nightly.** Extend `integration-auth.yml` (or a sibling keyless job for non-LLM surfaces) so the round-trips run on schedule, with the run-triage doc pattern for failures. | ci | todo | Keyless surfaces (MCP shape, CLI render) can run per-PR cheaply; only LLM-touching probes stay nightly. |
| 10 | **2.4 Gate the rule forward.** New external-dep feature ⇒ its PR includes one non-mocked round-trip, enforced as /spec + review guidance (advisory, per enforcement-vs-documentation), with the surface inventory as the audit trail. | docs | todo | Advisory by design — the hook can't see "external-dep feature" mechanically. |

---

## Done-state

This spec has two valid terminal states:

- **active** → after task #6 chooses (a). Phase 1+ is then
  designed and executed; cycles run under the new mechanism.
- **closed (out-of-scope)** → after task #6 chooses (b). The
  decision rationale stays in `decisions.md` for future
  reference, so when the question resurfaces the next reader
  can see why a framework wasn't built.
