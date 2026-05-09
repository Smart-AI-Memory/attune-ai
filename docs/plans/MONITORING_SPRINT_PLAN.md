---
description: Monitoring System - Sprint Plan & Task Tracker: **Project:** Attune AI Monitoring System (v3.8.0) **Timeline:** 3 sprints (2-3 weeks) **Status:** 🟡 Plan
---

# Monitoring System - Sprint Plan & Task Tracker

**Project:** Attune AI Monitoring System (v3.8.0)
**Timeline:** 3 sprints (2-3 weeks)
**Status:** 🟡 Planning Complete - Ready to Start

---

## Sprint 1: VSCode Panel Foundation (5 days)

**Goal:** Basic telemetry panel with overview stats and activity feed

**Start Date:** TBD
**End Date:** TBD
**Status:** ⚪ Not Started

### Day 1: Setup & Foundation

- [ ] **T1.1** Create monitoring package structure
  - Create `src/attune/monitoring/__init__.py`
  - Create `website/components/telemetry/` directory
  - Add package exports
  - **Estimate:** 1 hour

- [ ] **T1.2** Setup VSCode panel registration
  - Register new "Telemetry" panel in extension
  - Create basic panel container
  - Add navigation menu item
  - **Estimate:** 2 hours

- [ ] **T1.3** Implement JSONL parser (TypeScript)
  - Create `telemetryParser.ts`
  - Parse `.attune/llm_calls.jsonl`
  - Parse `.attune/workflow_runs.jsonl`
  - Convert to TypeScript interfaces
  - **Estimate:** 3 hours

- [ ] **T1.4** Create `useTelemetryData()` hook
  - React hook to load telemetry files
  - Handle file watch for auto-refresh
  - Error handling (file not found, parse errors)
  - **Estimate:** 2 hours

**Daily Standup Notes:**
```
What did I do yesterday: N/A (Day 1)
What will I do today: Setup package structure, panel registration, JSONL parser
Blockers: None
```

---

### Day 2: Overview Stats Component

- [ ] **T1.5** Create `OverviewStats.tsx` component
  - 4 stat cards: Total Cost, Call Count, Success Rate, Avg Latency
  - Responsive grid layout (2x2)
  - Tailwind CSS styling
  - **Estimate:** 3 hours

- [ ] **T1.6** Implement date range selector
  - Dropdown: Today, Last 7 days, Last 30 days, All time
  - Filter telemetry data by date range
  - Persist selection in local storage
  - **Estimate:** 2 hours

- [ ] **T1.7** Calculate analytics metrics
  - Total cost calculation
  - Success rate percentage
  - Average latency
  - Call count aggregation
  - **Estimate:** 2 hours

- [ ] **T1.8** Add loading and error states
  - Skeleton loaders for stats
  - Error boundary component
  - Retry mechanism
  - **Estimate:** 1 hour

**Daily Standup Notes:**
```
What did I do yesterday: Setup completed, JSONL parser working
What will I do today: Build overview stats component
Blockers: None
```

---

### Day 3: Activity Feed

- [ ] **T1.9** Create `ActivityFeed.tsx` component
  - Table view of recent LLM calls (last 20)
  - Columns: Time, Workflow, Provider, Cost, Status, Latency
  - Color-coded status (✓ success, ✗ error)
  - **Estimate:** 3 hours

- [ ] **T1.10** Implement filtering
  - Filter by workflow name (dropdown)
  - Filter by provider (Anthropic, OpenAI, Ollama)
  - Filter by tier (cheap, capable, premium)
  - Filter by status (success, error)
  - **Estimate:** 2 hours

- [ ] **T1.11** Add click-through navigation
  - Click call row → jump to workflow source file
  - Parse `workflow_name` → find file in workspace
  - Highlight relevant line if available
  - **Estimate:** 2 hours

- [ ] **T1.12** Add pagination
  - Show 20 calls per page
  - Next/Previous buttons
  - Page number indicator
  - **Estimate:** 1 hour

**Daily Standup Notes:**
```
What did I do yesterday: Overview stats working, date range selector done
What will I do today: Activity feed component
Blockers: None
```

