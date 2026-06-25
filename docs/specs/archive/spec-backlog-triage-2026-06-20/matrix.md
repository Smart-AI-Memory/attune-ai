# Spec Backlog Triage — 2026-06-20 (delta pass)

> A delta value-judgment pass over `docs/specs/`, building on the
> 2026-06-04 triage ([../archive/spec-backlog-triage-2026-06-04/matrix.md](../archive/spec-backlog-triage-2026-06-04/matrix.md))
> rather than redoing it. Goal per spec: **KEEP** (real remaining
> value + clear next action), **ARCHIVE** (complete/concluded —
> preserve in history), **MERGE** (fold into a sibling), **KILL**
> (premise invalid / infra-for-its-own-sake), or **VERIFY** (status
> drift between files — resolve before deciding).
>
> All calls are **recommendations**. Patrick makes the final calls;
> nothing is deleted or archived without sign-off.

---

## Context: what changed since 2026-06-04

The prior pass cut the backlog **69 → 41** (28 archived, 1 merged).
Sixteen days on, the active count is back to **48** directories — a
mix of new specs and KEEP-items from the prior pass that have since
**shipped** but were never moved to `archive/`. This pass closes that
gap.

Status was read from each spec's terminal status line. A notable
finding: several specs carry **conflicting status lines across files
within one directory** (e.g. `requirements.md` says "approved" while a
`decisions.md` or later file says "phase 5 complete"). Those are
marked **VERIFY** — the `spec-status-self-truthing` derivation is not
fully holding for multi-file specs.

---

## Summary

