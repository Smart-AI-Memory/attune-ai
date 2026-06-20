# Spec backlog disposition — 2026-06-09

Step 1 of the "disposition, not completion" plan. Every in-flight spec
(after the #696/#697/#699 truthing pass) tagged with one verdict, so the
backlog is a *decision* list, not a vibe. Goal by next Monday: dead specs
gone, valuable few sequenced, 2–3 actually finished.

Verdicts: **BUILD-NEXT** (real feature, sequence it) · **PHASE-0**
(run the cheap audit, let data decide) · **VERIFY/FLIP** (shipped,
correct the status) · **GATED** (blocked external) · **PARKED** (deferred
on purpose) · **RETIRE** (archived).

## Cheap wins (clear this week, low effort)

| Spec | Verdict | Action |
|---|---|---|
| `docs-release-prep` | **RETIRE** ✅ | Archived 2026-06-09 — targeted v7.3.0, project is at v8.0.1; arc shipped piecemeal; premise moot. |
| `docs-wiring-audit` | **VERIFY/FLIP** ✅ | Relabelled draft → partial (v1 `audit_docs_wiring.py` shipped). |
| `integration-coverage` | **PHASE-0** | Run the bug-catchability audit (classify 30 days of bugs) → it self-decides. |
| `just-in-time-recall` | **PHASE-0** | "D2 trigger PENDING Phase 0" — run its Phase 0. |
| `doc-stack-reference-subtypes` | **PHASE-0 / PARKED** | Cheap Phase-0 measurement, or leave parked for the next attune-author session. |

## Gated / parked (label honestly, no work)

| Spec | Why |
|---|---|
| `anthropic-memory-tool-backend` | Phase 1 shipped; Phase 2 gated on AMS 0.15.x (not on PyPI) + deferred pending a use case. |
| `sibling-package-pre-commit` | Phase 0 done, Phase 1+ consciously paused (sibling repo). |
| `test-discipline-controls` | Decisions recorded; D5 adopted as live policy. Effectively done-as-decision-record. |
| `enforcement-vs-documentation` | Slow-burn framework; first enforcement (`worktree_path_guard`) shipped, more as-needed. |

## Build-next (the real backlog — sequence these)

| Spec | State | Notes |
|---|---|---|
| `attune-verify` | Phase 3 awaiting review | **#1 pick** — active product, nearly there, high value. |
| `windows-xdist-flakes` | approved, design ready | **#2 pick** — recurring real pain, bounded. |
| `docs-completeness-audit` | approved; ~170 untracked docs unverified | **Live, growing debt** — `ORCHESTRATION_API.md` says v4.0.0, `PROJECT_OVERVIEW.md` says v5.1.1 (real: 8.0.1). Needs a SCOPE call (all ~170 vs high-traffic subset). |
| `opus-4-8-platform-fit` | Phase 1 approved, design next | Real; just moved to Opus 4.8. |
| `workflow-result-formatting` | T1 shipped (#649), rest pending | Finish what's started. |
| `website-update-dashboard-and-fold` | audit done, pre-Phase-1 | User-facing. |
| `pipeline-learner` + `pipeline-coordinator-error-fidelity` | both draft | Coupled arc — do together or not at all. |
| `sibling-subscription-auth` | Phase 0 shipped, Phase 1 gated on assumptions | Verify assumptions first. |

## The week, concretely

- **~4 cheap wins**: 1 retired + 1 flipped (done today); 3 Phase-0s to run.
- **~4 gated/parked**: honestly labeled, zero work.
- **~9 build-next**: pick the top 1–2 to *finish* this week — recommended pair
  `attune-verify` + `windows-xdist-flakes`; `docs-completeness-audit` is a strong
  third given the live version-fiction.
- Durable habit (prevents relapse): **flip a spec's status in the PR that ships
  its work** — now that the reconciler recognizes informative status (#697).
