# Baseline measurements

**Status**: complete (Phase 0 task 1)
**Created**: 2026-05-12
**Harness**: [scripts/phase0/measure.py](../../../scripts/phase0/measure.py)
**Target**: `src/attune/security/` — 2 files, 134 LOC total
**Budget**: `ATTUNE_MAX_BUDGET_USD=0` (cap disabled), depth=standard

## Methodology

The harness monkey-patches `agent_sdk_adapter.collect_agent_output()`
to count bytes per message type as they flow through the SDK stream,
then invokes the workflow's `execute()` directly. Per-run JSON
artifacts land in `docs/specs/agent-surface-rebalance/runs/`.

Captured fields:

- `stats.assistant_bytes` — bytes the orchestrator emits as
  intermediate `AssistantMessage` text in the SDK stream.
- `stats.result_bytes` — bytes in `ResultMessage.result`.
- `subagent_transcripts_kb` — bytes pulled separately via
  `list_subagents` / `get_subagent_messages` after the run.
  Already isolated from the parent stream by the SDK.
- `summary_bytes` — bytes in the WorkflowResult's `summary` field
  after adapter parsing.
- `final_output_bytes` — bytes the workflow returns as
  `final_output` (markdown report; **this is what crosses the
  workflow ↔ caller boundary**).

## Initial run (illustrates the budget-cap pitfall)

`security-audit` at depth=quick (default $2 cap) on the 2-file
target failed with `Reached maximum budget ($2)` after spawning
the first subagent. Even the smallest meaningful target exceeds
the quick cap because each of 4 subagents consumes its own
tokens. **Conclusion**: the quick cap is too low for real
multi-subagent analysis; standard ($10) or uncapped is the
minimum for measurement. The harness now defaults to `standard`.

Artifact: [runs/security-audit-quick-20260512-141333.json](runs/security-audit-quick-20260512-141333.json).

## Successful runs (cap disabled, depth=standard)

### security-audit

| Field | Value |
|-------|------:|
| elapsed_seconds | 146.2 |
| num_turns | 7 |
| cost_usd | $5.03 |
| messages_total | 140 |
| tool_use_messages | 45 |
| assistant_bytes | 6,821 |
| result_bytes | 279 |
| summary_bytes | 533 |
| final_output_bytes | 3,710 |
| subagent_transcripts_kb | 19.66 |
| intermediate_to_summary_ratio | 12.8x |

Artifact: [runs/security-audit-standard-20260512-141638.json](runs/security-audit-standard-20260512-141638.json).

### refactor-plan

| Field | Value |
|-------|------:|
| elapsed_seconds | 120.3 |
| num_turns | 4 |
| cost_usd | $3.75 |
| messages_total | 128 |
| tool_use_messages | 40 |
| assistant_bytes | 4,914 |
| result_bytes | 4,914 |
| summary_bytes | 486 |
| final_output_bytes | 486 |
| subagent_transcripts_kb | 0 |
| intermediate_to_summary_ratio | 10.1x |

Artifact: [runs/refactor-plan-standard-20260512-141911.json](runs/refactor-plan-standard-20260512-141911.json).

Note: refactor-plan's `assistant_bytes == result_bytes` reflects
the orchestrator's final `AssistantMessage` text being identical
to `ResultMessage.result` — i.e. the orchestrator does the
analysis directly rather than delegating, so its final text both
*is* the assistant turn and *is* the result. Different mechanism
than security-audit's 4-subagent fan-out.

## Where the bytes go (architectural reading)

```text
┌─────────────────────────────────┐
│ Claude Code main agent context  │
│                                 │
│  invokes MCP tool ──────────┐   │
│                             │   │
│  receives final_output ◄────┼── │ ← only crosses boundary
│  ( 3,710 B / 486 B )        │   │
└─────────────────────────────┼───┘
                              │
                              ▼
┌─────────────────────────────────┐
│ Workflow SDK session (isolated) │
│                                 │
│  orchestrator AssistantMessage  │
│  ( 6,821 B / 4,914 B )          │ ← stays inside
│                                 │
│  4 subagent sessions (security  │
│  audit) — 19.66 KB              │ ← also stays inside
│                                 │
│  ResultMessage.result           │
│  ( 279 B / 4,914 B )            │
└─────────────────────────────────┘
```

The "intermediate bytes" the spec proposed to isolate are
**already isolated** because both workflows are invoked through
MCP tools (verified in `plugin/skills/security-audit/SKILL.md`
and `plugin/skills/refactor-plan/SKILL.md`). The main agent
only ever sees `final_output`. See [decisions.md](decisions.md)
for the spec-level consequence.