| Disposition | Count | Status |
|---|---|---|
| ARCHIVE (complete — shipped since prior pass) | 18 | ✅ executed |
| VERIFY → ARCHIVE (reconciled to complete) | 3 | ✅ executed |
| VERIFY → KEEP (genuinely still open) | 3 | active |
| MERGE → archive (carryover fold, executed) | 1 | ✅ executed |
| KEEP — active, real value, clear next action | 15 | active |
| KEEP — draft/idea stage (commit or KILL — Patrick's call) | 7 | active |
| KEEP — living document | 1 | active |
| **Total active dirs (before)** | **48** | |

**Executed: 22 directories moved to `archive/`** (18 + 3 VERIFY + the
prior triage card + 1 fold). Active backlog **48 → 27**. Remaining
judgment call: the **7 drafts** (commit-or-kill, needs Patrick).

---

## ARCHIVE — complete, shipped since the prior pass

Terminal status line reads `complete`/`retired`, matching known
merged PRs. Move the spec record to `docs/specs/archive/`; no work
remains.

| Spec | Evidence (status line) |
|---|---|
| agent-surface-parallelism-evaluation | RETIRED 2026-05-29 — orchestrator already ships in `deep_review`. |
| anthropic-cost-integration | complete 2026-06-09 — `ops/anthropic_cost*` shipped. |
| attune-verify | complete 2026-06-09 — all build tasks done. |
| ci-matrix-right-sizing | complete — D1–D3 decided, slim matrix implemented (#937). |
| consolidate-claude-md-lessons | complete 2026-06-06 (#646 + #647). |
| doc-fiction-cleanup | complete — cleanup executed. |
| docs-completeness-audit | complete 2026-06-09 (#714–#717). |
| drift-guards-to-generators | complete 2026-06-19 — "Done when" met (conversions 1 + 2, #938). |
| ops-help-page | complete — `ops/routes/help.py` + `ops/help_data.py` shipped. |
| ops-session-discovery-cli | complete (recommendation: DEFER) — conclusion reached. |
| pattern-review-queue | complete 2026-06-09 — R1–R5 + R8 shipped (#689). |
| polish-cost-reduction | complete 2026-06-10 — both levers shipped. |
| public-help-site | complete 2026-06-09 — `attune-ai-dev/build_help.py` shipped. |
| sdk-subprocess-isolation | complete 2026-06-10 — all four phases shipped. |
| spec-status-self-truthing | complete — shipped in #567. |
| workflow-path-arg-unification | complete — all 5 target workflows accept `path`. |
| workflow-result-formatting | complete 2026-06-12 — `WorkflowReport` shipped. |
| spec-backlog-triage-2026-06-04 | The prior triage itself — decisions executed (see its §Decisions). Archive the card. |

---

## VERIFY — intra-directory status drift (RESOLVED)

These showed conflicting status across files. Reconciled against each
spec's canonical `requirements.md`/`tasks.md` line:

| Spec | Drift | Resolution |
|---|---|---|
| bulletin-curator | decisions "in progress" vs requirements + tasks "complete, shipped v8.0.0 (#657)" | **ARCHIVED** — canonical req+tasks complete; only optional Task 4.1 remained. |
| dashboard-pending-writes-journal | decisions "approved" vs requirements + design "complete (Phase 1 #469/#492)" | **ARCHIVED** — Phase 1 shipped; no further phase. |
| windows-xdist-flakes | requirements "draft" vs design "complete (v1)" | **ARCHIVED** — v1 done; reopen only if flakes resurface. |
| auto-merge-safe-class | req/design/decisions "approved" vs **tasks.md "in progress"** | **KEPT** — canonical tasks.md is open; don't archive mid-flight. (Memory says working e2e, but tasks aren't closed.) |
| usage-signals | requirements "approved" vs decisions "Phase 2b implemented — pending deploy/migration" | **KEPT** — in-flight; deploy now live (204 verified today) but client ships next PyPI release. Status line should be refreshed. |
| sibling-package-pre-commit | "approved" / "phase 0 complete" / "Phase 1+ pending" | **KEPT** — PR #940 (Phase 5 complete) merged to main *after* this worktree's base; don't archive from stale state. Reconcile after rebase. |

---

## MERGE — carryover from the prior pass, still not executed

| Spec | Fold into | Note |
|---|---|---|
| ops-dashboard-qa-2026-05-14 | ops-dashboard-polish | The 2026-06-04 pass recommended this MERGE; it was never executed (dir still present, status "ambiguous"). Re-surfaced. |

---

## KEEP — active, real value, clear next action (15)

Each maps to a live user surface or a CI gate. Genuinely in-flight.

- anthropic-memory-tool-backend — Phase 1 shipped (#671); later phases remain.
- ci-runner-hang — in progress; diagnostics hardened, root fix gated on N>1 captured dumps.
- docs-wiring-audit — partial; v1 shipped (`scripts/audit_docs_wiring.py`), CI advisory mode live.
- enforcement-vs-documentation — partial; framework approved, first enforcement shipped (cap=10).
- ops-dashboard-polish — Phase A complete; B/C/D partial.
- collaboration-gates — approved (2026-06-05); decisions recorded.
- doc-stack-reference-subtypes — approved; RAG retrieval-quality work, Phase-0 signal measured.
- integration-coverage — approved; KEEP as a gate — run cheap Phase-0 audit, archive if ROI absent.
- ops-mutating-endpoint-auth — approved; security gate for mutating endpoints.
- ops-path-picker — approved; filesystem scope picker, Phase 1 ready.
- redis-facade-direction — D1 relabel executed 2026-06-08; direction work ongoing.
- subsystem-value-gate — approved (2026-06-11); Owner: Patrick + agent.
- website-update-dashboard-and-fold — approved; folds attune-gui into `attune-ai[gui]`.
- pipeline-learner — draft but **arc member** (curator → learner); keep, clarify wiring before building.
- pipeline-coordinator-error-fidelity — draft; typed-error follow-up to the closed sdk-error spec.

## KEEP — draft / idea stage (commit or KILL — your call) (7)

Half-built-infra smell concentrates here. None have shipped code.
Recommend deciding commit-vs-kill per item rather than letting them
idle.

- ci-gating-lane-isolation — draft.
- just-in-time-recall — draft (2026-06-03); surfaces rules at decision points. (Note: a just-in-time recall hook appears to already fire at prompt time — verify premise vs. current behavior before building.)
- lessons-corpus-rag — draft (2026-06-11); authored after Phase 0 GO.
- opus-4-8-platform-fit — draft (2026-06-10); matrix pre-committed.
- sibling-subscription-auth — draft; routes sibling API calls through subscription (no double-billing); Phase 0 done.
- test-discipline-controls — draft; d5 ("pre-push hook must run `--branch`") adopted as live policy, rest deferred.
- opus-4-8-platform-fit / lessons-corpus-rag — both recent; likely keep, but confirm they aren't speculative.

## KEEP — living document (1)

- release-train — standing release-process doc; never "completes".

---

## Recommended execution order

1. **Archive the 18 confirmed-complete** (low risk — `docs/specs/` is
   mkdocs-excluded, so no strict-build risk; same as the prior pass).
2. **Resolve the 6 VERIFY items** — read each, reconcile the status
   line, archive the ones that are genuinely done (likely 4–6 of 6).
3. **Execute the deferred MERGE** (ops-dashboard-qa → ops-dashboard-polish).
4. **Triage the 7 drafts** with Patrick — commit or kill each.

Steps 1–3 are mechanical and cut the backlog ~48 → ~28 with no value
loss. Step 4 is the judgment call that needs Patrick.
