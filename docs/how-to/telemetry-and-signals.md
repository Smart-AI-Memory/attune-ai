# Telemetry and Agent Coordination Signals

Attune AI records detailed telemetry on every workflow run and tracks
coordination signals between agents. Use this guide when you want to
understand where your AI budget is going, whether the tier router is
making good decisions (e.g., a stage that keeps failing at Haiku may
need promotion to Sonnet), or what is happening across agents in a
multi-agent workflow.

---

## Telemetry Data Model

Every workflow run records:

- **Task type** — which workflow was called
- **Model used** — which Claude model tier executed the stage
- **Actual cost** vs **baseline cost** (what it would cost at Opus-only pricing)
- **Latency** — end-to-end duration in milliseconds
- **Success** — whether the stage completed successfully
- **Cache hits** — whether prompt caching reduced input tokens

Data is stored in `~/.attune/telemetry/usage.jsonl` (JSONL, one record per
run) and summarized in `~/.attune/costs.json`.

---

## Cost Tracking

### Daily Report

```bash
attune costs
attune costs --days 30
attune costs --workflow security-audit
```

**Example output:**

```
Cost Report — Last 7 days
--------------------------------------------------
  Requests:        142
  Actual cost:     $0.4821
  Baseline (Opus): $6.3900
  Saved:           $5.9079  (92.5%)
```

The "Baseline" figure is the estimated cost if every call had used Claude
Opus 4 at premium tier. The gap shows how much intelligent tier routing saved.

### Today's Spend

```bash
attune costs today
```

### Export for Analysis

```bash
attune costs export -o costs.json
attune costs export -o costs.csv --format csv --days 90
```

---

## Adaptive Routing Statistics

The adaptive router assigns each workflow stage to CHEAP, CAPABLE, or PREMIUM
tier based on learned performance data. The routing stats commands let you
inspect those decisions.

### Overall Routing Health

```bash
attune telemetry routing-stats
```

Shows tier distribution, cost breakdown, and cache hit rate across all
workflows for the past 7 days.

### Per-Workflow Breakdown

```bash
attune telemetry routing-stats --workflow code-review
attune telemetry routing-stats --workflow code-review --stage scan --days 14
```

**Example output:**

```
📊 Adaptive Routing Statistics

  Workflow:      code-review
  Period:        Last 14 days
  Total calls:   56
  Avg cost:      $0.0028
  Success rate:  98.2%

  Models used:   claude-haiku-4-5, claude-sonnet-4-5

  Per-Model Performance:
    claude-sonnet-4-5:
      Calls:         40   Success rate: 100.0%
      Avg cost:      $0.0042  Avg latency: 1380ms
      Quality score: 0.94
    claude-haiku-4-5:
      Calls:         16   Success rate: 93.8%
      Avg cost:      $0.0004  Avg latency: 620ms
      Quality score: 0.81
```

The **quality score** is a composite of success rate, output length, and
user feedback signals. A score below 0.80 suggests the assigned model
tier is not performing well for this stage — use
`attune telemetry routing-check` to get an explicit promotion
recommendation.

### Routing Recommendations

```bash
attune telemetry routing-check
attune telemetry routing-check --workflow perf-audit
```

Analyzes recent routing decisions and flags stages where the current tier
is underperforming. Output indicates whether to promote a stage to a higher
tier.

### Model Performance by Provider

```bash
attune telemetry models
attune telemetry models --days 30
```

Shows cost, latency, and success rate broken down by model across all
workflows — useful for identifying which models are most cost-effective.

---

## Agent Coordination Signals

Use this section when running multi-agent workflows (e.g., parallel
test generation or the release-prep team) and you want to verify that
all agents are alive and communicating, or to diagnose a workflow that
appears to have stalled. In single-agent workflows, this section is
not relevant.

In multi-agent workflows, agents communicate via a coordination bus. Each
agent registers itself, sends heartbeats, and can publish and subscribe to
coordination signals.

### Viewing Active Agents

```bash
attune telemetry agents
```

**Output:**

```
Active Agents
--------------------------------------------------
  ID           Type      Tier          Last heartbeat
  claude_...   claude    CONTRIBUTOR   2026-04-23 14:32:01
  worker_...   worker    STEWARD       2026-04-23 14:31:58
```

- **Type**: `claude`, `worker`, or `service`
- **Tier**: `OBSERVER`, `CONTRIBUTOR`, `VALIDATOR`, or `STEWARD`
- Access tier controls what resources an agent can read/modify

### Inspecting Signals for a Specific Agent

```bash
attune telemetry signals --agent claude_20260423_abc123
```

Shows all coordination messages — lock acquisitions, heartbeats,
announcements, and departures — for the given agent ID.

---

## Python API for Telemetry

```python
from attune.telemetry import UsageTracker

tracker = UsageTracker.get_instance()

# Overall stats
stats = tracker.get_stats(days=7)
print(f"Total calls:    {stats['total_calls']:,}")
print(f"Total cost:     ${stats['total_cost']:.4f}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")

# Cost by workflow
for name, cost in stats["by_workflow"].items():
    print(f"  {name:30s}: ${cost:.4f}")
```

### Recording a Custom Event

```python
tracker.record(
    task_type="custom-analysis",
    model="claude-sonnet-4-5",
    actual_cost=0.0025,
    baseline_cost=0.0150,
    latency_ms=1200,
    success=True,
    cache_hit=False,
)
```

---

## Telemetry Storage Locations

| File | Contents |
|------|----------|
| `~/.attune/telemetry/usage.jsonl` | Full request log (one JSON object per line) |
| `~/.attune/costs.json` | Aggregated cost summary by day and workflow |
| `~/.attune/telemetry/help_queries.jsonl` | Help system lookup events |

---

## Privacy and Data Control

All telemetry is stored locally — nothing is sent to any external service.

```bash
# Clear all cost data
attune costs reset --confirm

# Export before clearing
attune costs export -o backup.json && attune costs reset --confirm
```

---

## See Also

- [Cost Commands](../reference/cli-reference.md#costs-commands) — Full CLI reference
- [Agent Coordination](../reference/multi-agent.md) — Multi-agent architecture
  and access tiers
