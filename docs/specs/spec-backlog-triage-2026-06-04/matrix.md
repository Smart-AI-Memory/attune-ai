# Spec Backlog Triage — 2026-06-04

> A value-judgment pass over every directory in `docs/specs/`.
> Goal: decide, per spec, whether to **KEEP** (real remaining user
> value + a clear next action), **ARCHIVE** (complete or concluded —
> preserve in history), **MERGE** (fold into a named sibling), or
> **KILL** (premise invalid / infrastructure-for-its-own-sake with no
> validated user value).
>
> The KILL/ARCHIVE/MERGE calls in this doc are **recommendations**.
> Patrick makes the final calls; nothing is deleted without sign-off.

---

## Why this pass

The backlog held **69 spec directories** (the "170+" figure was
inflated — 221 files, not dirs). That volume is a smell: it suggests
more half-built infrastructure than validated user value. This pass
applies the repo's own recurring lessons:

- *Validate infrastructure against user value before extending* — the
  BEP-middleware lesson (93 tests, zero working skills, zero CLI
  integration).
- *Passing tests don't prove integration — verify with inbound-import
  grep* — dead modules ship green suites.
- *Re-validate a spec's premise against current code* — specs go stale
  in days; the code is the contract, the spec text is a hypothesis.

Status was derived (not header-trusted) per the
`spec-status-self-truthing` rules: terminal-line scan + strikethrough-
aware checkbox parsing + symbol/file greps in `src/` for any
completion or code-target claim.

---

## Summary

| Disposition | Count |
|---|---|
| ARCHIVE (complete — work shipped) | 19 |
| ARCHIVE (premise-invalid / superseded) | 3 |
| ARCHIVE (one-off chore / punch-list / out-of-repo) | 4 |
| MERGE (fold into sibling) | 2 |
| KILL-candidate (never-started, unvalidated value) | 4 |
| KEEP (active — real value, clear next action) | 37 |
| **Total** | **69** |

Net effect if all recommendations land: **28 specs leave the active
backlog** (26 archive/merge + closing the clear-completes), leaving
~37 specs that map to real, in-flight user value — plus 4 KILL
candidates surfaced for Patrick's call.

---

## ARCHIVE — complete (work shipped, verified in `src/`)

These are done. The spec record moves to history; no work remains.

