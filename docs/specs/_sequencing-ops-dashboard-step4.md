# Sequencing — Ops dashboard, "step 4" implementation phases

**Date:** 2026-05-16
**Source:** post-audit handoff from a multi-repo session (attune-rag Phase 2 ship → attune-ai dashboard audit). The session that produced this plan also: shipped attune-rag v0.1.19 (Phase 2 of v1.0 roadmap), closed out attune-rag Phase 3 (M5.3 verified against published 0.1.19), and ran a full audit of every "ops"/"dashboard"-named branch + spec in this repo.

**What was audited:** 16 local ops/dashboard branches (all already squash-merged → deleted), 6 dashboard-touching specs, 12 worktrees. Audit confirmed PR #364's `data.py` bug fix landed via commit `3ebeb0a9c` (line 829), and PR #388's Haiku summarizer was redone as #390 — no work actually lost.

**Why this doc exists:** The dashboard work has high spec-debt. Most phases of most ops specs are shipped, but the **last 10–20 % of each spec** is what makes the dashboard feel finished. Patrick wants to drive those tails to closure without re-doing work. Patrick is starting the next session in a fresh worktree; this doc is the orientation point.

---

## Critical context for the new session

1. **Do not re-do anything.** The audit verified each phase-state below by reading the spec's task table on `main`. If a phase shows "shipped," the commits are on `main` and the branch has been deleted. If you find a feat-branch with those keywords still around, audit it before assuming it's pending — it's almost certainly orphan or post-merge.
2. **Two unblocked specs are calendar-blocked, not work-blocked.** `ops-specs-features` Phase 4 needs a 2-week usage observation; `ops-security-hardening` Phase 5 needs a manual smoke run only Patrick can do. Neither is in this plan as primary scope — but Phase 1 below does pick up the security-hardening close-out because it's lightweight enough to bundle.
3. **One uncommitted artifact at session-handoff time:** [PR #407](https://github.com/Smart-AI-Memory/attune-ai/pull/407) flips `docs/specs/website-update-dashboard-and-fold/tasks.md` from `draft` → `approved`. Should merge cleanly; not load-bearing for this plan.
4. **The dashboard module:** `src/attune/ops/` — FastAPI server with `cli.py`, `server.py`, `routes/`, `runner.py`, `data.py`, `session_summarizer.py`, `sweep_results.py`, etc. The live dashboard at `http://127.0.0.1:8775/` is served by `python -m attune.ops`. Patrick keeps a worktree at `/private/tmp/attune-ops-view` for live preview.

---

## Phase ordering rationale

Smallest-first to build momentum and ship visible wins, with each phase scoped to ~one session. The four-bullet ordering from the audit summary is preserved:

1. **Phase 1 — ops-security-hardening P5–P6** (close the manual smoke + cleanup tail). Tiny scope, big "spec status flipped to complete" payoff.
2. **Phase 2 — ops-scope-picker-ia** (production implementation of an already-approved design). Small, contained, well-scoped.
3. **Phase 3 — discovery-sweep-ops-integration P3–P4** (Dashboard UI for sweep results). Frontend polish on a backend that's already in place.
4. **Phase 4 — ops-runner-tier2 P5–P6** (Structured recommendations + telemetry close-out). The largest phase; ride momentum from Phases 1–3.

Phases are independent — they touch different specs and different code paths. If one stalls, the others remain unblocked.

---

## Phase 1 — ops-security-hardening P5–P6 (manual smoke + close)

| Field | Value |
|---|---|
| Spec | [docs/specs/ops-security-hardening/](ops-security-hardening/) |
| Current status (per audit) | "complete (pending Phase 5 smoke)" — P1–P4 done |
| Remaining | P5 (manual verification, 6 tasks) + P6 (close, 4 tasks) = 10 task ticks |
| Branch | `chore/ops-security-hardening-close` |
| Estimated effort | 1–2 hours (mostly running steps + ticking boxes) |

### Scope

Read [docs/specs/ops-security-hardening/tasks.md](ops-security-hardening/tasks.md), Phase 5 and Phase 6 sections. Phase 5 is a manual smoke test of the four already-shipped pieces:

- Host header middleware (P1) — DNS rebinding block under a controlled bad-host request.
- Bounded subscriber queue (P2) — confirm bound is enforced under load.
- Run-view route observability (P3) — confirm logs surface the new fields.
- E2E output-replay test (P4) — confirm the test runs green on a fresh checkout.

Phase 6 is the "close" tail: ticking the final boxes, updating the spec status to `complete`, adding a CHANGELOG entry under `Fixed` / `Changed` / `Security` as the spec dictates.

### Acceptance

- Every P5 task box ticked with the verification artifact (curl output / log line / test name) recorded inline.
- Every P6 task box ticked.
- Spec status field at the top of `tasks.md` updated to `complete`.
- CHANGELOG entry in `[Unreleased]`.

### Dependencies / blockers

- Live dashboard must be running locally (`python -m attune.ops`).
- No code changes expected unless a smoke surfaces a real bug.

### Why first

This phase is the smallest by code surface but ships a visible result ("a spec is now complete"). It also exercises the dashboard end-to-end, which is a useful prelude to Phases 2–4.

---

## Phase 2 — ops-scope-picker-ia (implement the approved design)

| Field | Value |
|---|---|
| Spec | [docs/specs/ops-scope-picker-ia/](ops-scope-picker-ia/) |
| Current status (per audit) | "draft" — design fully resolved, **production implementation not started** |
| Remaining | ~5 files, ~100 LOC + ~50–60 tests |
| Branch | `feat/ops-scope-picker-ia-impl` |
| Estimated effort | 1 focused session |

### Scope

Per `requirements.md` and `design.md`:

- Storage model: **global localStorage** (not per-feature). Key name decided in design.md.
- First-load fallback chain (decided in spec):
  1. Use last-saved scope (localStorage).
  2. Else: alphabetically-first feature.
  3. Else: "All code" (newly-added option) as final fallback.
- Edge cases:
  - Project-wide remembered: pre-select on load.
  - Custom path saved literally; round-trip on reload.
  - Unmatched paths: fall back to step 2/3 of the chain, do NOT crash.
- Read-only behavior: localStorage write is opt-in to the user's action, not on every render.

Files likely touched (per design.md):

- `src/attune/ops/templates/*.html` — scope picker rendering.
- `src/attune/ops/routes/*.py` — passing through the selected scope.
- `src/attune/ops/static/js/scope-picker.js` (or equivalent client-side module).
- New tests under `tests/unit/ops/`.

### Acceptance

AC-1 through AC-6 from the spec, verbatim. Tests must cover each AC.

### Dependencies / blockers

None. Design is greenlit.

### Why second

Small, contained, no API design work needed — ideal warm-up for the new session. Builds frontend muscle that Phase 3 will lean on.

---

## Phase 3 — discovery-sweep-ops-integration P3–P4 (Dashboard UI)

| Field | Value |
|---|---|
| Spec | [docs/specs/discovery-sweep-ops-integration/](discovery-sweep-ops-integration/) |
| Current status (per audit) | "P0–P2B shipped; P3 pending" |
| Remaining | P3 (Dashboard UI: 6 tasks — chips + drill-in) + P4 (Documentation + sequencing: 3 tasks) |
| Branch | `feat/discovery-sweep-ops-phase3-ui` |
| Estimated effort | 1–2 sessions |

### Scope

Backend is already in place:

- Engine event_sink API (P1) — shipped.
- ATTUNE_DS stdout emission (P1b) — shipped.
- Sweep-results storage primitives (P2A) — shipped via PR #334.
- Daemon-side wiring + HTTP route gated by `ATTUNE_OPS_SWEEP_RESULTS=1` (P2B) — shipped.

Phase 3 is purely the dashboard UI:

- Chips on the relevant dashboard page showing per-source sweep counts / severity badges.
- Drill-in view from each chip to the JSON results for that scope.
- Empty-state handling when no results exist for a scope.

Phase 4 is the documentation pass and the cross-spec sequencing update — short close-out.

### Acceptance

Per the spec's P3 task list. Reviewer should be able to:
1. Launch the dashboard with `ATTUNE_OPS_SWEEP_RESULTS=1`.
2. Trigger a sweep (or load fixture results).
3. See chips render with the expected counts.
4. Drill into one chip and see the per-source results table render correctly.

### Dependencies / blockers

- Sweep results JSON files need to exist under the scope-keyed storage path for testing — pre-existing fixture set should cover this; if not, generate one.
- `ATTUNE_OPS_SWEEP_RESULTS=1` env gate must be enabled.

### Why third

Backend is done. This is visible polish that makes a half-shipped feature feel finished — high payoff/effort ratio.

---

## Phase 4 — ops-runner-tier2 P5–P6 (Structured recommendations + close)

| Field | Value |
|---|---|
| Spec | [docs/specs/ops-runner-tier2/](ops-runner-tier2/) |
| Current status (per audit) | "P1–P4 shipped; P5–P6 pending" |
| Remaining | P5 (Structured recommendations channel: 6 tasks) + P6 (Telemetry + close: 4 tasks) |
| Branch | `feat/ops-runner-tier2-phase5-structured-recs` |
| Estimated effort | 2–3 sessions |

### Scope

P1–P4 already shipped (via PRs #236, #239, #249, #324):

- Workflow `--path` capability audit (P1).
- Scope picker — feature + custom path (P2).
- Persistence + run history (P3).
- Workflow-name pills become chainable buttons (P4).

P5 — Structured recommendation channel:

- Define the recommendation payload shape (JSON contract).
- Server-side: workflows emit recommendations into the channel.
- Client-side: surface them in the run-view UI.
- 6 specific tasks per the spec.

P6 — Telemetry + close:

- Telemetry on usage of P3 / P4 / P5 features.
- Tick the close-out boxes.
- Final CHANGELOG entry.

### Acceptance

US-1 through US-6 and C-1 through C-6 from the spec.

### Dependencies / blockers

- Phase 5 needs an API design decision before implementation. First session deliverable should be a short design note in the spec dir (`design-phase5.md` or appended to existing `design.md`) before writing code.

### Why last

Largest phase by code surface, requires upfront API design, builds on patterns established in earlier phases.

---

## Handoff for the new session

### Worktree setup

```bash
cd /Users/patrickroebuck/attune-ai
# Pick the phase to work on. Phase 1 example:
git fetch origin
git worktree add .claude/worktrees/ops-security-hardening-close \
  -b chore/ops-security-hardening-close \
  origin/main
cd .claude/worktrees/ops-security-hardening-close
```

Per-phase worktrees keep the work isolated and let you bail on a phase without affecting the others.

### First steps in the new session

1. Read this doc.
2. Read the chosen phase's spec dir (linked above).
3. Re-state the phase's scope + acceptance criteria back to Patrick in 5–10 lines.
4. Propose a detailed task breakdown with sizing.
5. Get Patrick's nod.
6. Start work.

### Helpful state pointers

- **Latest main**: see `git log main --oneline -5` for context. As of this writing the tip is `4e6ac940 feat(ops): /specs "Ready to close?" completion-candidates section (#400)`.
- **Live dashboard worktree** (Patrick's): `/private/tmp/attune-ops-view`.
- **Audit (this session's work)**: the conversation that produced this plan also opened [PR #407](https://github.com/Smart-AI-Memory/attune-ai/pull/407) (one-line spec status flip) and pruned 16 merged ops/dashboard branches. Both are safe context, not actions to repeat.

### Things NOT in scope (deferred)

- `ops-specs-features` Phase 4 — telemetry-driven decision after 2 weeks of usage.
- `website-update-dashboard-and-fold` — separate spec, separate scope (website work, not dashboard work).
- `ops-sessions` follow-ups — landed via #390 + follow-ups; no immediate dashboard implication.
- Folding `attune-gui` back into `attune-ai` — separate spec, much larger scope.
- v7.0 release planning — gated on the four phases above plus more.

---

## Open questions for Patrick before starting Phase 1

Pose these in the new session's first turn:

1. Is Phase 1 still the right warm-up, or should the new session jump straight to Phase 2 / 3?
2. Should per-phase PRs target `main` directly, or stack onto a release branch?
3. For Phase 4's API design note — separate PR before implementation, or bundle?

Document version: 1.0 (initial handoff)
