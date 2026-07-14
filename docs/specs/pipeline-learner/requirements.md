# Spec: Pipeline Learner

> A mining workflow that reads workflow run history + bulletin
> archive, identifies common multi-step sequences, and offers
> to canonicalize them as declarative pipelines. The bottom-up
> path to pipeline authoring — songs that emerge from what
> we've actually played.

**Status:** draft — kill proposed at 2026-07-14 triage, SPARED by Patrick; commit-or-kill again next triage
**Created:** 2026-05-17
**Owner:** TBD
**Related:**
- [`multi-actor-bulletin`](../multi-actor-bulletin/requirements.md) — provides the archived run history this workflow mines
- [`bulletin-curator`](../bulletin-curator/requirements.md) — sibling consumer; the curator surfaces this learner's output to Patrick
- [`project_bulletin_and_pipeline_learner.md`](~/.claude/projects/-Users-patrickroebuck-attune-ai/memory/project_bulletin_and_pipeline_learner.md) — high-level synthesis

---

## Problem statement

The current state of pipeline authoring in attune-ai:
**top-down only.** Songs (`release-prep`, `secure-release`,
`doc-orchestrator`) are hardcoded as Python workflow classes.
There's no way for anyone — Patrick, downstream users, or me —
to look at the working patterns that actually emerge in real
use and canonicalize them as named, declarative pipelines.

The persisted run history in `~/.attune/ops/runs/<wf>/*.json`
contains thousands of runs going back months. Patterns are in
there — *"after security-audit on $path, code-review on the
same path runs within 30 min, 80% of the time"* — but nothing
mines them. They stay implicit in Patrick's working memory,
which means:

1. **They're not transferable.** New users (downstream) can't
   benefit from working patterns Patrick has discovered.
2. **They're not version-controlled.** A great working pattern
   today can be forgotten next quarter.
3. **They can't be automated.** Without a canonical name,
   nothing can invoke "the security-then-review pattern" as a
   first-class thing.

This spec defines the workflow that mines the history and
proposes canonicalization candidates. Acceptance — turning a
candidate into a real pipeline file — stays with Patrick (the
detector never writes; the writer never decides).

---

## Goals

1. **Mine run history** for common multi-step sequences with
   minimum-support thresholds.
2. **Rank candidates** by signal strength (frequency,
   consistency, recency, time-window tightness).
3. **Surface candidates** through the bulletin-curator's
   ranked-attention list as *"Save this as a named pipeline?"*
   items.
4. **Generate scaffolding** when accepted — write a candidate
   YAML pipeline file to `docs/specs/pipelines/<slug>.yaml`
   that Patrick can edit and commit.
5. **Stay opt-in.** No silent canonicalization. The learner
   proposes; Patrick disposes.

## Non-goals

- **Executing pipelines.** That's a separate concern handled by
  whatever pipeline runner lands later (the
  hybrid-with-decision-nodes design from the chord→song
  whiteboard discussion).
- **Reading semantic meaning** of workflow purposes. The miner
  works on observable patterns (workflow name, scope, timing),
  not on what the workflows do.
- **Predicting the next workflow** in real-time. That's the
  ATTUNE_REC channel's job. The learner mines *retrospectively*
  for patterns worth promoting.
- **Auto-applying canonical pipelines** as ATTUNE_REC
  suggestions. Possible v2; not v1.
- **Cross-host / multi-project mining.** Same-host, same-project
  in v1. Cross-project mining is a follow-up that depends on
  the Phase 3 Redis Streams bulletin backend (cross-host data
  source).

---

## Design

### Input: the corpus

Two source pools, merged:

1. `~/.attune/ops/runs/<wf>/*.json` — every persisted dashboard
   run since the dashboard started recording. Already has
   `workflow`, `scope`, `started_at`, `completed_at`, `status`,
   `actor` (after the bulletin spec lands).
2. `~/.attune/bulletin/archive/YYYY-MM-DD/*.jsonl` — daily
   rotated bulletin entries. Same shape; covers CLI / MCP /
   scheduled actors the dashboard doesn't see.

Both pools merge into a flat list of "actor X ran workflow Y on
scope Z, starting at T, completing at T+D, status S".

### Mining algorithm

A simple **temporal-sequence frequent-pattern mining** pass.
For each pair `(A, B)` of distinct workflows, count how often:

- Workflow A completed successfully on scope `P_A`
- Workflow B then ran on a scope `P_B` where `P_B ⊆ P_A` or
  `P_A ⊆ P_B`
- Both within the same actor's timeline (or same project, in v2)
- Within a configurable time window (default: 30 min)

Yields pair-frequency counts. Filter by minimum support (e.g.
`count ≥ 5 AND ratio_when_A_runs ≥ 0.5`). Extend to triples /
n-grams in a second pass; pair-mining is the v1 deliverable.

The thing being mined is **operator behavior** — when Patrick
manually runs A then B, that's signal. When ATTUNE_REC
auto-runs B from A, that's *different* signal (it's already a
canonicalized edge in the source code); the miner should
**weight manual sequences higher** because those represent
genuine emergent patterns, not encoded suggestions.

### Candidate output shape

For each above-threshold pair (or n-gram), emit:

```json
{
  "candidate_id": "security-audit_then_code-review",
  "sequence": [
    {"workflow": "security-audit", "scope_relation": "self_or_parent"},
    {"workflow": "code-review", "scope_relation": "from_predecessor"}
  ],
  "support": {
    "occurrences": 14,
    "first_seen": "2026-04-03",
    "last_seen": "2026-05-16",
    "ratio_when_first_step_runs": 0.78,
    "manual_vs_attune_rec": "12 manual / 2 attune-rec",
    "actors_observed": ["cc-session-abc", "dashboard-localhost-..."]
  },
  "confidence_score": 0.82,
  "suggested_pipeline_yaml": "docs/specs/pipelines/security-audit_then_code-review.yaml",
  "rationale": "Manual sequence emerged 12 times across 6 weeks; same-or-narrower scope on follow-up; 78% follow-rate."
}
```

