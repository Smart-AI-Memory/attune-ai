# Release Train: measured 8.x → 9.0.0

> A durable map of the path to 9.0.0. **9.0.0 is a destination, not a
> package to assemble.** We get there by shipping a sequence of strong
> minors (8.1.0, 8.2.0, …), each with a coherent theme. 9.0.0 becomes
> whatever natural breaking boundary *emerges* from that progression —
> most likely the real Redis memory-subsystem evolution, whenever it's
> genuinely ready — and is defined by accretion, not forced.

**Status:** fulfilled (2026-07-14 triage) — the 9.0.0 destination shipped 2026-06-26; repo now at 10.4.1; living map closed
**Created:** 2026-06-08 (from the Phase 1 code-grounded spec triage)
**Owner:** Patrick

---

## Governing direction (locked)

- **Redis is permanent.** attune *aligns on* Redis (the Agent Memory
  Server path via `attune_redis`) **and** Anthropic Claude (Memory tool,
  subagents) — the "follows both vendors' best practices" posture. No
  Redis exit. The in-tree `attune.redis_*` facades are the *older* way of
  using Redis, superseded by the *newer* `attune_redis` integration —
  both stay. See
  [`redis-facade-direction`](../redis-facade-direction/decisions.md).
- **No manufactured major.** We do not invent a breaking change to hit a
  round number. Features evolve to best practices as normal engineering.

---

## How the triage was done

Every non-archive spec under `docs/specs/` was triaged by **verifying its
primary artifact against the codebase** — not by trusting the spec's
self-reported status header (which the
[`spec-status-self-truthing`](../spec-status-self-truthing/) lesson shows
is stale ~80% of the time). Each spec was bucketed SHIPPED / PARTIAL /
UNEXECUTED / NOT-A-FEATURE with a grep-cited artifact.

The verification confirmed the lesson hard: roughly a third of the
"draft"/"approved" specs were already shipped. Those status headers were
corrected in a companion PR.

---

## 8.1.0 — cut what's already merged

A pile of value is sitting on `main`, unreleased. The `[Unreleased]`
CHANGELOG already carries the headline items (Anthropic Memory-tool
backend, AMS recency recall, Opus 4.8, the 3× premium-pricing fix, the
`attune_redis` working-memory + dedup + search-limit fixes). The triage
adds a set of **shipped-but-status-stale** specs whose code is already on
`main`:

| Spec | Verified artifact |
| --- | --- |
| anthropic-cost-integration | `ops/anthropic_cost.py` (Phases 1–2) |
| anthropic-memory-tool-backend | `memory/memory_tool.py` (Phase 1, #671) |
| bulletin-curator | `curator/core.py` + `/curator` page + CLI |
| collaboration-gates (spend gate v1) | `gates/spend_gate.py` (#637–#640) |
| dashboard-pending-writes-journal | `ops/pending_writes.py` |
| ops-help-page | `ops/routes/help.py` + `ops/help_data.py` |
| ops-mutating-endpoint-auth | `ops/security.py` token gate |
| ops-path-picker | `static/js/runner.js` scope picker |
| public-help-site | `attune-ai-dev/build_help.py` + CI |
| spec-status-self-truthing | `plugin/hooks/_state.py` |
| workflow-path-arg-unification | 5/5 workflows accept `path` (gap closed) |

**The 8.1.0 work is release ceremony, not new code:** finalize the
CHANGELOG section, bump the version across the 7+ files (pyproject + all
plugin manifests — PyPI version ≡ all manifests), rebuild `dist/`, tag,
trusted-publish, verify PyPI. Plus the standing CI hygiene below.

---

## 8.2.0+ — themed forward minors

The PARTIAL / UNEXECUTED specs, grouped into coherent themes to sequence
across the next minors. **Theme A is the recommended 8.2.0** — it's the
Redis + Anthropic spine and the most claimable.

### Theme A — Redis + Anthropic alignment (the strategic spine)

- **anthropic-memory-tool-backend Phase 2** — MCP/CLI surfacing (Phase 1
  shipped).
- **pattern-review-queue** — re-home `PatternStaging` on the file/AMS
  backend, off the old Redis coupling; needs CLI + dashboard surface
  (facade-direction D3). `PatternStaging` already exists in
  `memory/short_term/patterns.py`.
- **collaboration-gates referent gate** — the deferred second gate
  (spend gate v1 already shipped).
- **Leverage items (facade-direction D4)** — `agent-memory-server`
  0.14.0 → 0.15.2 bump + re-verify; the RedisVL `datatype` contribute-back
  PR.

### Theme B — Ops dashboard maturity

- **ops-dashboard-polish** — Phase B (a11y/behavioral), Phase C (Memory
  page), Phase D.
- **workflow-result-formatting** — `output.py` `Section`/`WorkflowReport`
  exist; needs the `voice/report_renderer.py` renderer + CLI `--verbose`
  + dashboard wiring.
- **website-update-dashboard-and-fold** — `/dashboard` feature route
  (install-command centralization already done).

### Theme C — Docs pipeline & release gating

- **docs-wiring-audit Phase 4** — nav/`features.yaml` sync + `orphans.yml`
  allowlist; promote `scripts/audit_docs_wiring.py` to a CI gate.
- **doc-stack-reference-subtypes** — procedural/free-form reference
  meta-templates in attune-author.
- **docs-completeness-audit → docs-release-prep** — the docs release
  ceremony (gated on the two audits).

### Theme D — Quality & CI hardening

- **test-discipline-controls** — the pre-push patch-coverage gate hook.
- **windows-xdist-flakes** — the flake investigation + fix-vs-marker call.
- **integration-coverage** — Phase 0 bug-catchability audit.
- **enforcement-vs-documentation** — the next enforcements (first one,
  the worktree-path-guard hook, already shipped).
- **Restore the larger-runner CI routing** — `tests.yml` is on a marked
  TEMPORARY default-runner fallback; don't ship a major on a temporary
  CI config.

### Theme E — Pipeline learning

- **pipeline-learner** — register `PatternLearner`
  (`meta_workflows/pattern_learner.py`) as a workflow + curator/CLI.
- **pipeline-coordinator-error-fidelity** — define `coordinator_error_kind`
  + per-stage error attribution in orchestrator workflows.

### Theme F — Recall UX

- **just-in-time-recall** — the `jit_recall` PreToolUse hook (guidance
  surfaced before the call).

### Sibling-repo work (not attune-ai releases)

- **sibling-package-pre-commit** — baseline hooks + CI in the 4 sibling
  repos.
- **sibling-subscription-auth** — subscription-aware LLM routing in
  attune-author / attune-rag.
- **attune-verify** — the deterministic-resolver + semantic-judge
  package (lives in its own repo).

---

## Backlog hygiene — closed out (not release items)

Audit / QA / process / evaluation docs — marked complete so they stop
polluting the in-flight list:

- agent-surface-parallelism-evaluation (RETIRED — redundant with
  `deep_review.py`)
- consolidate-claude-md-lessons (editorial, complete)
- doc-fiction-cleanup (cleanup executed)
- docs-completeness-audit / docs-release-prep (process docs)
- ops-dashboard-qa-2026-05-14 (QA punch list → ops-dashboard-polish)
- spec-backlog-triage-2026-06-04 (triage doc)
- test-quality-program (ongoing umbrella program, not a single ship)
- ops-session-discovery-cli (DEFER — see its decisions.md)

---

## Recommended next steps (in order)

1. **Cut 8.1.0** from merged work — it's ready; the value is on `main`.
2. **8.2.0 = Theme A** (Redis + Anthropic alignment).
3. Then Themes B–F as measured minors; 9.0.0 emerges as a natural
   boundary later, defined by accretion — never forced.
