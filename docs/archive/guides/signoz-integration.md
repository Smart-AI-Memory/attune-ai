---
description: SigNoz Integration Guide integration guide. Connect external tools and services with Attune AI for enhanced AI capabilities.
---

# SigNoz Integration Guide

This guide explains how to export Attune AI LLM telemetry to SigNoz for enterprise-grade observability.

## Overview

The Attune AI monitoring system has a **two-tier architecture**:

- **Tier 1 (Default - Zero Config)**: JSONL telemetry logged to `.empathy/`, viewable in VSCode dashboard and CLI
- **Tier 2 (Enterprise - Opt-in)**: OpenTelemetry export to collectors like SigNoz, Datadog, or New Relic

This guide focuses on **Tier 2** - setting up OpenTelemetry export to SigNoz.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Attune AI Application                  │
│                                                  │
│  ┌──────────────┐        ┌──────────────┐      │
│  │ LLM Call     │───────▶│ Multi-Backend│      │
│  │ log_call()   │        │              │      │
│  └──────────────┘        │  ┌────────┐  │      │
│                          │  │ JSONL  │  │      │
│  ┌──────────────┐        │  └────────┘  │      │
│  │ Workflow Run │───────▶│              │      │
│  │ log_workflow│        │  ┌────────┐  │      │
│  └──────────────┘        │  │ OTEL   │  │      │
│                          │  └────────┘  │      │
│                          └──────┬───────┘      │
└─────────────────────────────────┼──────────────┘
                                  │
                          gRPC 4317
                                  │
                                  ▼
                      ┌────────────────────┐
                      │  OTEL Collector    │
                      │  (localhost:4317)  │
                      └──────────┬─────────┘
                                 │
                                 ▼
                      ┌────────────────────┐
                      │     SigNoz         │
                      │  (Query Service)   │
                      └────────────────────┘
```

## Prerequisites

- Python 3.10+
- Docker and Docker Compose (for running SigNoz)
- Attune AI v3.8.0-alpha or later

## Step 1: Install OpenTelemetry Dependencies

Install Attune AI with OTEL support:

```bash
pip install attune-ai[otel]
```

Or for enterprise users:

```bash
pip install attune-ai[enterprise]  # Includes OTEL
```

This installs:
- `opentelemetry-api>=1.20.0`
- `opentelemetry-sdk>=1.20.0`
- `opentelemetry-exporter-otlp-proto-grpc>=1.20.0`

## Step 2: Set Up SigNoz

### Option A: Docker Compose (Recommended for Development)

1. Clone the SigNoz repository:

```bash
git clone https://github.com/SigNoz/signoz.git
cd signoz/deploy
```

2. Start SigNoz:

```bash
docker-compose -f docker/clickhouse-setup/docker-compose.yaml up -d
```

3. Wait for services to start (30-60 seconds), then verify:

```bash
# Check if OTEL collector is running
curl http://localhost:4317

# Access SigNoz UI
open http://localhost:3301
```

### Option B: SigNoz Cloud (Recommended for Production)

1. Sign up at [https://signoz.io/teams](https://signoz.io/teams)
2. Get your OTEL collector endpoint (e.g., `ingest.signoz.io:443`)
3. Get your ingestion key from the SigNoz dashboard

## Step 3: Configure Attune AI

### Option A: Environment Variable (Recommended)

Set the OTEL endpoint:

```bash
export ATTUNE_OTEL_ENDPOINT=http://localhost:4317
```

For SigNoz Cloud:

```bash
export ATTUNE_OTEL_ENDPOINT=https://ingest.signoz.io:443
export OTEL_EXPORTER_OTLP_HEADERS="signoz-access-token=YOUR_TOKEN_HERE"
```

### Option B: Auto-Detection

If you don't set `ATTUNE_OTEL_ENDPOINT`, the framework automatically detects:
1. `localhost:4317` (default OTEL gRPC port)
2. Falls back to JSONL-only if no collector is found

## Step 4: Use Multi-Backend Logging

Update your code to use the multi-backend:

```python
from attune.monitoring.multi_backend import get_multi_backend
from attune.models.telemetry import LLMCallRecord, WorkflowRunRecord

# Get multi-backend (auto-detects OTEL if available)
backend = get_multi_backend()

# Log LLM calls - goes to JSONL + OTEL
call_record = LLMCallRecord(
    call_id="call_123",
    timestamp="2026-01-05T10:00:00Z",
    provider="anthropic",
    model_id="claude-sonnet-4",
    tier="capable",
    task_type="code_review",
    input_tokens=1000,
    output_tokens=500,
    estimated_cost=0.025,
    latency_ms=2000,
    success=True,
)
backend.log_call(call_record)