| Spec | Evidence |
|---|---|
| agent-surface-rebalance | Retired 2026-05-12 — Phase 0 measurement falsified the context-bloat premise (MCP already isolates intermediate bytes). |
| ams-int8-quantization | `attune_redis/vector_db_int8.py` shipped in v7.4.0; Phase-0 GO. Flip `decisions.md` status, then archive. |
| ci-debt | Phase A complete 2026-05-10. **KEPT ACTIVE** (decision 4) — residual Phase 3 remains; not archived. |
| coverage-exclusion-policy | Complete 2026-05-12; `scripts/check_coverage_omits.py` + pre-commit hook live. |
| deprecated-module-retirement | Done 2026-05-09; both modules removed, zero callers cross-repo. |
| discovery-sweep | Complete 2026-05-13; engine + 6 sources + 10 CLI flags shipped (PRs #303–322). |
| discovery-sweep-ops-integration | Complete 2026-05-16; dashboard chips + drill-in live. |
| ignored-tests | Complete; 35 tests recovered, all `--ignore` directives removed. |
| multi-actor-bulletin | Backend shipped & wired — `src/attune/bulletin/` live, runner appends entries, `/bulletin` route renders. (Arc base — see arc note.) |
| ops-runner-tier2 | Complete 2026-05-24; all 6 phases shipped. |
| ops-scope-picker-ia | Implemented 2026-05-16 (PRs #344, #363, #365). |
| ops-security-hardening | Complete 2026-05-16; TrustedHost, queue bounds, run-view logging live. |
| ops-specs-page-refinement | Complete 2026-05-31 (PRs #533–539). |
| ops-workflows-page-refinement | Complete 2026-06-02 (v7.3.0/v7.3.1). |
| probe-c-memory-investigation | Complete 2026-05-12; threading leak fixed, `-n auto` restored (PR #242). |
| sdk-error-message-fidelity | Complete v7.3.1 2026-06-02; typed error kinds shipped, 14/16 workflows migrated. |
| telemetry | Complete (v3.8.0+); `src/attune/telemetry/` + CLI shipped. **KEPT ACTIVE** (decision 3) — now the home for the merged quality-dashboard direction; not archived. |
| test-infrastructure | Complete; xdist re-enabled, ignored files resolved. |
| vercel-noise-cleanup | Complete 2026-05-14; upstream Vercel project deleted. |

---

## ARCHIVE — premise-invalid or superseded

| Spec | Evidence |
|---|---|
| coverage-canonical-pattern | Paused 2026-05-12 — OOM/runner-shutdown premise invalidated; the actual fix landed via probe-c. No remaining work addresses current failures. |
| windows-xdist-honor | Superseded by windows-memory-detection — the `-n 1`-not-honored premise was a symptom of the memory/probe contention that windows-memory-detection root-caused. Verify Windows honors `-n auto`, then archive. |
| redis-decoupling | Partial — P1+P2 shipped (PRs #279, #281); P3 audited as no-op; full decoupling is a memory-subsystem rewrite explicitly deferred. The tractable scope is done; archive this spec, open a fresh one if the rewrite is ever wanted. |

---

## ARCHIVE — one-off chore / punch-list / out-of-repo scope

These were never durable feature specs — they're operational chores or
artifacts that belong elsewhere.

| Spec | Evidence |
|---|---|
| recursing-montalcini-stash-triage | One-off salvage of a dirty-deleted worktree's stash. Self-retiring by design. Run Phase 0 triage (≤1 session) or archive now; not a durable feature. |
| rag-code-gen-cleanup | Cleanup punch-list — security+quality fixes shipped; deferred items are cross-repo / architecture-wide, out of scope for this card. |
| help-ia-code-quality | Proposal-only; single execution goal approved 2026-05-14. Handed off to task-level (write one help template). No spec-level work remains. |
| spec-viewer-ia | An **attune-gui** concern (group `/specs` by project), not attune-ai. Belongs in the attune-gui repo's triage. |

---

## MERGE — fold into a named sibling

| Spec | Fold into | Rationale |
|---|---|---|
| ops-dashboard-qa-2026-05-14 | ops-dashboard-polish | It's the QA punch-list that ops-dashboard-polish already phases. Its value is captured there. |
| telemetry-rethink | telemetry (or keep separate — Patrick's call) | Proposes replacing the cost-savings rollup on `/telemetry` with a quality dashboard (redundant-call/latency/faithfulness). Same page, conflicting direction — needs a priority decision, not parallel specs. |

---

## KILL-candidate — never-started, unvalidated user value

The half-built-infra smell concentrates here. None have shipped code;
each rests on an unproven premise. Surfaced for Patrick's explicit
call — recommend KILL unless he wants to keep one as a parked idea.

| Spec | Why kill | Counter-argument (if kept) |
|---|---|---|
| files-api-adoption | Never-started token-optimization. No measured evidence that inline-payload cost is a real problem; Anthropic prompt caching already discounts repeated context. Classic optimize-before-measuring. | Could save tokens on large-repo scans — but should be a Phase-0 measurement, not a standing spec. |
| rag-async-integration | Never-started; depends on an `expand_async` API that attune-rag hasn't shipped. Premise gated on an external dependency that doesn't exist yet. | Real concurrency win once attune-rag ships async — re-open then. |
| worktree-inventory | Marginal operational add-on (a `group_by` panel on `/sessions`); depends on ops-sessions-page landing first. Operational tooling, not user value. | Cheap once ops-sessions-page exists — fold into it rather than carry a standalone spec. |
| subagent-surface-strategy | Documentation-only meta-spec that "closes a briefing carryover" by arguing the 1-agent/15-skill ratio is correct. No code, no user surface — the question is already answered in the doc. | It IS the answer to a recurring question; ARCHIVE-as-answered is arguably gentler than KILL. |

---

## KEEP — active, real value, clear next action (37)

Grouped by cluster. Each maps to a user-facing surface (a workflow,
skill, CLI, or dashboard page) or a CI gate that protects users.

### Ops dashboard (8)

- ops-dashboard-polish — concrete post-publish polish; B2/C1/C3/D2–D6 remain.
- ops-help-page — design locked, Phase 1 unblocked; browse/search the help corpus.
- ops-mutating-endpoint-auth — security gate for mutating endpoints; approved, gated.
- ops-path-picker — filesystem scope picker; design locked, Phase 1 ready.
- ops-sessions-page — resume recent-session context; Phase 1 locked.
- ops-specs-completion-candidates — surfaces completion candidates; conservative detector, Phase 1 locked.
- ops-specs-features — Specs tab port; gated on real CI/bug criteria.
- dashboard-pending-writes-journal — durability against silent edit loss; Phase 1 scoped.

### Docs / help / spec-tooling (10)

- doc-fiction-cleanup — removing fictional APIs from real docs; phases shipping.
- doc-stack-reference-subtypes — RAG retrieval quality; Phase-0 signal measured.
- docs-completeness-audit — audits 145+ untracked docs; companion to doc-fiction-cleanup.
- docs-link-prevalidation — catches LLM-hallucinated links before CI; design locked.
- docs-wiring-audit — `scripts/audit_docs_wiring.py` live; CI advisory mode shipped.
- docs-release-prep — orchestrates the doc-cleanup cluster into one release; gated on siblings.
- enforcement-vs-documentation — framework for promoting lessons to mechanical gates; first enforcement shipped.
- spec-status-self-truthing — derivation code partially in `_state.py`; finishes the status truthing this very pass relied on.
- website-update-dashboard-and-fold — folds attune-gui into `attune-ai[gui]`; contracts locked.
- consolidate-claude-md-lessons — reduce 6,973-line CLAUDE.md; clear plan, low risk, intentionally deferred.

### Testing / CI (7)

- ci-debt — real CI-matrix failures; Phase 3 pending. (Confirm vs ARCHIVE.)
- larger-runners — CI parallelism speedup; Phase 1 straightforward.
- integration-coverage — KEEP **as a gate**: run the cheap Phase-0 audit, then archive if ROI is absent.
- test-discipline-controls — coverage SOTH + pre-push gate; Phase 1 ready.
- test-quality-program — standing rubric-driven program; machinery in place.
- sibling-package-pre-commit — hook-version parity across siblings; Phase 0 done.
- windows-xdist-flakes — KEEP **as insurance**: run probes only if flakes resurface post windows-memory-detection; else defer.

### Collaboration loop / workflow (6)

- bulletin-curator — Phase 1 sources shipped (`src/attune/curator/`), orchestrator (`core.py`) missing; high-value. **Arc member.**
- pipeline-learner — mines run history into declarative pipelines; downstream of curator. **Arc member.**
- pipeline-coordinator-error-fidelity — typed error surfacing for pipeline coordinators; follow-up to closed sdk-error spec.
- workflow-failure-exit-propagation — exit-code contract (currently exit-0-on-failure); real user pain. (Queued prior task.)
- workflow-path-arg-unification — kwarg unification; bridge adequate, defer-but-keep.
- workflow-result-formatting — kill dataclass-repr dumps in output; tactical UX fix.

### Memory / cost / verification (6)

- anthropic-cost-integration — closes the $0-vs-$400 dashboard spend gap; Phase 1 ready.
- attune-verify — output-side hallucination fact-checker; design approved, Patrick-gated on repo/PyPI.
- claude-cross-session-memory — cross-session findings persistence; approved, Phase 1 ready.
- just-in-time-recall — surfaces rules at decision points mid-session; Phase 0 proof.
- sibling-subscription-auth — routes sibling API calls through subscription (no double-billing); Phase 0 done.
- agent-surface-parallelism-evaluation — KEEP **as a gate**: Phase-0 measurement. NOTE: `deep_review.py` is sequential (3 passes), so the parallel-fan-out premise is NOT already shipped — but if Phase 0 shows no win, retire it like its sibling agent-surface-rebalance.

---

## The collaboration-loop arc (do not break)

`multi-actor-bulletin → bulletin-curator → pipeline-learner` is an
intentionally sequenced arc (whiteboard memory). State:

- **multi-actor-bulletin** — base shipped (backend live, wired into
  runner + dashboard). Archive the spec record; the capability stays.
- **bulletin-curator** — Phase 1 sources shipped; orchestrator +
  CLI/dashboard surface remain. KEEP — this is the active linchpin.
- **pipeline-learner** — draft; learner code exists but its curator
  integration is undefined. KEEP, but clarify the wiring before
  building.

Recommendation: archive the completed base, keep the two live members.
Don't kill any arc member on isolated-value grounds.

---

## Decisions made (Patrick, 2026-06-04)

1. **Archive batch** → *Archive all 26 now.* Moved to
   `docs/specs/archive/` (whole `docs/specs/` tree is mkdocs-excluded,
   so no strict-build risk). **Exception:** ci-debt was pulled from the
   batch per decision 4 below, so 25 of the 26 archived here.
2. **KILL-candidates** → *Kill 3, fold the 4th.* files-api-adoption,
   rag-async-integration, subagent-surface-strategy archived under
   `archive/`; worktree-inventory folded into `ops-sessions-page` (note
   added there) and archived.
3. **telemetry-rethink** → *Merge into telemetry as the new direction.*
   Its files moved to `docs/specs/telemetry/quality-dashboard-*.md`;
   standalone dir removed; telemetry stays the active home.
4. **ci-debt** → *Keep for residual Phase 3.* Stays in the active
   backlog (removed from the archive batch).

### Net result

- **28 spec directories archived** to `docs/specs/archive/` (25 from
  the batch − ci-debt + 3 kills + worktree-inventory fold).
- **1 merged** (telemetry-rethink → telemetry).
- Active backlog: **69 → 41** spec directories (incl. this triage dir).

See [`archive/README.md`](../archive/README.md) for the per-spec
archive rationale.
