---
description: Attune AI Monitoring System - Specification & Implementation Plan: **Version:** 2.0 (Simplified) **Created:** 2026-01-05 **Updated:** 2026-01-05 **Targe
---

# Attune AI Monitoring System - Specification & Implementation Plan

**Version:** 2.0 (Simplified)
**Created:** 2026-01-05
**Updated:** 2026-01-05
**Target Release:** v3.8.0
**Estimated Timeline:** 2-3 weeks (3 sprints)

---

## Executive Summary

Build a **zero-config monitoring system** for LLM usage with progressive enhancement:

### Default Features (Developer Install - Zero Config)
1. **JSONL Telemetry** - Automatic logging to `.empathy/` (already implemented)
2. **CLI Dashboard** - View stats with `attune telemetry` (already implemented)
3. **VSCode Panel** - Real-time visualization (new, automatic)

### Enterprise Features (Explicit Opt-in)
4. **Alert System** - Threshold-based alerting via `attune alerts init` (opt-in)
5. **OpenTelemetry** - Export to SigNoz/Datadog via env vars (opt-in)

**Key Design Principles:**
- **Zero-config default experience** - Works immediately after `pip install`
- **Progressive enhancement** - Advanced features are opt-in
- **No required configuration files** - Use CLI wizards or env vars
- **Leverage existing infrastructure** - Built on [telemetry.py](../../src/attune/models/telemetry.py)
- **Privacy-first** - Local-first data storage, external export is opt-in

---

## Installation Tiers

### Tier 1: Developer Install (Default - Zero Config)

```bash
pip install attune-ai
attune workflow run code-review
```

**What works automatically:**
- ✅ Telemetry logged to `.empathy/llm_calls.jsonl` and `.empathy/workflow_runs.jsonl`
- ✅ CLI dashboard: `attune telemetry` (shows cost, calls, success rate)
- ✅ VSCode panel appears automatically (if using VSCode extension)
- ✅ Charts, activity feed, click-through to source files

**What's NOT enabled:**
- ❌ NO alerts (not running)
- ❌ NO OTEL export (not sending data externally)
- ❌ NO configuration files created
- ❌ NO background processes

**Setup time:** 0 minutes (works immediately)

---

### Tier 2: Enterprise Install (Explicit Opt-in)

#### Enable Alerts
```bash
attune alerts init  # Interactive 3-question wizard
```

**What happens:**
- Creates alert configuration (SQLite database)
- Starts background watcher process
- Sends webhooks/emails when thresholds exceeded

**Setup time:** 1 minute (3-question wizard)

---

#### Enable OTEL Export
```bash
export ATTUNE_OTEL_ENDPOINT=http://localhost:4317
pip install attune-ai[otel]
```

**What happens:**
- Telemetry sent to SigNoz/Datadog/New Relic
- JSONL telemetry still works (both enabled simultaneously)

**Setup time:** 2 minutes (env var + pip install)

---

## Architecture Overview

### Default Architecture (Tier 1)

```
┌─────────────────────────────────────────────────────────────────┐
│                     LLM Workflow Execution                       │
│  (Code Review, Research, Debug, Test Generation, etc.)          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │  TelemetryStore         │
              │  (JSONL Backend)        │
              └─────────────┬───────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
       ┌──────────────┐        ┌──────────────┐
       │ VSCode Panel │        │ CLI Dashboard│
       │ (Real-time)  │        │ (Terminal)   │
       └──────────────┘        └──────────────┘
```

**Key Points:**
- Single JSONL backend (default, always enabled)
- No external dependencies
- No background processes
- Privacy-first (all data local)

---

### Enterprise Architecture (Tier 2 - Opt-in)

```
┌─────────────────────────────────────────────────────────────────┐
│                     LLM Workflow Execution                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │  MultiBackend           │
              │  (Composite)            │
              └─────────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ JSONL Store  │   │ OTEL Backend │   │ Alert Engine │
│ (Default)    │   │ (Opt-in)     │   │ (Opt-in)     │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ VSCode/CLI   │   │ SigNoz/      │   │ Webhook/     │
│              │   │ Datadog      │   │ Email/Slack  │
└──────────────┘   └──────────────┘   └──────────────┘
```

**Key Points:**
- All backends optional except JSONL
- OTEL enabled via env vars
- Alerts enabled via CLI wizard
- User explicitly opts in to external data export