# Log workflow runs - goes to JSONL + OTEL
workflow_record = WorkflowRunRecord(
    run_id="run_456",
    workflow_name="code-review",
    started_at="2026-01-05T10:00:00Z",
    completed_at="2026-01-05T10:02:00Z",
    stages=[
        {
            "stage_name": "analyze",
            "tier": "capable",
            "model_id": "claude-sonnet-4",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost": 0.025,
            "latency_ms": 2000,
            "success": True,
            "skipped": False,
        }
    ],
    total_input_tokens=1000,
    total_output_tokens=500,
    total_cost=0.025,
    baseline_cost=0.100,
    savings=0.075,
    savings_percent=75.0,
    total_duration_ms=2000,
    success=True,
    providers_used=["anthropic"],
    tiers_used=["capable"],
)
backend.log_workflow(workflow_record)
```

## Step 5: Verify Telemetry in SigNoz

1. Open SigNoz UI: `http://localhost:3301` (or your SigNoz Cloud URL)
2. Navigate to **Services** → **attune-ai**
3. You should see:
   - Service overview with request rate, latency, error rate
   - Traces for each workflow run
   - Spans for each LLM call

### Trace Structure

Each workflow creates a trace with the following structure:

```
workflow.code-review (2000ms)
├── stage.analyze (2000ms)
│   └── llm.anthropic.claude-sonnet-4 (2000ms)
│       ├── llm.provider: anthropic
│       ├── llm.model: claude-sonnet-4
│       ├── llm.tier: capable
│       ├── llm.usage.input_tokens: 1000
│       ├── llm.usage.output_tokens: 500
│       ├── llm.cost.estimated: 0.025
│       └── llm.latency_ms: 2000
```

## Step 6: Query Telemetry Data

### Using SigNoz UI

1. **Metrics Dashboard**:
   - Filter by `service.name = attune-ai`
   - View cost trends: `sum(llm.cost.estimated) by workflow.name`
   - View token usage: `sum(llm.usage.total_tokens) by llm.tier`

2. **Traces Explorer**:
   - Filter by `workflow.name = code-review`
   - Sort by `workflow.cost.total` descending to find expensive workflows
   - Filter by `llm.error = true` to find failures

3. **Create Alerts**:
   - Go to **Alerts** → **New Alert**
   - Condition: `sum(workflow.cost.total) > 10.0` (daily spend > $10)
   - Channel: Slack, PagerDuty, etc.

### Using ClickHouse SQL (Advanced)

SigNoz stores traces in ClickHouse. You can query directly:

```sql
-- Top 10 most expensive workflows
SELECT
    workflow_name,
    SUM(total_cost) as total_cost,
    COUNT(*) as run_count,
    AVG(total_cost) as avg_cost
FROM signoz_traces.distributed_workflow_runs
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY workflow_name
ORDER BY total_cost DESC
LIMIT 10;
```

## Semantic Conventions

The Attune AI uses custom semantic conventions for LLM telemetry:

### LLM Call Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `llm.provider` | string | LLM provider name | `anthropic`, `openai` |
| `llm.model` | string | Model identifier | `claude-sonnet-4`, `gpt-4o` |
| `llm.tier` | string | Cost tier | `cheap`, `capable`, `premium` |
| `llm.task_type` | string | Task type | `code_review`, `summarization` |
| `llm.usage.input_tokens` | int | Input tokens | `1000` |
| `llm.usage.output_tokens` | int | Output tokens | `500` |
| `llm.usage.total_tokens` | int | Total tokens | `1500` |
| `llm.cost.estimated` | float | Estimated cost (USD) | `0.025` |
| `llm.cost.actual` | float | Actual cost (USD) | `0.024` |
| `llm.latency_ms` | int | Latency in milliseconds | `2000` |
| `llm.error` | bool | Whether call failed | `true`, `false` |
| `llm.error.type` | string | Error type | `RateLimitError` |
| `llm.error.message` | string | Error message | `Rate limit exceeded` |
| `llm.fallback.used` | bool | Whether fallback was used | `true`, `false` |
| `llm.fallback.original_provider` | string | Original provider before fallback | `openai` |

### Workflow Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `workflow.name` | string | Workflow name | `code-review` |
| `workflow.run_id` | string | Unique run ID | `run_123` |
| `workflow.usage.input_tokens` | int | Total input tokens | `2000` |
| `workflow.usage.output_tokens` | int | Total output tokens | `1000` |
| `workflow.cost.total` | float | Total cost (USD) | `0.050` |
| `workflow.cost.baseline` | float | Baseline cost (premium tier) | `0.200` |
| `workflow.cost.savings` | float | Savings (USD) | `0.150` |
| `workflow.cost.savings_percent` | float | Savings percentage | `75.0` |
| `workflow.duration_ms` | int | Duration in milliseconds | `5000` |
| `workflow.providers_used` | string | Comma-separated providers | `anthropic,openai` |
| `workflow.tiers_used` | string | Comma-separated tiers | `capable,cheap` |
| `workflow.success` | bool | Whether workflow succeeded | `true`, `false` |

