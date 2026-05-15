# Spec: Telemetry Rethink — Quality / Performance Dashboard

> Replace the current Telemetry page with a dashboard focused on
> **redundant API calls, spendthrift workflows, latency, and
> accuracy / truthfulness** — the signals Patrick actually wants
> to act on now that attune is aligned with Anthropic's solutions
> rather than positioned as cost-saving-first.

---

## Phase 1: Requirements

**Status**: draft

### Problem statement

The current `/telemetry` page renders a cost-savings rollup:
"today's events," "7-day spend," "savings vs naive baseline,"
"top workflows by cost." The page worked correctly for its
original framing — "how much did the framework save me?" — but
two things have changed:

1. **Positioning shift.** Attune is no longer cost-saving-first.
   The product is aligned with Anthropic's Agent SDK and uses
   the API where appropriate. "Savings" is a less useful headline
   than "where am I wasting effort?"
2. **New quality concerns.** With RAG grounding and the
   faithfulness work in attune-rag, accuracy / truthfulness is
   measurable and worth surfacing on the dashboard rather than
   left to manual spot-checks.

Patrick (2026-05-14): *"I'm more concerned that you're monitoring
redundant api calls or spendthrift practices as far as workflows
and computer processes go, latency is also a consideration that I
want to test. Just as I want to test the accuracy and truthfulness
of responses now that we've done more to improve them with RAG and
other features."*

The cost rollup isn't wrong — it's just no longer the most useful
view. Patrick's call: **replace** the current page rather than
add a sibling page (per the QA review).

### Scope

**In scope: replace `/telemetry` with a Quality page**

Four panels, each tied to a signal Patrick named:

1. **Redundant API calls** — detect when the same prompt
   (normalized: trimmed, stripped of timestamps and file paths)
   was sent N times within a window. Surface the top 10 redundant
   prompt clusters with click-through to the workflow that
   emitted them.
2. **Spendthrift workflows** — cost-per-result ratio. For each
   workflow, divide total cost by some unit of work (run count,
   bytes of output, fix count if available). Top 10 highest-
   ratio workflows; flags candidates for prompt tuning or
   restructuring.
3. **Latency** — per-workflow median + p95 wall-clock time.
   Separately, per-subagent latency where available. Surfaces
   slow operators independently of cost.
4. **Accuracy / faithfulness** — wire attune-rag's
   `FaithfulnessJudge` results (already structured per the
   2026-04-19 decision matrix) into a rolling chart. Hallucination
   rate and faithfulness score over the last 7 / 30 days.

Each panel includes:
- A 7-day trend sparkline (or comparable visual)
- A "What changed?" delta vs the previous 7-day window
- Click-through to the underlying events / workflow

**Out of scope:**

- The original cost rollup (deprecated, deleted)
- Per-event drilldowns (Phase 2)
- Alerting / threshold-crossing notifications (Phase 2)
- Cross-machine aggregation (out of scope for the local dashboard)

### Acceptance criteria

1. `/telemetry` now renders the Quality dashboard with four
   panels populated from live data.
2. Redundant-call detection catches at least one duplicate when
   the user re-runs a workflow with the same input within ~5
   minutes (verified manually).
3. Spendthrift-workflow panel surfaces the workflow with the
   highest cost-per-run when the user runs two workflows of
   different shapes.
4. Latency panel shows non-zero median for any workflow that
   has run in the time window.
5. Accuracy panel shows a faithfulness score from at least one
   attune-rag run; renders an empty state cleanly when no
   faithfulness telemetry exists yet.
6. The old cost rollup is gone from the page — no "savings"
   chip, no "7-day spend" KPI, no Daily activity table. The
   Home page's `home_kpis` cost tile is unaffected (Home stays).
7. The CHANGELOG documents the rename / replace as a behavior
   change so users who bookmarked `/telemetry` know what to
   expect.

### Non-goals / explicitly deferred

- **Rebuilding `read_telemetry_summary`.** The underlying
  `usage.jsonl` reader is fine; this spec changes what we
  AGGREGATE and PRESENT, not the storage layer.
- **Migrating away from the cost-bucket concept entirely.** Cost
  data still flows in; we just don't lead with it.
- **Alerting.** A user can read the Quality page and act; we're
  not paging them.

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| "Redundant" prompt clustering is fuzzy (when are two prompts the same?) | Med | Start with exact-match-after-normalization; add Levenshtein / embedding similarity in Phase 2 only if false negatives are common |
| Spendthrift metric formula is contestable (what's a "unit of result"?) | Med | First pass: cost-per-run. Document the formula on the page. Iterate after Patrick uses it for a week. |
| Faithfulness telemetry not yet wired | High | Build the empty state first; spec the data contract (`{workflow, faithfulness_score, ts}` records under `~/.attune/telemetry/rag/`); attune-rag PR follows |
| Replacing the page surprises users who bookmarked the cost view | Low | CHANGELOG note; the existing `read_telemetry_summary` data is still queryable via the API for anyone needing it |
| Latency panel surfaces noise if a workflow ran once with a network glitch | Low | Require ≥3 runs in the window before including a workflow; lower bar for the dev-mode dashboard |