---

## Component 1: VSCode Dashboard Panel

### 1.1 Specification

**Purpose:** Real-time LLM usage monitoring integrated into VSCode extension

**Features:**
- **Overview Dashboard**
  - Total cost (today, week, month)
  - Token usage (input/output breakdown)
  - Success rate (% of successful calls)
  - Active workflows count

- **Cost Analytics**
  - Cost over time (line chart)
  - Cost by provider (pie chart)
  - Cost by tier (cheap/capable/premium)
  - Top 5 expensive workflows

- **Performance Metrics**
  - Average latency by tier
  - Fallback rate (% of calls using fallback)
  - Error rate trend
  - Circuit breaker status

- **Live Activity Feed**
  - Recent LLM calls (last 20)
  - Click to jump to workflow source file
  - Filter by workflow/provider/tier

**Technology Stack:**
- React (existing VSCode extension)
- Chart.js or Recharts (visualizations)
- WebSocket (optional, for real-time updates)
- Read from `.empathy/llm_calls.jsonl` and `.empathy/workflow_runs.jsonl`

### 1.2 User Interface Mockup

```
╔══════════════════════════════════════════════════════════════╗
║                  EMPATHY TELEMETRY                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📊 Overview (Last 7 days)                                   ║
║  ┌────────────┬────────────┬────────────┬────────────┐      ║
║  │ Total Cost │   Calls    │  Success   │ Avg Latency│      ║
║  │   $12.45   │   1,234    │   98.5%    │   1.2s     │      ║
║  └────────────┴────────────┴────────────┴────────────┘      ║
║                                                              ║
║  💰 Cost by Provider                                         ║
║  ┌──────────────────────────────────────┐                   ║
║  │  Anthropic:  $8.20  (65.9%)          │                   ║
║  │  OpenAI:     $3.15  (25.3%)          │                   ║
║  │  Ollama:     $1.10  (8.8%)           │                   ║
║  └──────────────────────────────────────┘                   ║
║                                                              ║
║  🏆 Top Expensive Workflows                                  ║
║  ┌──────────────────────────────────────┐                   ║
║  │  1. code-review      $4.50 (12 runs) │ → [View]         ║
║  │  2. research         $2.80 (8 runs)  │ → [View]         ║
║  │  3. debug            $1.90 (15 runs) │ → [View]         ║
║  └──────────────────────────────────────┘                   ║
║                                                              ║
║  📈 Cost Trend (Last 30 days)                                ║
║  ┌──────────────────────────────────────┐                   ║
║  │        ▁▂▃▄▅▆▇█                      │                   ║
║  │     ▁▂▃▄▅▆▇█                         │                   ║
║  │  ▁▂▃▄▅▆▇█                            │                   ║
║  └──────────────────────────────────────┘                   ║
║                                                              ║
║  🔴 Recent Activity                     [Refresh] [Clear]   ║
║  ┌──────────────────────────────────────────────────────┐   ║
║  │ 2m ago  code-review  Anthropic  $0.12  ✓  320ms     │   ║
║  │ 5m ago  debug        OpenAI     $0.08  ✓  450ms     │   ║
║  │ 7m ago  research     Anthropic  $0.25  ✗  1200ms    │   ║
║  └──────────────────────────────────────────────────────┘   ║
║                                                              ║
║  [Export CSV] [Clear History] [Settings]                    ║
╚══════════════════════════════════════════════════════════════╝
```

### 1.3 Implementation Details

**File Structure:**
```
website/components/telemetry/
├── TelemetryPanel.tsx           # Main panel component
├── OverviewStats.tsx             # Overview cards
├── CostChart.tsx                 # Cost visualization
├── WorkflowList.tsx              # Top expensive workflows
├── ActivityFeed.tsx              # Recent calls feed
├── hooks/
│   ├── useTelemetryData.ts      # Data fetching hook
│   └── useTelemetryStats.ts     # Analytics calculations
└── utils/
    ├── telemetryParser.ts       # Parse JSONL files
    └── chartHelpers.ts          # Chart data transformation
```

**Data Flow:**
1. VSCode extension reads `.empathy/llm_calls.jsonl` on panel open
2. Parse JSONL → convert to LLMCallRecord objects
3. Calculate analytics (using existing TelemetryAnalytics)
4. Render dashboard with charts
5. Optional: Watch file for changes → auto-refresh