---

### Day 4: Integration & Polish

- [ ] **T1.13** Integrate all components into `TelemetryPanel.tsx`
  - Layout: Header + Overview + Activity Feed
  - Add refresh button (manual trigger)
  - Add "Clear History" action
  - **Estimate:** 2 hours

- [ ] **T1.14** Style and UX polish
  - Consistent spacing and typography
  - Hover states and transitions
  - Dark mode support
  - Responsive design (works on narrow panels)
  - **Estimate:** 3 hours

- [ ] **T1.15** Add empty states
  - No telemetry data message
  - First-time user guidance
  - Link to documentation
  - **Estimate:** 1 hour

- [ ] **T1.16** Performance optimization
  - Memoize expensive calculations
  - Virtualize long lists (React Window)
  - Debounce filter inputs
  - **Estimate:** 2 hours

**Daily Standup Notes:**
```
What did I do yesterday: Activity feed complete with filtering
What will I do today: Integration and polish
Blockers: None
```

---

### Day 5: Testing & Documentation

- [ ] **T1.17** Write unit tests
  - Test `telemetryParser.ts` (JSONL parsing)
  - Test `useTelemetryData()` hook
  - Test stat calculations
  - Test filtering logic
  - **Coverage Goal:** >80%
  - **Estimate:** 3 hours

- [ ] **T1.18** Manual testing
  - Test with empty telemetry files
  - Test with 1,000+ records
  - Test with malformed JSONL
  - Test error scenarios
  - **Estimate:** 2 hours

- [ ] **T1.19** Write user documentation
  - Create `docs/guides/TELEMETRY_PANEL_GUIDE.md`
  - Screenshots of panel
  - Feature walkthrough
  - Troubleshooting section
  - **Estimate:** 2 hours

- [ ] **T1.20** Sprint 1 demo prep
  - Record 2-minute demo video
  - Prepare demo script
  - Create sample telemetry data
  - **Estimate:** 1 hour

**Daily Standup Notes:**
```
What did I do yesterday: Panel complete and polished
What will I do today: Testing and documentation
Blockers: None
```

---

### Sprint 1 Review Checklist

- [ ] VSCode panel loads and displays telemetry data
- [ ] Overview stats are accurate (verified against CLI)
- [ ] Activity feed shows recent calls with filtering
- [ ] Click-through to source files works
- [ ] Empty states and error handling work
- [ ] Documentation is complete
- [ ] Demo video recorded

**Sprint 1 Retrospective:**
- What went well:
- What could be improved:
- Action items for Sprint 2:

---

## Sprint 2: Charts & Alert System (5 days)

**Goal:** Add visualizations and threshold-based alerting

**Start Date:** TBD
**End Date:** TBD
**Status:** ⚪ Not Started

### Day 1: Cost Visualizations Setup

- [ ] **T2.1** Add Chart.js dependency
  - Install `chart.js` and `react-chartjs-2`
  - Configure chart defaults (theme, colors)
  - Create chart wrapper components
  - **Estimate:** 1 hour

- [ ] **T2.2** Create `CostChart.tsx` (line chart)
  - Cost over time (daily/weekly aggregation)
  - X-axis: Date, Y-axis: Cost
  - Tooltip with detailed breakdown
  - Responsive sizing
  - **Estimate:** 3 hours

- [ ] **T2.3** Add provider breakdown pie chart
  - Slice per provider (Anthropic, OpenAI, Ollama)
  - Percentage labels
  - Color-coded by provider
  - Click to filter activity feed
  - **Estimate:** 2 hours

- [ ] **T2.4** Add tier distribution bar chart
  - Bars: cheap, capable, premium
  - Show cost and call count
  - Stacked bar (input tokens vs output tokens)
  - **Estimate:** 2 hours

**Daily Standup Notes:**
```
What did I do yesterday: Sprint 1 complete
What will I do today: Add chart visualizations
Blockers: None
```

---

### Day 2: Top Workflows & Alert Engine Foundation

- [ ] **T2.5** Create `WorkflowList.tsx` component
  - List top 5 expensive workflows
  - Show: workflow name, total cost, run count, avg cost
  - Click to filter activity feed by workflow
  - **Estimate:** 2 hours