The `confidence_score` is a weighted blend of frequency,
ratio, recency, and manual-fraction. Tuned later; sensible v1
defaults baked in.

### YAML pipeline scaffolding

When Patrick accepts a candidate (via the curator's
`AskUserQuestion` card), the learner writes a starter pipeline
YAML to `docs/specs/pipelines/<slug>.yaml`:

```yaml
# Auto-generated 2026-05-17 by pipeline-learner.
# Supporting evidence in docs/specs/pipelines/<slug>.evidence.json
# Edit freely. Original support metrics preserved in the evidence file.

name: security-audit_then_code-review
summary: "Run security-audit then code-review on the same scope."
pipeline:
  - workflow: security-audit
    scope: ${input.scope}
  - workflow: code-review
    scope: ${prev.scope}
```

Plus a sibling `.evidence.json` with the full support metrics
so the pipeline's provenance is auditable. Patrick edits the
YAML to taste, commits it, and the pipeline becomes a
first-class song.

### Invocation model

`pipeline-learner` is itself a workflow registered in the
existing workflow registry. Runs on-demand (`attune workflow
run pipeline-learner`) or on a schedule (weekly cron). Outputs
its candidates to:

1. `~/.attune/pipeline-learner/candidates.jsonl` — durable
   output the curator reads as one of its sources.
2. The dashboard's `/specs` or a new `/pipelines/candidates`
   surface.

Mining is CPU-bound, not LLM-backed in v1 (deterministic
algorithm; no agent calls needed). v2 might add an LLM pass to
generate human-readable pipeline names and summaries, but the
core mining is pure algorithm.

---

## Acceptance criteria

1. **Surfaces a known pattern.** Seed the corpus with 10
   fixture runs that contain the security-audit →
   code-review pattern 7 times. Run the learner. The candidate
   appears with `occurrences: 7` and a sensible confidence
   score.
2. **Filters noise.** Same fixture also contains 2 isolated
   workflow runs that aren't part of any pattern. They do not
   appear as candidates.
3. **Manual vs auto weighting.** Add 3 ATTUNE_REC-triggered
   security-audit → bug-predict pairs. The candidate scores
   them with `manual_vs_attune_rec: "0 manual / 3 attune-rec"`
   and confidence is lower than an equivalent-count manual
   pattern.
4. **Scaffolding lands.** Acceptance via the curator's
   AskUserQuestion writes a non-empty
   `docs/specs/pipelines/<slug>.yaml` + sibling evidence file.
5. **Idempotent re-runs.** Running the learner twice in a row
   without new corpus data produces identical candidates.
6. **No silent writes.** The learner never writes to
   `docs/specs/pipelines/` without an explicit acceptance
   signal.

---

## Tasks (phased)

### Phase 1 — Corpus reader + mining algorithm (~4h)

| # | Task | Effort |
|---|------|--------|
| 1 | `attune.pipeline_learner.corpus` — merge dashboard runs + bulletin archive | 1h |
| 2 | Pair-mining algorithm with scope-relation logic | 2h |
| 3 | Confidence scoring (frequency / ratio / recency / manual-weight) | 1h |

### Phase 2 — Workflow registration + outputs (~2h)

| # | Task | Effort |
|---|------|--------|
| 4 | `PipelineLearnerWorkflow` class registered in `_DEFAULT_WORKFLOW_NAMES` | 30m |
| 5 | Persist candidates to `~/.attune/pipeline-learner/candidates.jsonl` | 30m |
| 6 | Wire into the four registry drift-guard gates (per CLAUDE.md lesson) | 30m |
| 7 | Unit tests against fixture corpora | 30m |

### Phase 3 — Curator integration + scaffolding (~2h)

| # | Task | Effort |
|---|------|--------|
| 8 | Curator reads candidates as one of its sources | 30m |
| 9 | `AskUserQuestion` acceptance handler writes the YAML + evidence file | 1h |
| 10 | End-to-end test: fixture corpus → mine → curator → accept → YAML lands | 30m |

### Phase 4 — Triples / n-grams (~2h, deferrable)

| # | Task | Effort |
|---|------|--------|
| 11 | Extend mining to 3-step sequences with cohesion threshold | 1.5h |
| 12 | Tests | 30m |

**Total estimated:** 8h for v1 (Phases 1–3); +2h for triples.

---

## Open questions

1. **Scope-relation logic.** Subset-relations are easy on
   absolute paths (`src/attune/security/` ⊂ `src/attune/`). But
   the bulletin allows custom scope strings, and discovery-sweep
   uses scope hashes. Lean: treat unrecognized scope strings
   as "scope: opaque" and only mine pairs where the scope
   relationship is determinable. Document the limitation.
2. **What counts as the same "operator behavior"?** Within a
   Claude Code session, sequential runs are clearly the same
   operator. Across sessions, less clear. Lean: same actor_id
   AND same project for v1. The bulletin-curator can later
   merge cross-session candidates if signals agree.
3. **Threshold tuning.** Defaults: 5 occurrences, 0.5 ratio.
   These are guesses; iterate based on what surfaces. The
   confidence score deliberately separates the inputs so we
   can re-weight without rerunning the miner.
4. **Negative evidence.** When Patrick dismisses a candidate
   ("not a real pattern"), the learner should suppress it
   from future surfacings. Per-candidate suppression for N
   days is simple; lean that for v1. Learning to *predict*
   which candidates will be dismissed is a v2 problem.