**Integration Points:**
- Reuse `TelemetryAnalytics` from [telemetry.py](../../src/attune/models/telemetry.py:332-527)
- Call Python analytics via VSCode extension bridge
- Cache results in extension state (update every 30s)

---

## Component 2: Alert System

### 2.1 Specification

**Purpose:** Proactive monitoring with threshold-based alerts

**Alert Types:**
1. **Cost Alerts**
   - Daily spend exceeds threshold
   - Workflow cost spike (>2x average)
   - Provider cost anomaly

2. **Performance Alerts**
   - Error rate exceeds threshold (e.g., >5%)
   - Latency spike (>2x average)
   - Fallback rate exceeds threshold

3. **Usage Alerts**
   - Token usage spike
   - Unusual workflow activity
   - Circuit breaker opened

**Alert Channels:**
- **Webhook** - POST JSON to any URL (Slack, Discord, custom)
- **Email** - SMTP integration (optional)
- **Stdout** - Console logging (development)

**Configuration Format:**
```yaml
# .empathy/alerts.yaml
alerts:
  - name: high_daily_cost
    description: Alert when daily spend exceeds $10
    condition:
      metric: daily_cost
      operator: gt
      threshold: 10.0
    actions:
      - type: webhook
        url: https://hooks.slack.com/services/YOUR/WEBHOOK
        payload:
          text: "⚠️ Daily LLM cost exceeded $10: ${value}"
      - type: email
        to: team@example.com
        subject: "High LLM Cost Alert"

  - name: error_rate_spike
    description: Alert when error rate exceeds 10%
    condition:
      metric: error_rate
      operator: gt
      threshold: 10.0
      window: 1h
    actions:
      - type: webhook
        url: https://hooks.slack.com/services/YOUR/WEBHOOK

  - name: expensive_workflow
    description: Alert when single workflow costs >$5
    condition:
      metric: workflow_cost
      operator: gt
      threshold: 5.0
    actions:
      - type: webhook
        url: https://hooks.slack.com/services/YOUR/WEBHOOK
        payload:
          text: "💸 Expensive workflow: {workflow_name} cost ${value}"
```

### 2.2 Alert Engine Architecture

```python
# src/attune/monitoring/alerts.py

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Protocol

class Operator(Enum):
    GT = "gt"      # Greater than
    LT = "lt"      # Less than
    EQ = "eq"      # Equal
    GTE = "gte"    # Greater than or equal
    LTE = "lte"    # Less than or equal

class MetricType(Enum):
    DAILY_COST = "daily_cost"
    WORKFLOW_COST = "workflow_cost"
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    FALLBACK_RATE = "fallback_rate"
    TOKEN_USAGE = "token_usage"

@dataclass
class AlertCondition:
    metric: MetricType
    operator: Operator
    threshold: float
    window: str | None = None  # e.g., "1h", "24h"

@dataclass
class AlertAction:
    type: str  # "webhook", "email", "stdout"
    config: dict[str, Any]

@dataclass
class AlertRule:
    name: str
    description: str
    condition: AlertCondition
    actions: list[AlertAction]
    enabled: bool = True
    cooldown_minutes: int = 60  # Don't re-alert for 1 hour

class AlertEngine:
    """Background alert monitoring engine."""

    def __init__(self, rules_file: str = ".empathy/alerts.yaml"):
        self.rules = self._load_rules(rules_file)
        self.last_triggered: dict[str, datetime] = {}

    def check_alerts(self, telemetry_store: TelemetryStore) -> None:
        """Check all alert rules against current metrics."""
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check cooldown
            if self._in_cooldown(rule):
                continue

            # Calculate metric
            value = self._calculate_metric(rule.condition, telemetry_store)

            # Check condition
            if self._evaluate_condition(rule.condition, value):
                self._trigger_alert(rule, value)

    def _trigger_alert(self, rule: AlertRule, value: float) -> None:
        """Execute alert actions."""
        for action in rule.actions:
            if action.type == "webhook":
                self._send_webhook(action, rule, value)
            elif action.type == "email":
                self._send_email(action, rule, value)
            elif action.type == "stdout":
                print(f"🚨 ALERT: {rule.name} - {value}")

        self.last_triggered[rule.name] = datetime.now()
```

