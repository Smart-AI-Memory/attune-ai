# Spec Backlog Triage — 2026-06-24 (delta pass)

> A delta value-judgment pass over `docs/specs/`, building on the
> 2026-06-20 triage
> ([../archive/spec-backlog-triage-2026-06-20/matrix.md](../archive/spec-backlog-triage-2026-06-20/matrix.md))
> rather than redoing it. Dispositions: **KEEP**, **ARCHIVE**,
> **MERGE**, **KILL**, **VERIFY**. All calls are recommendations;
> Patrick signs off. Nothing archived without sign-off — this pass
> was executed after sign-off on 2026-06-24.

---

## Context: what changed since 2026-06-20

The 2026-06-20 pass cut the active backlog 48 → 27 and was fully
executed (18 ARCHIVE + 3 VERIFY→ARCHIVE now under `archive/`). In the
four days since, the remaining KEEP-set kept shipping: nine specs
reached `complete`/`retired`/`implemented` (plus the prior triage card
itself) and were sitting in `docs/specs/` only because nothing had
moved them. This pass closes that gap and reconciles four stale status
lines.

---

## Summary

| Disposition | Count | Status |
|---|---|---|
| ARCHIVE — shipped/retired since prior pass | 7 | ✅ executed |
| VERIFY → ARCHIVE — confirmed shipped, stale status line | 2 | ✅ executed |
| ARCHIVE — prior triage card (executed) | 1 | ✅ executed |
| KEEP — active partials / approved-buildable | ~7 | active |
| KEEP — drafts (commit-or-kill — Patrick's call) | 8 | active |
| KEEP — living document | 2 | active |

**Executed: 10 directories moved to `archive/`.** Active top-level
backlog **33 → 23**. Four stale status lines reconciled in the archived
copies.

---

## ARCHIVE — complete/retired since the prior pass

| Spec | Evidence |
|---|---|
| reach-snapshot-resilience | implemented 2026-06-24 — Option A shipped (#1056). |
| help-docs-single-source | req executed + tasks complete 2026-06-24 — rollout done end-to-end. |
| attune-docs-marketplace | all files complete 2026-06-22 — Option A (retire + consolidate). |
| website-update-dashboard-and-fold | all files RETIRED / superseded 2026-06-20. |
| sibling-package-pre-commit | req + tasks complete 2026-06-20 (#940 on main; matrix kept it pending rebase — now reconciled). |
| collaboration-gates | req + tasks complete 2026-06-09 (#637/#638/#639). `decisions.md` carried a stale "in progress" — reconciled. |
| ops-path-picker | requirements "complete (shipped)". `decisions.md` carried a stale "approved" — reconciled. |
| spec-backlog-triage-2026-06-20 | the prior triage card, decisions executed — archive like its 06-04 predecessor. |

## VERIFY → ARCHIVE — confirmed shipped, status line was stale

| Spec | Drift | Verification |
|---|---|---|
| claude-agent-sdk-0-2-migration | req "approved" / tasks "approved (for review)" vs reality | `pyproject.toml` pins `claude-agent-sdk>=0.2.101,<0.3.0`, lockfile 0.2.105, "0.2.x adopted deliberately 2026-06-16", 17857 keyless tests green. Shipped in 8.7.0 (#917). Status reconciled to complete. |
| auto-merge-safe-class | req/design/decisions "approved" vs tasks.md "in progress" (matrix KEPT it on this very drift) | `.github/workflows/auto-merge-safe.yml` is live; memory records working end-to-end (#881). tasks.md reconciled to complete. |

---

## KEEP — genuinely open (23 remain)

**Active partials (clear next step):**

- ci-gating-lane-isolation — Layer A shipping; B/C deferred.
- docs-wiring-audit — partial; Phase 4 (nav/features.yaml sync, orphans) remaining.
- enforcement-vs-documentation — partial; framework live (cap=10), enforcements queued as candidates surface.

**Approved, buildable:**

- usage-signals — Phase 2b done; client ships with next PyPI release (near-done — refresh status line).
- integration-coverage — run the cheap Phase-0 audit, then keep-or-kill on ROI.
- help-serving-bridge — approved 2026-06-24 (new).
- extended-cache-ttl-siblings — approved 2026-06-22 (new; lives in top-level `specs/`).
- subsystem-value-gate — approved 2026-06-11.
- doc-stack-reference-subtypes — approved 2026-05-16.

**Near-complete (confirm → archive next pass):**

- anthropic-memory-tool-backend — Phase 1+2 shipped (#671); Option ③ re-scoped out. Confirm Phase 2 surfacing closed, then archive.

**Approved-with-artifacts (no requirements.md but live decisions/tasks):**

- ops-dashboard-polish — Phase A complete; B/C/D partial.
- ops-mutating-endpoint-auth — approved; security gate for mutating endpoints.
- redis-facade-direction — D1 relabel executed; direction work ongoing.

**Drafts — commit-or-kill (Patrick's call):**

- ci-runner-hang — active diagnostics; has a captured-dump lead.
- just-in-time-recall — ⚠️ verify premise (recall already fires at prompt time?) before building.
- lessons-corpus-rag — draft (Phase 0 GO).
- opus-4-8-platform-fit — Phase 1 approved; matrix pre-committed.
- pipeline-learner — draft; arc member (curator → learner).
- pipeline-coordinator-error-fidelity — draft; typed-error follow-up.
- post-commit-help-check-only — draft awaiting review.
- sibling-subscription-auth — draft; Phase 0 done.
- test-discipline-controls — d5 adopted as live policy; rest deferred.

**Living documents:**

- test-quality-program — ongoing program; never "completes".
- release-train — standing release-process doc.

---

## Strategic note

The genuinely-actionable approved specs are all infra/telemetry-adjacent
— the class Patrick's standing guidance flags as *not* the growth lever
(distribution + real users is). The backlog's dominant need this pass was
**hygiene** (archive the shipped 10), not execution. Nothing here
outranks the community-marketplace submission.
