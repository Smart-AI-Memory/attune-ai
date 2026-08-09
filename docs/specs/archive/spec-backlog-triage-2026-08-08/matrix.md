# Spec Backlog Triage — 2026-08-08

> Fourth pass, following 2026-06-04, 2026-06-20, 2026-06-24 (and
> the 2026-07-14 delta in the 06-24 dir). Scope per the session
> contract: classify every in-flight dir under `docs/specs/`
> (ship-shipped-unflipped / genuinely-active / parked-needs-trigger
> / dead-close), fix stale status lines in ONE docs PR, then
> advance one genuinely-active spec one phase. Method: status-line
> extraction across all dirs, then four parallel read-only
> verification lanes that grepped each suspect's named
> files/symbols/PRs against the current tree (the code is the
> contract; spec text is a hypothesis). Status flips are executed
> in this PR; ARCHIVE-MOVE dispositions are recommendations —
> nothing moves without Patrick's sign-off.

## Summary

51 live dirs (redis-config-truth excluded — its close-out flip is
in-flight in #1995). 16 suspects were tree-verified; 8 were
shipped-unflipped, and every stale line is fixed in this PR.

| Bucket | Count |
|---|---|
| Terminal, status already accurate | 20 |
| Shipped-unflipped → FLIPPED in this PR | 8 |
| Status refreshed (token kept, annotation stale) | 5 |
| Parked (4 newly flipped + 6 already accurate) | 10 |
| Genuinely active | 5 |
| Living | 3 |
| Dead-close | 0 |

## Flipped in this PR (verified against the tree)

| Spec | Was | Now | Evidence |
|---|---|---|---|
| attune-author-consolidation | approved, "remaining: T2–T5" | complete (2026-07-27) | T3 #1574, T2 #1586/#1699, T4 executed in pyproject 2026-07-27; residual no-op import noted |
| cross-provider-session-handoff | APPROVED, "staged post-07-27" | complete (2026-07-28) | T1+T2 #1605, T3 #1694, T4 #1700; R6 closed PASS live |
| cross-review (tasks.md) | APPROVED, execution second | complete; R5 ledger stays living | T1–T4 shipped; ledger accruing through 2026-08-08 |
| outcome-first-fix | active, "Task 3 awaiting go" | shipped (2026-08-02) | Tasks 0–4 all merged (#1806/#1808/#1811/#1818/#1824); Task 4 log bullet backfilled |
| roundtable-producing-team | active (2026-07-18) | shipped (2026-07-29) | P1–P4 landed (#1462/#1464/#1466); re-run queue closed |
| roundtable-triage | approved / active | shipped; decisions living | TA-1..8 landed (#1511/#1515/#1517/#1734); live 07-28 fire receipt |
| discovery-sweep-rich-surface | draft (2026-06-28) | parked + trigger | Phase 1 SHIPPED #1148/#1151 two days after "draft"; Phase 2 unbuilt |
| local-first-reports | active | parked + trigger | Phase 1 #1823 done; Phase 2 explicitly unauthorized |
| agent-work-report | active/approved-waiting | parked + trigger | zero artifacts in tree; 11.2.0-cut wait long discharged |
| memory-claim-verification | draft | parked + trigger | D6 gate cleared 2026-07-28; ref-binding table now convenable |
| fable-premium-tier | parked, trigger 07-28 | active — Task 9 OVERDUE | trigger elapsed; premium-price callout absent from CHANGELOG, tier docs say premium=Opus |

## Annotation refreshes (token unchanged)

- **claim-drift-gates** — G4's "held #1561" MERGED (`82fa8f780`);
  only G3 remains (blocked on absent hook-timeout-budgets spec).
  Follow-ups: G4(c) still `continue-on-error: true` past its
  ~08-04 promotion check; website-only-PR guard gap unruled.
- **usage-signals** — US-5 satisfied by two chair rulings
  (#1836, #1930); remaining: US-3 outreach close-out (timebox
  expired ~08-03; record UNRESOLVED) + US-7 done-when closure.
- **elicitation-form-surface** — v2 was already shipped BEFORE its
  07-14 "recommit" (#1131/#1132); shipped through V7 (#1945).
  OPEN: V6 (MCP Apps) needs an approve-or-drop ruling.
- **feature-lead-governance** — P1 active mode; open items are
  D14 register + D13c one-pager, tasks stay draft by design.
- **docs-outbox** — AC-2 closed 2026-08-07 (was "pending chip
  click"); R3 lint + R4 chip + launchd install carried open.

## Structural fixes in this PR

- **product-direction-review** — had NO canonical phase file, so
  it was invisible to the lifecycle detector and status-line gate.
  Added `decisions.md` (living) with the round log.
- **docs-outbox / memory-claim-verification decisions.md** — no
  file-level status line; detector read D1's inline status. Added
  file-level lines.
- **docs-wiring-audit** — five in-body "not started" phase footers
  contradicted the shipped top-of-file status; reconciled.

## Status-accurate (no change)

Terminal: advanced-debugging-plugin, agent-round-table,
antigravity-adapter, broad-except-ratchet,
cross-provider-collaboration-projector,
cross-provider-memory-transport, diagramkit, docs-wiring-audit,
gemini-projector, memory-feedback-signal, memory-recall-eval,
post-commit-help-check-only, run-record-corpus,
sdk-teardown-exit-guard, self-healing-traps, spec-lifecycle-gates,
test-discipline-controls, trap-battery, windows-exit139-segfault,
spec-status-self-truthing-era archives.

Parked/draft with valid triggers: exit-code-honesty-guard (awaiting
chair review), feature-page-scaffolder, hooks-install (unruled
candidate — do not implement from draft), integration-coverage,
ops-dashboard-polish, socratic-ambiguity-calibration,
telemetry-models-layering, widget-kernel-family (awaiting chair),
workflow-intake-forms (RULE OF THREE trigger).

Living: subsystem-value-gate, test-quality-program,
product-direction-review (newly anchored).

Active: memory-security-hardening, memory-status-integrity,
docs-outbox, feature-lead-governance, claim-drift-gates (G3),
usage-signals (US-3/US-7 close-out), fable-premium-tier (Task 9).

Unverified this pass: pipeline-learner (approved, gated on RR-1
corpus readiness — VERIFY corpus readiness before acting).

## Follow-up debt surfaced by the sweep (not executed here)

1. **fable-premium-tier Task 9** — premium-price callout missing
   from CHANGELOG; `tier-routing.md` help says premium = Opus. A 2×
   price change reached released builds with stale user docs.
2. **Status-line gate coverage hole** — a dir with `.md` content
   but no `_PHASE_FILES` member is invisible to the corpus sweep
   (how product-direction-review hid for 8 weeks).
3. **attune-author residual** —
   `plugins/attune-author/hooks/help_post_commit.py` imports
   `attune_author.maintenance.run_hook` (never absorbed); permanent
   no-op under its ImportError guard.
4. **V6 elicitation (MCP Apps)** — approve-or-drop ruling owed;
   freeze lapsed, predecessor V7 shipped.
5. **US-3 outreach close-out** — record external usage UNRESOLVED
   per the requirement; timebox expired.
6. **claim-drift G4(c) promotion** — `contributing-smoke.yml`
   still advisory past its ~2026-08-04 promotion check.
7. **memory-claim-verification table sitting** — ref-binding fork
   convenable since 2026-07-28.

## Spec-candidates (from the 11.5.0 self-review — NOT authored
this session, per the effort cap)

Structural refactor items queued in
`docs/reports/post-release-self-review-11.5.0.md`: core→ops
dependency, BaseWorkflow name clash, Empathy vestiges, god files.
Plus the two unruled 07-30 candidates (lane-yield 90% cap;
hooks-install) — pointed at their docs, not implemented.

## Archive-move recommendations (await Patrick sign-off)

The 20 terminal dirs above plus the 8 newly flipped terminal specs
are archive-eligible (`git mv` into `docs/specs/archive/`).
Recommended batch: attune-author-consolidation,
cross-provider-session-handoff, outcome-first-fix,
roundtable-producing-team, plus the 20 long-terminal dirs. Keep
top-level despite terminal status: cross-review (living R5
ledger), roundtable-triage (living carrier), diagramkit (recent
close, memory anchor). Nothing moves in this PR.