### 2.3 CLI Commands

```bash
# Watch for alerts (runs in background)
attune alerts watch

# Test alert configuration
attune alerts test --rule high_daily_cost

# List configured alerts
attune alerts list

# Trigger alert manually
attune alerts trigger --rule high_daily_cost --test
```

---

## Component 3: OpenTelemetry Backend

### 3.1 Specification

**Purpose:** Export telemetry to enterprise monitoring platforms (SigNoz, Datadog, New Relic)

**Features:**
- OTEL-compatible span export
- Configurable OTLP endpoint
- Batch export (performance optimization)
- Attribute mapping (LLM-specific → OTEL semantic conventions)
- Optional dependency (`pip install attune-ai[otel]`)

**OTEL Semantic Conventions Mapping:**

| Empathy Field | OTEL Attribute | Example |
|---------------|----------------|---------|
| `provider` | `llm.provider` | `anthropic` |
| `model_id` | `llm.model` | `claude-sonnet-4-5` |
| `input_tokens` | `llm.tokens.input` | `1024` |
| `output_tokens` | `llm.tokens.output` | `256` |
| `estimated_cost` | `llm.cost` | `0.0123` |
| `latency_ms` | `llm.latency_ms` | `1200` |
| `task_type` | `llm.task.type` | `code_review` |
| `tier` | `llm.tier` | `capable` |
| `fallback_used` | `llm.fallback.used` | `true` |
| `fallback_chain` | `llm.fallback.chain` | `["anthropic", "openai"]` |

### 3.2 Implementation

```python
# src/attune/monitoring/otel_backend.py

from typing import Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from ..models.telemetry import LLMCallRecord, WorkflowRunRecord, TelemetryBackend

class OpenTelemetryBackend(TelemetryBackend):
    """Export telemetry to OpenTelemetry collectors.

    Usage:
        >>> backend = OpenTelemetryBackend(
        ...     endpoint="http://localhost:4317",
        ...     service_name="attune-ai"
        ... )
        >>> backend.log_call(llm_call_record)

    Compatible with:
        - SigNoz (https://signoz.io)
        - Datadog APM
        - New Relic
        - Any OTLP-compatible collector
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:4317",
        service_name: str = "attune-ai",
        headers: dict[str, str] | None = None,
    ):
        self.endpoint = endpoint
        self.service_name = service_name

        # Initialize OTLP exporter
        self.exporter = OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers or {},
        )

        # Setup tracer provider
        provider = TracerProvider(
            resource=Resource.create({"service.name": service_name})
        )
        provider.add_span_processor(BatchSpanProcessor(self.exporter))
        trace.set_tracer_provider(provider)

        self.tracer = trace.get_tracer(__name__)

    def log_call(self, record: LLMCallRecord) -> None:
        """Export LLM call as OTEL span."""
        with self.tracer.start_as_current_span(
            "llm_call",
            kind=trace.SpanKind.CLIENT,
            start_time=self._parse_timestamp(record.timestamp),
        ) as span:
            # Set standard OTEL attributes
            span.set_attributes({
                "llm.provider": record.provider,
                "llm.model": record.model_id,
                "llm.tokens.input": record.input_tokens,
                "llm.tokens.output": record.output_tokens,
                "llm.cost": record.estimated_cost,
                "llm.latency_ms": record.latency_ms,
                "llm.task.type": record.task_type,
                "llm.tier": record.tier,
                "llm.success": record.success,
            })

            # Add fallback tracking
            if record.fallback_used:
                span.set_attributes({
                    "llm.fallback.used": True,
                    "llm.fallback.chain": ",".join(record.fallback_chain),
                    "llm.fallback.original_provider": record.original_provider or "",
                })

            # Add error tracking
            if not record.success:
                span.set_status(Status(StatusCode.ERROR, record.error_message))
                span.set_attributes({
                    "error.type": record.error_type or "unknown",
                    "error.message": record.error_message or "",
                })

            # Add workflow context
            if record.workflow_name:
                span.set_attributes({
                    "workflow.name": record.workflow_name,
                    "workflow.step": record.step_name or "",
                })

            # Add user context
            if record.user_id:
                span.set_attribute("user.id", record.user_id)
            if record.session_id:
                span.set_attribute("session.id", record.session_id)

            # Set span duration
            span.end(
                end_time=self._parse_timestamp(record.timestamp)
                + timedelta(milliseconds=record.latency_ms)
            )

    def log_workflow(self, record: WorkflowRunRecord) -> None:
        """Export workflow run as OTEL span with child spans."""
        with self.tracer.start_as_current_span(
            "workflow_run",
            kind=trace.SpanKind.INTERNAL,
            start_time=self._parse_timestamp(record.started_at),
        ) as parent_span:
            # Set workflow-level attributes
            parent_span.set_attributes({
                "workflow.name": record.workflow_name,
                "workflow.total_cost": record.total_cost,
                "workflow.total_tokens": record.total_input_tokens + record.total_output_tokens,
                "workflow.savings": record.savings,
                "workflow.savings_percent": record.savings_percent,
                "workflow.success": record.success,
            })

            # Create child spans for each stage
            for stage in record.stages:
                with self.tracer.start_as_current_span(
                    f"workflow_stage:{stage.stage_name}",
                    kind=trace.SpanKind.INTERNAL,
                ) as stage_span:
                    stage_span.set_attributes({
                        "stage.name": stage.stage_name,
                        "stage.tier": stage.tier,
                        "stage.model": stage.model_id,
                        "stage.cost": stage.cost,
                        "stage.latency_ms": stage.latency_ms,
                        "stage.success": stage.success,
                    })

                    if stage.skipped:
                        stage_span.set_attribute("stage.skipped", True)
                        stage_span.set_attribute("stage.skip_reason", stage.skip_reason or "")

            # Set workflow end time
            if record.completed_at:
                parent_span.end(
                    end_time=self._parse_timestamp(record.completed_at)
                )
```

