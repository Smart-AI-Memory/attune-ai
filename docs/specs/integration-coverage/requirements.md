# Spec: Integration Coverage Program
**Status:** parked (2026-07-13; re-affirmed 2026-07-19, chair
ruling T1 of `q-briefing-triage-001`) · Resume-Trigger: evergreen
(no external clock) — Phases 0–1 + task 7 shipped (see
decisions.md); remaining: tasks 8–10
**Created**: 2026-05-13
**Origin**: Complement to the `test-quality-program` umbrella
([requirements.md](../test-quality-program/requirements.md)).
The per-module coverage loop has known structural blind spots
— bugs that require multiple modules wired together, real LLM
behavior, concurrency, or external-dep changes don't surface
through single-module unit tests. This spec frames the
question of what fills those gaps, with a deliberate **Phase 0
audit before design** to avoid pre-committing to the wrong
mechanism.

---

## Phase 1: Requirements

### Why

The test-quality-program is shipping cleanly (14 modules
processed 2026-05-12, 2 real bugs surfaced, 3 dead-code
candidates flagged), but its design is fundamentally
single-module-with-mocked-boundaries. By construction it
cannot catch:

1. **Integration bugs across modules.** Two units that each
   pass their own unit tests can fail when wired together.
   The "SDK adapter swallows subagent findings" lesson in
   `.claude/CLAUDE.md` (later proven wrong but the original
   misdiagnosis stood for weeks) is exactly this shape — the
   adapter's individual tests passed, the workflow's
   individual tests passed, the bug was in their interaction
   under real SDK behavior.

2. **Real LLM behavior.** Every SDK shell test mocks
   `claude_agent_sdk.query()`. The actual agent loop —
   subagent spawning, message stream collection, budget
   enforcement, max_turns cutoff — is never exercised in CI.
   Production bugs in this layer surface only via dogfooding
   (already documented as a lesson in CLAUDE.md:
   "dogfood runs catch bugs unit tests miss").

3. **Concurrency / race conditions.** The Windows xdist
   memory failures resolved by PR #260 were not surfaced by
   coverage cycles. Single-process pytest with mocked I/O
   cannot model multi-worker contention, socket pressure,
   or filesystem race conditions.

4. **Tests with wrong assertions.** Coverage measures
   execution, not correctness. A test that exercises a code
   path with `assert result == "wrong"` still hits the
   coverage counter. Mutation testing or property-based
   testing addresses this; line coverage does not.

5. **Untouched modules.** The rubric is opportunistic
   top-down by score; ~30% of the codebase has never been
   picked. Bug Class 2 finds (dead code) suggest a lot more
   rot is sitting where the rubric hasn't looked. The
   sibling Phase 4 task in `test-quality-program/tasks.md`
   addresses the rubric refinement (inbound-import signal),
   but doesn't change the fundamentally per-module shape.

6. **External dep changes.** `python-frontmatter` in
   `[author]` not `[dev]` was a real bug found by accident
   when the rubric pointed at `cli_commands/help_commands.py`
   (PR #287). Other deps in `[author]`, `[memory]`, etc.
   could have similar gates that won't surface until the
   rubric drifts that way.

7. **UX bugs, performance regressions, security
   boundaries.** Out of scope for unit tests by nature.

8. **Process-shaped bugs.** I admin-merged PR #279 tonight
   without reading the `build` check's failure carefully
   (Vercel-noise blindness), breaking main's docs build. No
   amount of unit testing catches "human skims the failure
   list."

### What this spec is NOT

- **Not a replacement for the test-quality-program.** Per-module
  coverage work continues as the steady-state cycle; this spec
  is a complement, not a substitute.
- **Not a commitment to building a framework.** Phase 0
  explicitly defers framework design until the data on actual
  failure modes lands. The framework may end up being existing
  tools (`tests/integration/`, dogfooding scripts, fuzz
  harnesses) reorganized, not new infrastructure.
- **Not a 100% integration coverage target.** Integration
  testing has steep marginal cost (real LLM API calls,
  real Redis, real filesystems). The right ratio of unit vs
  integration is data-driven — see Phase 0.

### Phase 0 — Audit before design

The CLAUDE.md lesson "A spec's measurable premise should be
probed in Phase 0 BEFORE implementation, even when the probe
costs real API budget" applies directly. Before designing a
framework, measure:

**0.1 — Inventory existing integration tests.** What lives in
`tests/integration/` today? When was it last run? Does it pass?
What fraction of that subtree is currently `xfail` or
`importorskip`-gated? Output: a single page summarizing
present state.

**0.2 — Classify the last 30 days of bug findings by
catchability.**
Sources: `docs/COVERAGE_BUG_LOG.md`, `CHANGELOG.md`
"Internal" entries, `.claude/CLAUDE.md "Lessons Learned"`
additions, recent CI-break root causes from PR history.
For each entry, classify:

- **unit-catchable** — a per-module unit test would have
  caught it (the existing program handles these).
- **integration-catchable** — required multiple modules
  wired together, real LLM behavior, real I/O, or
  multi-process state.
- **process-catchable** — required a procedural change
  (review checklist, CI gate, branch protection) rather
  than a test.
- **uncatchable-cheaply** — would require expensive
  infrastructure (production traffic replay, fuzz time
  budget, etc.) disproportionate to the impact.

Output: a CSV at
`docs/specs/integration-coverage/bug_catchability.csv` plus a
one-paragraph summary of the distribution.

**0.3 — Cost model for the most-promising mechanism.** Based
on 0.2's distribution, pick the *one* mechanism with the
highest impact-per-effort ratio and estimate its costs:

- If integration-catchable dominates: cost of a fixture
  framework + recorded LLM responses + CI minute budget.
- If process-catchable dominates: cost of a PR-template
  review-checklist update + admin-merge guardrail script.
- If uncatchable-cheaply dominates: this spec closes as
  "no scalable mechanism justified."

Output: a `decisions.md` entry. If costs are clearly
disproportionate to the catchability distribution, this spec
closes here. Otherwise, **Phase 1+ are designed in a
follow-up commit, not committed in this spec**.

### Success criteria

- Phase 0 audit ships within ~3 hours of focused work.
- The decision-doc output is sharp enough that "design a
  framework" vs "close as out-of-scope" is unambiguous.
- The audit is reusable — next time the question recurs,
  the script that classified the 30-day window can re-run
  against a fresh time range without manual re-classification.

### Non-goals

- **Mutation testing.** Out of scope unless Phase 0 finds
  that "tests with wrong assertions" dominates the
  classification — unlikely.
- **Fuzz testing.** Out of scope unless Phase 0 finds
  uncatchable-cheaply bugs that fuzzing specifically would
  catch — possible for security-boundary code, but a
  separate spec.
- **Replacing the test-quality-program.** This spec is a
  complement.

### Out-of-scope follow-ups (flagged, not committed)

- **Process changes that emerged tonight.** The
  Vercel-blindness admin-merge regression on PR #279 →
  docs build break is a process bug. Phase 0's
  classification will surface whether process-shaped bugs
  dominate; if so, that's a separate spec (something like
  `pr-merge-checklist`) rather than this one.
- **Test framework consolidation.** If Phase 0 finds the
  existing `tests/integration/` subtree is mostly dead, the
  right move is a sibling retirement spec, not building
  more on top.
