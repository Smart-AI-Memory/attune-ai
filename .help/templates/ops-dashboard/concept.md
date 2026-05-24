---
type: concept
name: ops-dashboard-concept
feature: ops-dashboard
depth: concept
generated_at: 2026-05-21T03:19:56.072840+00:00
source_hash: 70c9679ee8d985ef96c30f885e28ddd1a4c9216d86c485efecac67f77809fb67
status: generated
---

# Ops Dashboard

The ops dashboard is a web interface that runs workflows, tracks their progress, and provides operational insights into your project's AI activity.

## Core capabilities

**Workflow execution**: Run any workflow from the dashboard with a scope picker that filters available options by project features. Each run streams logs in real-time and persists its history for later review.

**Cost monitoring**: Display usage costs from the Anthropic admin API, broken down by day, model, and cost type. The dashboard caches this data locally and refreshes on demand.

**Session tracking**: Show active Claude Code sessions with duration, message counts, and starter prompts. This gives you visibility into how AI tools are being used across your project.

**Spec completion detection**: Identify workflow specifications that appear ready for the next phase based on their current status and file contents.

## Architecture overview

The dashboard runs as a FastAPI application on `127.0.0.1:8765` by default. You start it with `python -m attune.ops` or `attune ops`.

**Configuration**: The `Config` class determines where the dashboard reads project state from, which directories to scan for specs, and operational settings like run retention and trusted hosts.

**Cost data**: `CostSummary` structures hold account-level spending data fetched from Anthropic's admin API. The `CostFetchError` class categorizes fetch failures when the API is unavailable or credentials are missing.

**Workflow intelligence**: The dashboard scans your spec directories to detect completion candidates - workflows that have reached a natural stopping point and might benefit from moving to the next phase.

**Telemetry**: `TelemetrySummary` aggregates request counts, costs, and savings across workflows, providing insight into which parts of your project generate the most AI activity.

## Data persistence

The dashboard stores operational data in your attune home directory:

- Run history persists for 30 days by default (configurable via `runs_retention_days`)
- Cost data caches to reduce API calls to Anthropic
- Session information tracks Claude Code usage patterns
- Spec completion dismissals remember which candidates you've already reviewed

## Integration points

The ops dashboard connects to several parts of the attune ecosystem:

| Component | Connection | Purpose |
|-----------|------------|---------|
| Workflow runner | Direct execution | Run workflows from the web interface |
| Scope picker | Feature detection | Filter workflows by project areas |
| Anthropic API | Cost reporting | Monitor usage and spending |
| Claude Code | Session tracking | Visibility into AI tool usage |
| Spec detector | Completion analysis | Identify workflows ready for next phase |

The dashboard serves as the operational control center, giving you a unified view of workflow execution, cost management, and project AI activity.