### 3.3 Configuration

```yaml
# .empathy/monitoring.yaml
otel:
  enabled: true
  endpoint: "http://localhost:4317"
  service_name: "attune-ai"
  headers:
    authorization: "Bearer YOUR_API_KEY"

  # Batch export settings
  batch_size: 512
  export_interval_ms: 5000
  max_queue_size: 2048

# Enable multiple backends
backends:
  - type: jsonl
    storage_dir: ".empathy"

  - type: otel
    endpoint: "http://localhost:4317"
    service_name: "empathy-prod"
```

---

## Sprint Breakdown

### Sprint 1: VSCode Panel Foundation (Week 1) - DEFAULT FEATURES

**Goal:** Zero-config VSCode telemetry panel with overview stats

**Scope:** Tier 1 (Developer Install) features only
- VSCode panel with charts and activity feed
- Reads from existing `.empathy/` JSONL files
- No alerts, no OTEL, no configuration files

**Tasks:**
1. **Setup** (2 hours)
   - [ ] Create `docs/specs/MONITORING_SYSTEM_SPEC.md`
   - [ ] Create `src/attune/monitoring/` package
   - [ ] Add Sprint 1 tracking to project board

2. **VSCode Panel Foundation** (1 day)
   - [ ] Create `TelemetryPanel.tsx` component
   - [ ] Add panel registration to VSCode extension
   - [ ] Implement JSONL file reader in TypeScript
   - [ ] Create `useTelemetryData()` hook

3. **Overview Stats** (1 day)
   - [ ] Implement `OverviewStats.tsx` (4 stat cards)
   - [ ] Calculate: total cost, call count, success rate, avg latency
   - [ ] Add date range selector (today, 7d, 30d)
   - [ ] Style with Tailwind CSS

4. **Activity Feed** (1 day)
   - [ ] Implement `ActivityFeed.tsx` component
   - [ ] Display last 20 LLM calls
   - [ ] Add filtering (by workflow, provider, tier)
   - [ ] Add click-through to workflow source file

5. **Testing & Polish** (1 day)
   - [ ] Write unit tests for telemetry parser
   - [ ] Test with sample telemetry data
   - [ ] Add loading states and error handling
   - [ ] Documentation: usage guide for panel

**Deliverables:**
- ✅ Working VSCode panel with overview stats
- ✅ Activity feed with recent calls
- ✅ Click-through to source files
- ✅ Basic filtering and date range selection

**Sprint Review:**
- Demo: Open VSCode panel, show overview stats and activity feed
- Gather feedback on UX and missing features

---

### Sprint 2: VSCode Panel Polish & Charts (Week 2) - DEFAULT FEATURES

