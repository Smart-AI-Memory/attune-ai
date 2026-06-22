# Decisions: Dashboard Pending-Writes Journal

**Status:** approved (2026-05-25)

Append-only log. New decisions go at the bottom with date +
context. Earlier decisions are not edited (they're history,
not live config).

---

## D1 — 2026-05-25 — Journal as source of truth, not auto-commit

**Context:** Six solution approaches considered in scoping
discussion (full enumeration in design.md). Auto-commit on
heartbeat was attractive but introduces too many failure
modes.

**Decision:** Journal (append-only JSONL) is the source of
truth. Humans remain in the commit loop. The journal makes
the loop frictionless; it doesn't replace the loop.

**Rationale:**

- Auto-commit needs git permissions on the dashboard process
  (GPG keys, SSH agent forwarding, branch policy) — operational
  burden
- Auto-commit creates a discoverability problem: small commits
  on side branches that humans never see
- Race conditions: dashboard PID 35492 commits while session
  PID 12345 is doing manual git work
- Branch cleanup burden grows linearly with usage
- Cleaner contract: dashboard records, human decides, agent
  facilitates

**Counter-arguments considered:**

- "But humans forget to commit" — yes; the surfacing layer
  (UI chip + session-start hook) makes forgetting hard. That's
  the right place to address forgetting, not auto-commit.

---

## D2 — 2026-05-25 — Layered, not monolithic

**Context:** Each damage mode (loss, confusion, drift,
time-cost) maps to a different consumer (current-session
user, fresh-session agent, downstream tooling).

**Decision:** Three layers — journal (source of truth) → API
(contract) → consumers (UI chip, session-start hook, anyone
else who wants the signal).

**Rationale:** Each layer addresses a distinct concern with
a distinct surface. Coupling them loses flexibility. The
journal serves any consumer; the API formalizes the contract;
each consumer slices the API output per its needs.

---

## D3 — 2026-05-25 — API returns enriched-not-filtered

**Context:** Multiple consumers will want to filter the
journal differently (UI chip wants `uncommitted_count`;
session-start hook wants entries where `is_committed=false`;
an auditor wants `matches_journal=false`).

**Decision:** API returns ALL journal entries enriched with
computed fields (`is_committed`, `matches_journal`,
`dashboard_still_running`, `current_disk_sha256`). Consumers
filter as needed.

**Rationale:** Better to enrich once at the API layer and let
consumers slice than to re-implement git-status checks in
every consumer. Reduces duplication and makes the contract
inspectable.

**Tradeoff:** Larger response payload. Mitigation: the
journal is small (<10KB even after months of typical usage);
not a concern.

---

## D4 — 2026-05-25 — Phase split: journal+API today, UI+hook later

**Context:** Original plan was "spec + implementation today."
Patrick approved phase split during scoping
([feedback exchange](../../../docs/COVERAGE_BUG_LOG.md) —
recommendation lead with Phase 1 only).

**Decision:** Phase 1 (this spec, this session) ships journal
+ API + tests + spec status setter wire-in. Phase 2 (UI chip
+ review page) and Phase 3 (session-start hook + CLI
subcommand) are scoped here but ship in future sessions.

**Rationale:** Phase 1 is independently shippable: the
journal becomes durable infrastructure; the API becomes a
queryable contract. Phase 2 and Phase 3 are independently
useful additions, not blocked on each other. The Phase 1
slice gives us the worked example for the article without
exhausting today's energy budget.

**Acceptance for Phase 1:** journal writes happen on the
spec-status setter; API returns enriched entries; tests
cover both; manual smoke test passes (edit a spec status in
the dashboard, see the entry appear via curl on the API,
commit the file, see `is_committed=true` on next API call).

---

## D5 — 2026-05-25 — Journal failures must not block writes

**Context:** If the journal append fails (disk full, no
permission to `~/.attune/ops/`, etc.), should the actual
dashboard write fail or proceed?

**Decision:** Proceed. The journal append is wrapped in
try/except; failures log WARNING; the actual write
endpoint returns success per its normal contract.

**Rationale:** The journal is observability infrastructure,
not a precondition for correctness. Blocking real user work
on infrastructure failure is the wrong tradeoff. The
WARNING log surfaces the journal failure for separate
investigation.

**Counter-argument considered:** "But then we lose
provenance." Yes — for that one write. The git history
(once committed) is still the authoritative record. The
journal is a convenience layer.

---

## D6 — 2026-05-25 — In-scope endpoints: spec status setter only (Phase 1)

**Context:** Multiple dashboard endpoints potentially mutate
the working tree. Should Phase 1 instrument all of them?

**Decision:** Phase 1 instruments the spec-status setter
endpoint only (`PUT /api/cowork/specs/{feature}/{phase}/status`).
Other mutating endpoints (manifest edits, feature toggles,
future surfaces) are NOT instrumented in Phase 1.

**Rationale:**

- The spec-status setter is the highest-traffic mutating
  endpoint; today's evidence (10 unstaged edits) is entirely
  from this surface
- Instrumenting all endpoints at once requires auditing the
  whole dashboard route surface — scope creep
- Adding instrumentation to a new endpoint is a single
  `pending_writes.append_entry(...)` call — easy to extend
  per-endpoint as the need surfaces

**Future:** A follow-up task to audit all mutating endpoints
and instrument them. Best done as a sweep after Phase 1
ships.

---

## Notes on the spec itself as worked example

This spec was produced during a session where Patrick said
"we should try to find a proactive solution to this problem...
it would make a good example" — meaning the spec design and
implementation work would itself become article material for
§6 (Multi-agent Coordination) of the
[Discipline of Agent Collaboration article](../../process/COLLABORATION_DISCIPLINE_outline.md).

The discipline-in-action visible in this spec:

- **Problem named**: dashboard live-writes becoming silent
  debt — observed today, named as a class of bug
- **Solution space enumerated**: 6 candidates with
  pros/cons before picking
- **Recommendation made with reasoning**: layered approach,
  with each layer addressing a distinct damage mode
- **Phase split proposed**: don't try to ship the whole thing
  in one session
- **Decisions captured here as durable**: future sessions
  see the choices and their rationales, not just the
  outcomes
- **Article cross-reference**: this spec is intentionally a
  worked example, not just utility infrastructure

That's the article's central thesis demonstrated by the work
of designing the article: discipline producing both the
artifact AND the example of the discipline producing the
artifact.
