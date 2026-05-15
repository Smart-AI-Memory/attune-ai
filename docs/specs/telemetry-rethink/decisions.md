# Spec: Telemetry Rethink — Decisions

> Pre-committed decisions captured 2026-05-14.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| Replace vs add page | **Replace** | Patrick's call. Avoids two dashboards competing for the same mental model. CHANGELOG note covers the bookmarked-URL transition. |
| New page identity | "Quality" or "Performance" | Final name decided at design phase. "Telemetry" is retired as a route label even if the URL stays `/telemetry` for backwards compat. |
| URL | Keep `/telemetry` | Bookmarks survive; the new title at the top of the page sets the new expectation. |
| Cost rollup fate | **Removed** from this page entirely | The cost data still flows through `usage.jsonl`; the Home page's KPI tiles continue showing it. Anyone who wants the rollup view can hit `/api/telemetry-summary` JSON. |
| Redundancy clustering — Phase 1 | Exact match after normalization (trim whitespace, drop timestamps, drop absolute file paths) | Cheap, deterministic. Embedding-based clustering is Phase 2 if false negatives are common. |
| Spendthrift formula — Phase 1 | `total_cost / run_count` per workflow | Simplest defensible formula. Document on-page so users can see what they're looking at. |
| Latency aggregation | Median + p95 per workflow over the time window | Median resists outliers; p95 catches the tail. |
| Latency minimum sample | ≥ 3 runs in the window | Below 3 it's noise, not signal. |
| Faithfulness data source | `~/.attune/telemetry/rag/*.jsonl` (NEW path; attune-rag must emit) | Keeps the data structurally separate from `usage.jsonl` cost events. attune-rag's `FaithfulnessJudge` already produces these records — just needs the disk write. |
| Empty-state policy | Each panel renders a meaningful "no data yet" message that names what would populate it | No silent zeros. |
| Time-window default | 7 days, with "Compare to previous 7 days" delta | Matches the Home page convention. |
| Configurable thresholds | Spendthrift `cost_per_run_threshold_usd`, latency `slow_workflow_p95_seconds`, redundancy `min_cluster_size`, faithfulness `low_score_threshold` — all under `[tool.attune-ops.telemetry]` in pyproject.toml | Lets the user calibrate to their workflow mix. |

---

## Open questions (resolve during design phase)

1. **Page name — "Quality" vs "Performance".** Both fit. "Quality"
   leans toward accuracy / faithfulness; "Performance" leans
   toward latency / cost. The page covers both. Patrick picks
   at design time.

2. **Redundancy window.** A 5-minute window catches re-runs of
   the same prompt. A longer window catches habitual rewrites.
   Start with 60 minutes? 24 hours? Calibrate against real
   telemetry.

3. **Spendthrift signal granularity.** Per-workflow is coarse;
   per-subagent (when SDK telemetry exposes it) would be sharper.
   Phase 1 = per-workflow; Phase 2 considers per-subagent if the
   data is available.

4. **What "result" means for spendthrift ratio.** Cost-per-run
   is the simplest. Patrick floated cost-per-bytes-of-output;
   cost-per-fix-found (security-audit, code-review) would be
   even better. Probably introduce only when there's a
   well-defined unit per workflow.

---

## Calibration record

To be filled in during implementation:

- [ ] Redundancy window — what value lets a real user catch
  obvious duplicates without flooding the list?
- [ ] Latency thresholds — what's the 95th-percentile
  workflow time across the 20 registered workflows?
- [ ] Faithfulness baseline — what score range do real
  attune-rag runs land in?

---

## Decision-change log

- 2026-05-14 — Initial decisions captured during spec draft.
  Triggered by QA review and Patrick's "moving away from cost-
  saving-first" framing. Memory page dropped, Sessions page
  scoped separately.