**Goal:** Complete Tier 1 features with visualizations and polish

**Scope:** Tier 1 (Developer Install) features only
- Cost charts and visualizations
- Top workflows list
- Performance optimizations
- Complete VSCode panel (production-ready)

**Tasks:**
1. **Cost Visualizations** (1.5 days)
   - [ ] Add Chart.js dependency
   - [ ] Implement `CostChart.tsx` (line chart for cost over time)
   - [ ] Add provider breakdown pie chart
   - [ ] Add tier distribution bar chart
   - [ ] Implement `WorkflowList.tsx` (top 5 expensive workflows)

2. **VSCode Panel Enhancements** (2 days)
   - [ ] Add export to CSV functionality
   - [ ] Add settings panel (refresh interval, data retention)
   - [ ] Implement auto-refresh (configurable interval)
   - [ ] Add empty states and error boundaries
   - [ ] Performance optimization (caching, virtualization)

3. **Testing & Documentation** (1.5 days)
   - [ ] Write unit tests for all components
   - [ ] Write integration tests (JSONL → panel)
   - [ ] Performance testing (10,000 records)
   - [ ] Create user guide for VSCode panel
   - [ ] Update README with panel features
   - [ ] Record demo video (2 minutes)

**Deliverables:**
- ✅ Cost charts in VSCode panel
- ✅ Top expensive workflows list
- ✅ Export/settings/auto-refresh features
- ✅ Production-ready VSCode panel (Tier 1 complete)
- ✅ Documentation and examples

**Sprint Review:**
- Demo: Complete VSCode panel with charts and activity feed
- Review UX, performance, and feature completeness
- Gather feedback on default experience

---

### Sprint 3: Enterprise Features (Week 3) - ALERTS + OTEL

**Goal:** Tier 2 (Enterprise) opt-in features

**Scope:** Enterprise features only (explicit opt-in)
- Alert system with CLI wizard
- OTEL backend for SigNoz/Datadog
- Multi-backend support
- Enterprise documentation

**Tasks:**
1. **Alert System Foundation** (2 days)
   - [ ] Create `src/attune/monitoring/alerts.py`
   - [ ] Implement `AlertRule`, `AlertCondition`, `AlertAction` classes
   - [ ] Implement `AlertEngine` with rule evaluation
   - [ ] Create SQLite database for alert configuration
   - [ ] Implement cooldown mechanism (prevent spam)

2. **Alert CLI Wizard** (1.5 days)
   - [ ] Create `attune alerts init` interactive wizard
   - [ ] Ask 3 questions: metric, threshold, webhook URL
   - [ ] Generate alert configuration automatically
   - [ ] Start background watcher (systemd/launchd templates)
   - [ ] Add `attune alerts list`, `test`, `stop` commands

3. **Alert Actions** (1 day)
   - [ ] Implement webhook action (POST JSON to any URL)
   - [ ] Implement email action (SMTP, optional)
   - [ ] Create Slack webhook payload templates
   - [ ] Add retry logic and error handling

4. **OTEL Backend** (1.5 days)
   - [ ] Add optional dependency: `pip install attune-ai[otel]`
   - [ ] Create `src/attune/monitoring/otel_backend.py`
   - [ ] Implement `OpenTelemetryBackend` class
   - [ ] Map LLMCallRecord → OTEL span attributes
   - [ ] Environment variable configuration (no YAML required)

5. **SigNoz Integration & Testing** (2 days)
   - [ ] Test OTEL export to local SigNoz instance
   - [ ] Create Docker Compose for SigNoz quickstart
   - [ ] Write enterprise setup guide (alerts + OTEL)
   - [ ] Integration tests: Alert webhook delivery
   - [ ] Integration tests: OTEL export to SigNoz

6. **Documentation & Polish** (1 day)
   - [ ] Write `ENTERPRISE_FEATURES_GUIDE.md`
   - [ ] Document alert CLI wizard
   - [ ] Document OTEL setup with environment variables
   - [ ] Create sample alert configurations
   - [ ] Update README with Tier 1 vs Tier 2 comparison

**Deliverables:**
- ✅ Alert system with CLI wizard (Tier 2 opt-in)
- ✅ OTEL backend with environment variable config (Tier 2 opt-in)
- ✅ SigNoz integration guide
- ✅ Enterprise documentation
- ✅ Zero-config default + enterprise opt-ins working

