# Archived Specs

Specs moved here are no longer in the active backlog. They are
**preserved in full** (git history + these directories) for reference;
nothing is deleted. The whole `docs/specs/` tree — including this
`archive/` subdir — is excluded from the mkdocs build, so archived
specs never affect the strict docs build.

Archived 2026-06-04 by the spec-backlog triage pass. See the full
rationale and evidence in
[`../spec-backlog-triage-2026-06-04/matrix.md`](../spec-backlog-triage-2026-06-04/matrix.md).

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
intentionally sequenced arc. Only the **completed base**
(multi-actor-bulletin — capability shipped and live in code) is
archived. The two active members stay in the live backlog:

- `bulletin-curator` — Phase 1 sources shipped; orchestrator remains.
- `pipeline-learner` — draft; curator wiring to be clarified.

Archiving the base spec record does not remove the capability or break
the arc.
