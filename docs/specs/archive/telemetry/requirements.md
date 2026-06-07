# Spec: Telemetry System

**Status**: complete (cost rollup) — quality-dashboard direction active

> **2026-06-04 (backlog triage):** the former `telemetry-rethink` spec
> was merged here as the forward direction for `/telemetry`. The cost-
> savings rollup (this spec, Phase 1–4) is shipped and complete; the
> next phase replaces it with a quality dashboard (redundant-call
> detection, spendthrift-workflow ranking, latency, faithfulness). See
> [quality-dashboard-requirements.md](./quality-dashboard-requirements.md)
> and [quality-dashboard-decisions.md](./quality-dashboard-decisions.md).

> Originally `docs/specs/TELEMETRY_DESIGN.md`, version 1.0 targeting attune-ai v3.8.2.
> Shipped in v3.8.0+. Implementation lives in `src/attune/telemetry/` (notably `usage_tracker.py`, `cli.py`, `cli_commands/telemetry_commands.py`).
>
> **Drift since authoring:** the design doc named the storage path `~/.empathy/telemetry/`; the shipped code uses `~/.attune/telemetry/`. Spec text below preserves the original wording for historical record; consult `usage_tracker.py` for current paths.

---

## Phase 1: Requirements

**Status**: complete

### Problem statement

Attune AI claims meaningful cost savings via tier routing (CHEAP / CAPABLE / PREMIUM) and caching, but those numbers are population estimates ("expected savings 73–77% for mid-level developer"), not measured per-user. Without local telemetry there is no way to:

- Show a user their **actual** savings on their own usage pattern.
- Validate the savings claims against real workflows.
- Diagnose anomalies (cost spikes, cache regressions).

The honest fix is local telemetry: every LLM call writes one JSON line to a local log; CLI commands aggregate that log into reports.

### Scope

**In scope:**

- A `UsageTracker` class that records one entry per LLM call: workflow, tier, model, provider, cost, tokens, cache hit/miss, duration.
- JSON Lines storage at a stable local path with atomic appends.
- File rotation (default 10 MB) and retention (default 90 days).
- Hook into `BaseWorkflow._call_llm()` so all workflows track automatically.
- CLI commands: `attune telemetry {show,savings,compare,reset,export}`.
- Privacy: SHA-256 hash of user identifier; no prompts, responses, file paths, code content, or credentials ever stored.
- Configuration file (`config.json`) for enable/disable and retention/size knobs.

**Out of scope (defer to v3.9.0+):**

- Real-time charts in a VSCode extension dashboard.
- Anonymous team-level aggregation across multiple users.
- Anomaly detection / cost-spike alerts.
- Active optimization suggestions (e.g. "switch this workflow to CHEAP").
- Export to external BI / analytics services.

### User stories

1. *As an attune user*, after a week of normal usage I want `attune telemetry show` to display my actual call counts, costs, and cache hit rate — so I can see what attune is doing on my behalf.
2. *As an attune user*, I want `attune telemetry savings` to tell me the dollar amount I saved this period vs. an all-PREMIUM baseline — so I can verify the marketing claim against my own data.
3. *As an attune user*, I want `attune telemetry compare` to compare two periods side-by-side — so I can see whether changes I made (more caching, different tier defaults) actually improved my cost profile.
4. *As a privacy-conscious user*, I want a one-line `attune telemetry reset` to nuke all local data, and I want documentation that proves no prompts or responses were ever recorded — so I can adopt this without worry.

### Edge cases & open questions

| Question / Edge case | Resolution |
|---|---|
| Process crash mid-write | Atomic write via temp file + POSIX rename. Partial entries are not possible. |
| File grows unbounded | Auto-rotate when current file exceeds `max_file_size_mb` (default 10). Up to 9 rotations kept (`usage.jsonl.1` … `.9`). |
| Old data accumulates indefinitely | `retention_days` (default 90) prunes during rotation/scan. |
| User has no telemetry data yet | `savings` and `compare` return a "no data" message with the workflow command to start tracking. |
| Baseline cost for "savings" calculation | Spec's first cut: assume `$0.45/task` × call count for an all-PREMIUM baseline. Acknowledged as approximate; refine if real PREMIUM-only runs are available. |
| Telemetry file corrupted | Reader skips malformed lines and continues; surfaces a warning in CLI output. |
| Multiple attune processes writing concurrently | Append-only with atomic temp-rename serialises writes; line atomicity guaranteed by single-line JSON + newline terminator. |
| User opts out | `enabled: false` in `config.json` short-circuits `track()`. Tracking off by default? **Decision: ON by default; documented prominently; trivial to disable.** |

### Affected layers

- [x] attune-ai (workflows + CLI + storage) — `src/attune/telemetry/`, `src/attune/cli_commands/telemetry_commands.py`, hook in `src/attune/workflows/base.py::_call_llm()`
- [ ] attune-rag (backend) — none
- [ ] attune-gui (frontend) — none in v3.8.x; future enhancement
- [ ] attune-help (mobile/docs) — none
- [ ] attune-author (authoring/infra) — none