**Sprint Review:**
- Demo: Zero-config default experience (Tier 1)
- Demo: Opt-in to alerts with `attune alerts init` (Tier 2)
- Demo: Opt-in to OTEL with env vars (Tier 2)
- Production readiness checklist

---

## Technical Requirements

### Dependencies

**Core (No new dependencies):**
- Existing: `dataclasses`, `json`, `pathlib`, `datetime`

**VSCode Extension:**
- Existing: `react`, `typescript`
- New: `chart.js` or `recharts` (visualizations)

**Optional (Monitoring extras):**
```toml
[project.optional-dependencies]
monitoring = [
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp>=1.20.0",
]
```

### File Structure

```
src/attune/monitoring/
├── __init__.py
├── alerts.py                    # Alert engine
├── otel_backend.py              # OpenTelemetry backend
├── multi_backend.py             # Composite backend
└── utils.py                     # Shared utilities

website/components/telemetry/
├── TelemetryPanel.tsx           # Main panel
├── OverviewStats.tsx            # Overview cards
├── CostChart.tsx                # Cost visualization
├── WorkflowList.tsx             # Top workflows
├── ActivityFeed.tsx             # Recent calls
├── hooks/
│   ├── useTelemetryData.ts
│   └── useTelemetryStats.ts
└── utils/
    ├── telemetryParser.ts
    └── chartHelpers.ts

docs/
├── specs/
│   └── MONITORING_SYSTEM_SPEC.md  # This file
├── guides/
│   ├── MONITORING_GUIDE.md         # User guide
│   ├── ALERTS_GUIDE.md             # Alert configuration
│   └── OTEL_INTEGRATION.md         # SigNoz setup
└── examples/
    ├── alerts.yaml                 # Sample alerts
    └── monitoring.yaml             # Sample config

tests/monitoring/
├── test_alerts.py
├── test_otel_backend.py
└── test_telemetry_panel.py
```

---

## Testing Strategy

### Unit Tests
- Alert rule evaluation logic
- OTEL attribute mapping
- Telemetry data parsing
- Chart data transformations

### Integration Tests
- End-to-end: LLM call → JSONL → VSCode panel
- End-to-end: Alert trigger → webhook delivery
- End-to-end: Telemetry → OTEL → SigNoz

### Performance Tests
- JSONL parsing with 10,000 records
- Alert evaluation with 100 rules
- OTEL batch export with 1,000 spans

### User Acceptance Tests
- VSCode panel loads in <500ms
- Charts render correctly with sample data
- Alerts trigger within 60s of threshold breach
- OTEL export visible in SigNoz dashboard

---

## Success Metrics

### Sprint 1
- [ ] VSCode panel loads telemetry data
- [ ] Overview stats match CLI output (`python -m attune.models.cli telemetry`)
- [ ] Activity feed shows recent calls
- [ ] Click-through to source files works

### Sprint 2
- [ ] Cost charts render with sample data
- [ ] Alert engine evaluates rules correctly
- [ ] Webhook successfully delivers to Slack
- [ ] CLI commands work: `attune alerts watch`

### Sprint 3
- [ ] OTEL spans visible in SigNoz dashboard
- [ ] Multi-backend sends to both JSONL and OTEL
- [ ] VSCode panel refreshes automatically
- [ ] Documentation covers all features

### Release Criteria (v3.8.0)
- [ ] All tests passing (>90% coverage)
- [ ] Documentation complete
- [ ] Video walkthrough published
- [ ] Migration guide for existing users
- [ ] Performance validated (10k records in <1s)
- [ ] Zero breaking changes to existing APIs

---

## Future Enhancements (v3.9.0+)

**Not in scope for v3.8.0, but worth considering:**

1. **Real-time Streaming**
   - WebSocket connection for live updates
   - Server-Sent Events (SSE) for activity feed