- [ ] **T2.6** Create alert engine module
  - Create `src/attune/monitoring/alerts.py`
  - Define `AlertRule`, `AlertCondition`, `AlertAction` dataclasses
  - Implement `Operator` enum (gt, lt, eq, gte, lte)
  - Implement `MetricType` enum (daily_cost, error_rate, etc.)
  - **Estimate:** 2 hours

- [ ] **T2.7** Implement `AlertEngine` class
  - Rule loading from YAML
  - Rule evaluation loop
  - Metric calculation (use TelemetryAnalytics)
  - Cooldown tracking (don't re-alert within X minutes)
  - **Estimate:** 4 hours

**Daily Standup Notes:**
```
What did I do yesterday: Charts added to panel
What will I do today: Top workflows list, alert engine foundation
Blockers: None
```

---

### Day 3: Alert Actions

- [ ] **T2.8** Implement webhook action
  - POST JSON to configurable URL
  - Template variable substitution: `{value}`, `{workflow_name}`, `{timestamp}`
  - Retry logic (3 attempts with exponential backoff)
  - Timeout handling (5 seconds)
  - **Estimate:** 3 hours

- [ ] **T2.9** Implement email action
  - SMTP integration using `smtplib`
  - Support TLS/SSL
  - Template support (subject, body)
  - HTML and plain text emails
  - **Estimate:** 3 hours

- [ ] **T2.10** Implement stdout action
  - Console logging with formatting
  - Color-coded by severity
  - Timestamp and alert name
  - **Estimate:** 1 hour

- [ ] **T2.11** Create Slack webhook templates
  - Rich message formatting (blocks, attachments)
  - Example templates for common alerts
  - Color coding (red for errors, yellow for warnings)
  - **Estimate:** 1 hour

**Daily Standup Notes:**
```
What did I do yesterday: Alert engine evaluating rules
What will I do today: Implement alert actions
Blockers: None
```

---

### Day 4: Alert CLI

- [ ] **T2.12** Add `attune alerts` CLI command group
  - Create CLI parser for alerts subcommand
  - Add to main CLI entry point
  - **Estimate:** 1 hour

- [ ] **T2.13** Implement `alerts watch` command
  - Background watcher (runs every 60s)
  - Check all rules against telemetry
  - Trigger actions when conditions met
  - Graceful shutdown (Ctrl+C)
  - **Estimate:** 3 hours

- [ ] **T2.14** Implement `alerts test` command
  - Test specific alert rule
  - Dry-run mode (don't actually send webhooks)
  - Show what would be triggered
  - **Estimate:** 2 hours

- [ ] **T2.15** Implement `alerts list` command
  - List all configured alerts
  - Show: name, condition, enabled status
  - Table format
  - **Estimate:** 1 hour

- [ ] **T2.16** Add `alerts trigger` command
  - Manually trigger alert for testing
  - Override condition (force trigger)
  - Useful for testing webhooks
  - **Estimate:** 1 hour

**Daily Standup Notes:**
```
What did I do yesterday: All alert actions working
What will I do today: Build alert CLI commands
Blockers: None
```

---

### Day 5: Testing & Documentation

- [ ] **T2.17** Write alert engine tests
  - Test rule evaluation logic
  - Test metric calculations
  - Test cooldown mechanism
  - Test condition operators (gt, lt, etc.)
  - **Coverage Goal:** >90%
  - **Estimate:** 3 hours

- [ ] **T2.18** Write alert action tests
  - Mock webhook calls (use `responses` library)
  - Mock SMTP server (use `aiosmtpd`)
  - Test retry logic
  - Test template substitution
  - **Estimate:** 3 hours

- [ ] **T2.19** Create sample alert configurations
  - `docs/examples/alerts.yaml` with 5+ examples
  - Daily cost alert
  - Error rate spike alert
  - Expensive workflow alert
  - Fallback rate alert
  - Token usage spike alert
  - **Estimate:** 1 hour

- [ ] **T2.20** Write alert documentation
  - Create `docs/guides/ALERTS_GUIDE.md`
  - Configuration syntax
  - Available metrics
  - Webhook formats (Slack, Discord, generic)
  - Troubleshooting
  - **Estimate:** 2 hours

**Daily Standup Notes:**
```
What did I do yesterday: Alert CLI complete
What will I do today: Testing and documentation
Blockers: None
```

---

### Sprint 2 Review Checklist

- [ ] Cost charts render correctly in panel
- [ ] Top workflows list shows accurate data
- [ ] Alert engine evaluates rules correctly
- [ ] Webhook successfully delivers to Slack
- [ ] Email alerts send (if SMTP configured)
- [ ] CLI commands work: `attune alerts watch`, `test`, `list`
- [ ] Documentation covers all alert types
- [ ] Sample configurations work out-of-the-box

**Sprint 2 Retrospective:**
- What went well:
- What could be improved:
- Action items for Sprint 3:

---

## Sprint 3: OpenTelemetry & Production Polish (5 days)

**Goal:** OTEL integration, performance optimization, production readiness

**Start Date:** TBD
**End Date:** TBD
**Status:** ⚪ Not Started

### Day 1: OTEL Backend Foundation

- [ ] **T3.1** Add optional OTEL dependencies
  - Update `pyproject.toml` with `[monitoring]` extra
  - Add `opentelemetry-sdk>=1.20.0`
  - Add `opentelemetry-exporter-otlp>=1.20.0`
  - **Estimate:** 30 minutes

- [ ] **T3.2** Create `otel_backend.py` module
  - Create `src/attune/monitoring/otel_backend.py`
  - Implement `OpenTelemetryBackend` class
  - Initialize OTLP exporter
  - Setup tracer provider
  - **Estimate:** 2 hours

- [ ] **T3.3** Implement `log_call()` method
  - Map `LLMCallRecord` → OTEL span
  - Set standard attributes (llm.provider, llm.model, etc.)
  - Set custom attributes (tier, task_type, fallback_chain)
  - Add error tracking (span status)
  - **Estimate:** 3 hours

- [ ] **T3.4** Implement `log_workflow()` method
  - Map `WorkflowRunRecord` → OTEL trace
  - Create parent span for workflow
  - Create child spans for each stage
  - Set workflow-level attributes (savings, cost, etc.)
  - **Estimate:** 3 hours

**Daily Standup Notes:**
```
What did I do yesterday: Sprint 2 complete
What will I do today: Build OTEL backend
Blockers: Need to test with local OTEL collector
```

---

### Day 2: Multi-Backend & Configuration

- [ ] **T3.5** Create `MultiBackend` class
  - Composite pattern: route to multiple backends
  - Implement `log_call()` → fan out to all backends
  - Implement `log_workflow()` → fan out to all backends
  - Error handling (one backend fails, others continue)
  - **Estimate:** 2 hours

- [ ] **T3.6** Create monitoring configuration
  - Create `monitoring.yaml` schema
  - Support JSONL backend config
  - Support OTEL backend config
  - Support multiple backends simultaneously
  - **Estimate:** 2 hours

- [ ] **T3.7** Implement configuration loader
  - Parse `monitoring.yaml`
  - Instantiate backends based on config
  - Validate configuration (missing fields, invalid values)
  - Provide defaults (JSONL backend if no config)
  - **Estimate:** 2 hours

- [ ] **T3.8** Update telemetry initialization
  - Auto-load backends from `monitoring.yaml`
  - Fallback to default JSONL backend
  - Log backend initialization (which backends active)
  - **Estimate:** 2 hours

**Daily Standup Notes:**
```
What did I do yesterday: OTEL backend working
What will I do today: Multi-backend support and configuration
Blockers: None
```

---

### Day 3: SigNoz Integration & Testing

- [ ] **T3.9** Setup local SigNoz instance
  - Create Docker Compose file for SigNoz
  - Start SigNoz locally
  - Verify OTLP endpoint (http://localhost:4317)
  - **Estimate:** 1 hour

- [ ] **T3.10** Test OTEL export to SigNoz
  - Run sample workflow with OTEL backend enabled
  - Verify spans appear in SigNoz UI
  - Check attribute mapping (llm.*, workflow.*)
  - Test trace hierarchy (parent + child spans)
  - **Estimate:** 2 hours

- [ ] **T3.11** Create SigNoz dashboard template
  - Export dashboard JSON from SigNoz
  - Create pre-built dashboard for Attune AI
  - Include: cost chart, latency chart, error rate
  - Save to `docs/examples/signoz_dashboard.json`
  - **Estimate:** 2 hours

- [ ] **T3.12** Write SigNoz integration guide
  - Create `docs/guides/OTEL_INTEGRATION.md`
  - Docker setup instructions
  - Configuration examples
  - Dashboard import instructions
  - Screenshots of SigNoz UI
  - **Estimate:** 3 hours

**Daily Standup Notes:**
```
What did I do yesterday: Multi-backend working
What will I do today: SigNoz integration and testing
Blockers: None
```

---

### Day 4: Performance Optimization

- [ ] **T3.13** Implement telemetry data caching
  - Cache parsed JSONL in VSCode extension state
  - Invalidate cache on file change
  - Reduce re-parsing overhead
  - **Estimate:** 2 hours

- [ ] **T3.14** Implement incremental JSONL parsing
  - Track file offset (last parsed position)
  - Only parse new lines since last read
  - Append to existing data
  - **Estimate:** 3 hours

- [ ] **T3.15** Optimize alert rule evaluation
  - Skip evaluation if no new telemetry data
  - Cache metric calculations
  - Batch rule checks (evaluate all rules once per interval)
  - **Estimate:** 2 hours

- [ ] **T3.16** Add rate limiting to webhooks
  - Prevent webhook spam (max 1 per alert per cooldown period)
  - Queue webhooks if rate limit exceeded
  - Log rate limit events
  - **Estimate:** 1 hour

**Daily Standup Notes:**
```
What did I do yesterday: SigNoz integration working
What will I do today: Performance optimizations
Blockers: None
```

---

### Day 5: VSCode Panel Enhancements & Final Polish

- [ ] **T3.17** Add export to CSV functionality
  - Export telemetry data to CSV file
  - Include: timestamp, workflow, provider, cost, latency, status
  - Open save dialog in VSCode
  - **Estimate:** 2 hours

- [ ] **T3.18** Add "Clear history" action
  - Confirmation dialog
  - Archive old data (don't delete, move to `.attune/archive/`)
  - Clear telemetry files
  - **Estimate:** 1 hour

- [ ] **T3.19** Add settings panel
  - Refresh interval (10s, 30s, 60s, manual)
  - Data retention (7d, 30d, 90d, unlimited)
  - Chart settings (theme, colors)
  - **Estimate:** 2 hours

- [ ] **T3.20** Implement auto-refresh
  - Poll telemetry files every 30s (configurable)
  - Visual indicator when refresh occurs
  - Pause auto-refresh when user is interacting
  - **Estimate:** 2 hours

- [ ] **T3.21** Final testing & bug fixes
  - Load testing: 10,000 telemetry records
  - Test all error paths
  - Fix any bugs found during testing
  - **Estimate:** 2 hours

- [ ] **T3.22** Complete documentation
  - Finalize `MONITORING_GUIDE.md`
  - Update README with monitoring features
  - Add migration guide for existing users
  - **Estimate:** 1 hour

- [ ] **T3.23** Create video walkthrough
  - 5-minute demo video
  - Show: VSCode panel, alerts, OTEL export
  - Publish to YouTube or docs site
  - **Estimate:** 2 hours

**Daily Standup Notes:**
```
What did I do yesterday: Performance optimizations complete
What will I do today: Final polish and documentation
Blockers: None
```

---

### Sprint 3 Review Checklist

- [ ] OTEL backend exports to SigNoz successfully
- [ ] Multi-backend sends to both JSONL and OTEL simultaneously
- [ ] VSCode panel has export/clear/settings features
- [ ] Auto-refresh works correctly
- [ ] Performance validated (10k records load in <1s)
- [ ] All documentation complete
- [ ] Video walkthrough published
- [ ] Zero breaking changes to existing APIs

**Sprint 3 Retrospective:**
- What went well:
- What could be improved:
- Action items for v3.9.0:

---

## Release Checklist (v3.8.0)

### Code Quality
- [ ] All unit tests passing (>90% coverage)
- [ ] All integration tests passing
- [ ] No linting errors (`ruff check`)
- [ ] Type checking passes (`mypy`)
- [ ] No security vulnerabilities (`bandit`)

### Documentation
- [ ] `MONITORING_GUIDE.md` complete
- [ ] `ALERTS_GUIDE.md` complete
- [ ] `OTEL_INTEGRATION.md` complete
- [ ] Sample configurations in `docs/examples/`
- [ ] README updated with monitoring features
- [ ] CHANGELOG updated for v3.8.0
- [ ] Migration guide for existing users

### Testing
- [ ] Manual testing on macOS
- [ ] Manual testing on Linux
- [ ] Manual testing on Windows (VSCode extension)
- [ ] Performance testing (10k records)
- [ ] Load testing (100k records)
- [ ] OTEL export verified with SigNoz
- [ ] Alert webhook verified with Slack

### Release
- [ ] Version bumped to 3.8.0 in `pyproject.toml`
- [ ] Git tag created: `v3.8.0`
- [ ] GitHub release created
- [ ] PyPI package published
- [ ] VSCode extension published
- [ ] Announcement blog post
- [ ] Social media posts (Twitter, LinkedIn)

---

## Metrics & Success Criteria

### Sprint 1 Metrics
- [ ] VSCode panel loads in <500ms
- [ ] Overview stats match CLI output (100% accuracy)
- [ ] Activity feed renders 1,000 records in <1s
- [ ] User feedback: "Easy to use" rating >4/5

### Sprint 2 Metrics
- [ ] Charts render in <200ms
- [ ] Alert evaluation completes in <100ms
- [ ] Webhook delivery success rate >99%
- [ ] User feedback: "Alerts are useful" rating >4/5

### Sprint 3 Metrics
- [ ] OTEL export adds <10ms overhead per call
- [ ] Panel auto-refresh doesn't impact IDE performance
- [ ] 10,000 telemetry records load in <1s
- [ ] User feedback: "Production ready" rating >4/5

### Overall Success Criteria
- [ ] 100+ GitHub stars within 1 month of release
- [ ] 10+ community contributions (issues, PRs, discussions)
- [ ] Featured on "Show HN" with >50 upvotes
- [ ] Mentioned in at least 1 AI newsletter
- [ ] 1,000+ PyPI downloads in first month

---

## Risk Mitigation

### Technical Risks
1. **OTEL dependency conflicts**
   - Mitigation: Make optional, document version requirements
   - Contingency: Provide Docker image with all deps

2. **VSCode panel performance**
   - Mitigation: Implement caching, pagination, virtualization
   - Contingency: Add "lightweight mode" with reduced features

3. **Alert false positives**
   - Mitigation: Add cooldown, configurable thresholds, testing mode
   - Contingency: Add "snooze" feature, machine learning for anomaly detection

### Timeline Risks
1. **Sprint 1 takes longer than expected**
   - Mitigation: Focus on core features, defer polish to Sprint 2
   - Contingency: Extend Sprint 1 to 7 days, compress Sprint 3

2. **OTEL integration complexity**
   - Mitigation: Start OTEL work early (Sprint 2 overlap)
   - Contingency: Release v3.8.0 without OTEL, add in v3.8.1

---

## Post-Release Roadmap (v3.9.0+)

### Q1 2026
- [ ] Real-time streaming (WebSocket)
- [ ] Advanced analytics (cost forecasting, anomaly detection)
- [ ] Slack SDK integration (richer messages)

### Q2 2026
- [ ] Standalone web dashboard
- [ ] Multi-user authentication
- [ ] Shareable dashboards

### Q3 2026
- [ ] Mobile app (iOS/Android)
- [ ] Push notifications
- [ ] Custom metric queries (SQL-like)

---

**Sprint Plan Status:** ✅ Complete - Ready for execution

**Next Step:** Start Sprint 1, Task T1.1 (Create monitoring package structure)
