# Archived Specs

Specs moved here are no longer in the active backlog. They are
**preserved in full** (git history + these directories) for reference;
nothing is deleted. The whole `docs/specs/` tree — including this
`archive/` subdir — is excluded from the mkdocs build, so archived
specs never affect the strict docs build.

Archived in two passes:

- **2026-06-04** — original triage (69 → 41). See
  [`spec-backlog-triage-2026-06-04/matrix.md`](spec-backlog-triage-2026-06-04/matrix.md).
- **2026-06-20** — delta pass (48 → 27), closing the gap where prior
  KEEP-items shipped but were never moved here. See
  [`../spec-backlog-triage-2026-06-20/matrix.md`](../spec-backlog-triage-2026-06-20/matrix.md)
  and the dated section at the bottom of this file.

---

## Complete — work shipped (verified in `src/`)

| Spec | Why archived |
|---|---|
| agent-surface-rebalance | Retired — Phase 0 measurement falsified the context-bloat premise. |
| ams-int8-quantization | `attune_redis/vector_db_int8.py` shipped in v7.4.0; Phase-0 GO. |
| coverage-exclusion-policy | Complete; omit-audit script + pre-commit hook live. |
| deprecated-module-retirement | Done; both modules removed, zero callers cross-repo. |
| discovery-sweep | Complete; engine + 6 sources + CLI shipped (PRs #303–322). |
| discovery-sweep-ops-integration | Complete; dashboard chips + drill-in live. |
| ignored-tests | Complete; 35 tests recovered, all `--ignore` removed. |
| multi-actor-bulletin | Base of the collaboration arc — backend shipped & wired (`src/attune/bulletin/`, runner, `/bulletin`). See arc note below. |
| ops-runner-tier2 | Complete; all 6 phases shipped. |
| ops-scope-picker-ia | Implemented (PRs #344, #363, #365). |
| ops-security-hardening | Complete; TrustedHost, queue bounds, run-view logging. |
| ops-specs-page-refinement | Complete (PRs #533–539). |
| ops-workflows-page-refinement | Complete (v7.3.0/v7.3.1). |
| probe-c-memory-investigation | Complete; threading leak fixed, `-n auto` restored. |
| sdk-error-message-fidelity | Complete v7.3.1; typed error kinds, 14/16 workflows migrated. |
| test-infrastructure | Complete; xdist re-enabled, ignored files resolved. |
| vercel-noise-cleanup | Complete; upstream Vercel project deleted. |

## Premise-invalid or superseded

| Spec | Why archived |
|---|---|
| coverage-canonical-pattern | OOM/runner-shutdown premise invalidated; real fix landed via probe-c. |
| windows-xdist-honor | Superseded by windows-memory-detection (root-caused the contention). |
| redis-decoupling | P1+P2 shipped; full decoupling is a deferred memory-subsystem rewrite. |

## One-off chore / punch-list / out-of-repo

| Spec | Why archived |
|---|---|
| recursing-montalcini-stash-triage | One-off stash salvage; self-retiring, not a durable feature. |
| rag-code-gen-cleanup | Cleanup punch-list; shipped scope done, rest cross-repo/architecture. |
| help-ia-code-quality | Proposal handed off to task-level (one help template). |
| spec-viewer-ia | An attune-gui concern; belongs in that repo's triage. |

## Killed — never-started, unvalidated value

| Spec | Why archived |
|---|---|
| files-api-adoption | Never-started token-opt; no measured need, prompt caching already discounts. |
| rag-async-integration | Never-started; depends on an `expand_async` API attune-rag hasn't shipped. |
| subagent-surface-strategy | Documentation-only meta-spec; the question it poses is already answered in its own text. |

## Folded into a sibling

| Spec | Folded into |
|---|---|
| worktree-inventory | `ops-sessions-page` — a marginal `group_by` panel, not a standalone spec. |

Note: `telemetry-rethink` was also retired in this pass but **merged
into** `docs/specs/telemetry/` (as `quality-dashboard-*.md`) rather
than moved here, since telemetry stays the active home for that work.

---

## Collaboration-loop arc note

`multi-actor-bulletin → bulletin-curator → pipeline-learner` is an
intentionally sequenced arc. As of the 2026-06-20 pass, **two of three
members are complete and archived**:

- `multi-actor-bulletin` — base capability shipped and live in code
  (archived 2026-06-04).
- `bulletin-curator` — complete; Phases 2–3 shipped in v8.0.0 (#657),
  Task 4.1 was optional manual verify (archived 2026-06-20).
- `pipeline-learner` — **still active** (draft); curator wiring to be
  clarified before building. Stays in the live backlog.

Archiving the completed members does not remove the capability or
break the arc; `pipeline-learner` remains the open downstream member.

---

## 2026-06-20 delta-pass additions

Archived this pass — prior-KEEP items that shipped since 2026-06-04,
three VERIFY items reconciled to complete, the prior triage card, and
one deferred fold. Full evidence:
[`../spec-backlog-triage-2026-06-20/matrix.md`](../spec-backlog-triage-2026-06-20/matrix.md).

### Complete — shipped since the prior pass

| Spec | Why archived |
|---|---|
| agent-surface-parallelism-evaluation | RETIRED 2026-05-29 — orchestrator ships in `deep_review`. |
| anthropic-cost-integration | Complete 2026-06-09 — `ops/anthropic_cost*` shipped. |
| attune-verify | Complete 2026-06-09 — all build tasks done. |
| ci-matrix-right-sizing | Complete — slim matrix implemented (#937). |
| consolidate-claude-md-lessons | Complete 2026-06-06 (#646 + #647). |
| doc-fiction-cleanup | Complete — cleanup executed. |
| docs-completeness-audit | Complete 2026-06-09 (#714–#717). |
| drift-guards-to-generators | Complete 2026-06-19 — conversions 1 + 2 (#938). |
| ops-help-page | Complete — `ops/routes/help.py` + `ops/help_data.py` shipped. |
| ops-session-discovery-cli | Complete — conclusion reached (recommendation: DEFER). |
| pattern-review-queue | Complete 2026-06-09 — R1–R5 + R8 shipped (#689). |
| polish-cost-reduction | Complete 2026-06-10 — both levers shipped. |
| public-help-site | Complete 2026-06-09 — `attune-ai-dev/build_help.py` shipped. |
| sdk-subprocess-isolation | Complete 2026-06-10 — all four phases shipped. |
| spec-status-self-truthing | Complete — shipped in #567. |
| workflow-path-arg-unification | Complete — all 5 target workflows accept `path`. |
| workflow-result-formatting | Complete 2026-06-12 — `WorkflowReport` shipped. |

### VERIFY items reconciled to complete

| Spec | Why archived |
|---|---|
| bulletin-curator | requirements + tasks "complete, shipped v8.0.0 (#657)"; only optional Task 4.1 remained. (Arc member — see arc note.) |
| dashboard-pending-writes-journal | requirements + design "complete — Phase 1 shipped (`pending_writes.py` + routes + tests, #469, #492)". |
| windows-xdist-flakes | design "complete (v1, 2026-06-10)"; reopen only if flakes resurface. |

### Prior triage card + deferred fold

| Spec | Why archived |
|---|---|
| spec-backlog-triage-2026-06-04 | The prior triage card; its decisions were executed. |
| ops-dashboard-qa-2026-05-14 | Folded into `ops-dashboard-polish` — the 2026-06-04 pass recommended this MERGE; executed now. |