2. **Advanced Analytics**
   - Cost forecasting (predict next month's spend)
   - Anomaly detection (ML-based)
   - Custom metric queries (SQL-like)

3. **Standalone Web Dashboard**
   - Flask/FastAPI backend
   - Shareable dashboards (team view)
   - Multi-user authentication

4. **Additional Alert Channels**
   - Slack SDK integration (richer messages)
   - PagerDuty integration
   - SMS via Twilio

5. **Mobile App**
   - iOS/Android app for monitoring on-the-go
   - Push notifications for alerts

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OTEL dependency conflicts | Medium | High | Make optional, document version requirements |
| VSCode panel performance with large datasets | Medium | Medium | Implement pagination, data caching |
| Alert false positives | High | Low | Add cooldown, configurable thresholds |
| Webhook delivery failures | Medium | Medium | Add retry logic, log failures |
| User confusion about OTEL setup | Medium | Low | Detailed guide, Docker Compose examples |

---

## Questions for Stakeholder (You)

1. **VSCode Panel Priority**: Should we prioritize real-time updates (WebSocket) or is 30s polling sufficient for v3.8.0?

2. **Alert Channels**: Is webhook + email enough for v3.8.0, or should we add Slack SDK integration in Sprint 2?

3. **OTEL Adoption**: Do we expect most users to use OTEL, or will JSONL + VSCode panel be the primary workflow?

4. **Privacy**: Any concerns about users sending telemetry to external OTEL collectors? Should we add data anonymization options?

5. **Pricing Impact**: If we market this as "enterprise monitoring," should we consider a paid tier for advanced features (real-time, forecasting)?

---

## Appendix A: Sample Alert Configurations

### Example 1: Daily Cost Alert (Slack)
```yaml
alerts:
  - name: daily_cost_limit
    description: Alert when daily LLM spend exceeds $20
    condition:
      metric: daily_cost
      operator: gt
      threshold: 20.0
    actions:
      - type: webhook
        url: https://hooks.slack.com/services/T00/B00/XXX
        payload:
          text: "⚠️ Daily LLM cost exceeded $20: ${value:.2f}"
          channel: "#engineering"
```

### Example 2: Error Rate Spike (Email)
```yaml
alerts:
  - name: high_error_rate
    description: Alert when error rate exceeds 10% over 1 hour
    condition:
      metric: error_rate
      operator: gt
      threshold: 10.0
      window: 1h
    actions:
      - type: email
        to: ops-team@example.com
        subject: "LLM Error Rate Spike: {value:.1f}%"
        body: |
          Error rate exceeded 10% in the last hour.
          Current rate: {value:.1f}%

          Check the dashboard: https://monitoring.example.com
```

### Example 3: Expensive Workflow (Custom Webhook)
```yaml
alerts:
  - name: expensive_workflow
    description: Alert when single workflow costs >$10
    condition:
      metric: workflow_cost
      operator: gt
      threshold: 10.0
    actions:
      - type: webhook
        url: https://api.example.com/alerts
        payload:
          alert_type: "expensive_workflow"
          workflow_name: "{workflow_name}"
          cost: "{value:.2f}"
          timestamp: "{timestamp}"
```

---

## Appendix B: OTEL Span Example

**LLM Call Span:**
```json
{
  "traceId": "abc123...",
  "spanId": "def456...",
  "name": "llm_call",
  "kind": "CLIENT",
  "startTime": "2026-01-05T10:30:00Z",
  "endTime": "2026-01-05T10:30:01.2Z",
  "attributes": {
    "llm.provider": "anthropic",
    "llm.model": "claude-sonnet-4-5",
    "llm.tokens.input": 1024,
    "llm.tokens.output": 256,
    "llm.cost": 0.0123,
    "llm.latency_ms": 1200,
    "llm.task.type": "code_review",
    "llm.tier": "capable",
    "llm.success": true,
    "workflow.name": "code-review",
    "workflow.step": "analyze_code"
  }
}
```

**Workflow Trace:**
```json
{
  "traceId": "xyz789...",
  "spans": [
    {
      "spanId": "root...",
      "name": "workflow_run",
      "kind": "INTERNAL",
      "attributes": {
        "workflow.name": "code-review",
        "workflow.total_cost": 0.0345,
        "workflow.savings_percent": 65.2
      },
      "children": [
        {
          "spanId": "stage1...",
          "name": "workflow_stage:analyze",
          "attributes": {
            "stage.tier": "capable",
            "stage.cost": 0.0123
          }
        },
        {
          "spanId": "stage2...",
          "name": "workflow_stage:summarize",
          "attributes": {
            "stage.tier": "cheap",
            "stage.cost": 0.0022
          }
        }
      ]
    }
  ]
}
```

---

**End of Specification**

Ready to proceed with Sprint 1?
