---
type: task
name: ops-dashboard-task
feature: ops-dashboard
depth: task
generated_at: 2026-05-21T03:19:56.082581+00:00
source_hash: 70c9679ee8d985ef96c30f885e28ddd1a4c9216d86c485efecac67f77809fb67
status: generated
---

# Work with ops dashboard

Use the ops dashboard when you need to monitor workflow operations, track costs, or manage running processes through a local web interface with real-time updates.

## Prerequisites

- Python environment with attune installed
- Access to the project source code in `src/attune/ops/`
- Admin API key for Anthropic cost reporting (optional, for cost features)

## Start the dashboard

1. **Launch the dashboard server.**
   Run the ops dashboard from your project root:
   ```bash
   python -m attune.ops
   ```
   Or use the CLI subcommand:
   ```bash
   attune ops
   ```

2. **Access the web interface.**
   Open `http://127.0.0.1:8765` in your browser. The dashboard loads with:
   - Workflow runner with scope picker
   - Cost tracking from Anthropic admin API
   - Session history and telemetry
   - Real-time SSE log streaming

3. **Configure dashboard settings.**
   Modify the dashboard configuration by editing the config parameters:
   - Host and port: Default `127.0.0.1:8765`
   - Project root: Auto-detected from current directory
   - Spec roots: Configured via `Config.specs_roots`
   - Retention policy: `runs_retention_days` (default 30)

## Monitor costs and usage

1. **View cost summaries.**
   Check the cost panel for:
   - Today's usage in USD
   - 7-day and 30-day trends
   - Month-to-date totals
   - Breakdown by model and cost type

2. **Handle cost fetch errors.**
   If cost data fails to load, check:
   - Admin API key availability via `load_admin_key()`
   - Network connectivity to `api.anthropic.com`
   - API rate limits and authentication

3. **Clear cached data.**
   Reset cost cache when testing or troubleshooting:
   ```python
   from attune.ops.anthropic_cost import clear_cache
   clear_cache()
   ```

## Track workflow sessions

1. **Review session history.**
   The sessions page shows:
   - Claude Code session IDs and timestamps
   - Message counts and duration
   - Starting prompts and activity patterns

2. **Analyze telemetry data.**
   Check telemetry summaries for:
   - Total requests and costs
   - Cost savings from workflow optimization
   - Usage patterns by workflow type
   - Daily activity trends

## Detect completion candidates

1. **Enable candidate detection.**
   Set `specs_candidates_enabled: true` in your config to scan for specs ready for completion.

2. **Review detected candidates.**
   The dashboard identifies specs with:
   - Status progression indicators
   - Evidence of completion readiness
   - Current phase and next steps

## Verification

The ops dashboard is working correctly when:
- Web interface loads at the configured host/port
- Cost data appears (if admin key is configured)
- Workflow scope picker shows your project features
- Session history displays recent Claude Code activity
- Real-time logs stream during workflow execution