## Troubleshooting

### OTEL Backend Not Detected

**Symptom**: Logs show "⚠️ Failed to initialize OTEL" or telemetry only goes to JSONL

**Solutions**:
1. Check if SigNoz collector is running:
   ```bash
   curl http://localhost:4317
   ```

2. Verify OTEL dependencies are installed:
   ```bash
   python -c "import opentelemetry.trace; print('OK')"
   ```

3. Check environment variable:
   ```bash
   echo $ATTUNE_OTEL_ENDPOINT
   ```

4. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Traces Not Appearing in SigNoz

**Symptom**: OTEL backend initializes but traces don't appear

**Solutions**:
1. Check SigNoz logs:
   ```bash
   docker logs signoz-otel-collector
   ```

2. Verify endpoint is correct:
   ```python
   from attune.monitoring.otel_backend import OTELBackend
   backend = OTELBackend()
   print(f"Endpoint: {backend.endpoint}")
   print(f"Available: {backend.is_available()}")
   ```

3. Manually flush spans:
   ```python
   backend.flush()
   ```

### High Latency

**Symptom**: Application slows down after enabling OTEL export

**Solutions**:
1. Use batch export (already default in BatchSpanProcessor)
2. Increase batch size:
   ```python
   from attune.monitoring.otel_backend import OTELBackend
   backend = OTELBackend(batch_size=100)  # Default: 10
   ```

3. Use async export (recommended for production):
   ```python
   # The BatchSpanProcessor already exports asynchronously
   # No additional configuration needed
   ```

## Production Best Practices

### 1. Use SigNoz Cloud for Production

Self-hosted SigNoz requires managing ClickHouse, query service, and collector. SigNoz Cloud handles this for you.

### 2. Set Up Alerts

Configure alerts for:
- **Daily cost exceeds $50**: `sum(workflow.cost.total) > 50.0`
- **Error rate exceeds 5%**: `count(llm.error = true) / count(*) > 0.05`
- **Latency exceeds 10s**: `p95(llm.latency_ms) > 10000`

### 3. Use Sampling for High Volume

For applications with >10K LLM calls/day, enable sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
```

### 4. Secure Your Endpoint

For SigNoz Cloud, always use HTTPS and set the ingestion key:

```bash
export ATTUNE_OTEL_ENDPOINT=https://ingest.signoz.io:443
export OTEL_EXPORTER_OTLP_HEADERS="signoz-access-token=YOUR_SECRET_TOKEN"
```

### 5. Monitor Both JSONL and OTEL

- **JSONL**: Fast local debugging, always available
- **OTEL**: Enterprise observability, team collaboration

The multi-backend ensures you have both - if OTEL fails, JSONL keeps working.

## Cost Optimization

### 1. Identify Expensive Workflows

Query SigNoz for workflows with high cost:

```sql
SELECT
    workflow_name,
    AVG(savings_percent) as avg_savings,
    SUM(total_cost) as total_cost
FROM signoz_traces.distributed_workflow_runs
WHERE timestamp >= now() - INTERVAL 30 DAY
GROUP BY workflow_name
HAVING avg_savings < 50.0  -- Less than 50% savings
ORDER BY total_cost DESC;
```

### 2. Optimize Tier Usage

Find workflows that could use cheaper tiers:

```sql
SELECT
    workflow_name,
    tier,
    COUNT(*) as call_count,
    AVG(cost) as avg_cost_per_call
FROM signoz_traces.distributed_llm_calls
WHERE tier = 'premium'
GROUP BY workflow_name, tier
ORDER BY avg_cost_per_call DESC;
```

### 3. Track Savings Over Time

Create a dashboard to visualize cost savings:

```sql
SELECT
    DATE(timestamp) as date,
    SUM(total_cost) as actual_cost,
    SUM(baseline_cost) as baseline_cost,
    SUM(savings) as total_savings,
    AVG(savings_percent) as avg_savings_percent
FROM signoz_traces.distributed_workflow_runs
WHERE timestamp >= now() - INTERVAL 90 DAY
GROUP BY date
ORDER BY date;
```

## Next Steps

1. **Set up alerts** for cost and error monitoring
2. **Create dashboards** for your team to track LLM usage
3. **Integrate with CI/CD** to track telemetry per deployment
4. **Export to data warehouse** for long-term analysis (ClickHouse → Snowflake/BigQuery)

## Additional Resources

- [SigNoz Documentation](https://signoz.io/docs/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [Attune AI Monitoring Architecture](../architecture/monitoring.md)
- [Alert CLI Guide](../how-to/setup-alerts.md)

## Support

For issues with:
- **Attune AI**: [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **SigNoz**: [SigNoz Slack](https://signoz.io/slack) or [GitHub](https://github.com/SigNoz/signoz/issues)
- **OpenTelemetry**: [CNCF Slack #opentelemetry](https://slack.cncf.io/)
