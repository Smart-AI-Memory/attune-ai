---
description: Monitoring System - Executive Summary: **Version:** 2.0 (Simplified) **Status:** Ready to implement **Timeline:** 3 weeks (3 sprints) --- ## What We're Building
---

# Monitoring System - Executive Summary

**Version:** 2.0 (Simplified)
**Status:** Ready to implement
**Timeline:** 3 weeks (3 sprints)

---

## What We're Building

A **zero-config monitoring system** with progressive enhancement:

- **Default:** Works immediately after `pip install` (no setup)
- **Enterprise:** Opt-in features for advanced users (alerts, OTEL)

---

## The Simplified Approach

### ✅ What Changed (Addressing Your Concern)

**Before (Complex):**
- Required YAML configuration files
- Multiple backends to configure
- Alerts enabled by default
- Confusing setup process

**After (Simple):**
- Zero configuration required
- Works out-of-the-box
- Alerts/OTEL are explicit opt-ins
- Progressive enhancement model

---

## Installation Tiers

### Tier 1: Developer Install (Default - Zero Config)

```bash
pip install attune-ai
attune workflow run code-review
# ✅ Telemetry works automatically
# ✅ View with: attune telemetry
# ✅ VSCode panel appears if using VSCode
```

**What's included:**
- JSONL telemetry (logged to `.empathy/`)
- CLI dashboard (`attune telemetry`)
- VSCode panel (charts, activity feed, export)

**What's NOT included:**
- ❌ NO alerts (not watching)
- ❌ NO OTEL export (not sending data externally)
- ❌ NO configuration files
- ❌ NO background processes

**Setup time:** 0 minutes

---

### Tier 2: Enterprise Install (Explicit Opt-in)

#### Feature 1: Alerts

```bash
attune alerts init  # 3-question wizard
```

**What happens:**
- Asks: What metric? (daily cost, error rate, etc.)
- Asks: What threshold? (e.g., $10)
- Asks: Where to send? (webhook URL or email)
- Starts background watcher
- Sends alerts when thresholds exceeded

**Setup time:** 1 minute

---

#### Feature 2: OTEL Export

```bash
export ATTUNE_OTEL_ENDPOINT=http://localhost:4317
pip install attune-ai[otel]
```

**What happens:**
- Telemetry sent to SigNoz/Datadog/New Relic
- JSONL telemetry still works (both enabled)

**Setup time:** 2 minutes

---

## Sprint Plan (3 Weeks)

### Sprint 1: VSCode Panel Foundation (Week 1)
**Scope:** Tier 1 features only

**Deliverables:**
- VSCode panel with overview stats
- Activity feed with filtering
- Click-through to source files
- Auto-refresh

**Demo:** Open VSCode, see telemetry panel working

---

### Sprint 2: VSCode Panel Polish (Week 2)
**Scope:** Tier 1 features only

**Deliverables:**
- Cost charts (line, pie, bar)
- Top expensive workflows list
- Export to CSV
- Settings panel
- Performance optimizations

**Demo:** Complete VSCode panel with all features

---

### Sprint 3: Enterprise Features (Week 3)
**Scope:** Tier 2 opt-in features

**Deliverables:**
- Alert system with CLI wizard
- OTEL backend with env var config
- SigNoz integration guide
- Enterprise documentation

**Demo:** Opt-in to alerts and OTEL, show full stack

---

## Key Differences from Original Plan

| Aspect | Original Plan | Simplified Plan |
|--------|---------------|-----------------|
| **Default install** | Requires config | Zero config |
| **Alerts** | Enabled by default | Explicit opt-in |
| **OTEL** | YAML configuration | Environment variables |
| **Configuration files** | Required | Optional (only for alerts) |
| **Background processes** | Always running | Only if alerts enabled |
| **Setup complexity** | High (YAML editing) | Low (CLI wizard) |
| **Developer experience** | Must configure | Just works |

---

## Feature Comparison Matrix

| Feature | Tier 1 (Default) | Tier 2 (Enterprise) |
|---------|------------------|---------------------|
| **JSONL telemetry** | ✅ Automatic | ✅ Automatic |
| **CLI dashboard** | ✅ `attune telemetry` | ✅ `attune telemetry` |
| **VSCode panel** | ✅ Automatic | ✅ Automatic |
| **Cost charts** | ✅ Built-in | ✅ Built-in |
| **Activity feed** | ✅ Built-in | ✅ Built-in |
| **Export to CSV** | ✅ Built-in | ✅ Built-in |
| **Alerts** | ❌ Not included | ✅ Via `attune alerts init` |
| **OTEL export** | ❌ Not included | ✅ Via env vars |
| **Webhook notifications** | ❌ Not included | ✅ With alerts |
| **SigNoz/Datadog** | ❌ Not included | ✅ With OTEL |
| **Configuration required** | ❌ None | ✅ Wizard or env vars |
| **Background processes** | ❌ None | ✅ If alerts enabled |

---

## User Journey

### Developer (Tier 1)

**Day 1:**
```bash
pip install attune-ai
attune workflow run code-review
```
✅ Telemetry works automatically

**Day 2:**
```bash
attune telemetry
```
✅ See cost, usage, success rate

**Day 3:**
- Open VSCode extension
✅ Panel appears with charts

**Day 4-30:**
- Continue using normally
✅ Telemetry accumulated, visible in panel

---

### Enterprise User (Tier 2)

**Week 1:** Same as Developer (Tier 1)

**Week 2:** Enable alerts
```bash
attune alerts init
# What metric? daily_cost
# Threshold? 10
# Webhook? https://hooks.slack.com/...
```
✅ Alerts now watching

**Week 3:** Enable OTEL
```bash
export ATTUNE_OTEL_ENDPOINT=http://localhost:4317
pip install attune-ai[otel]
```
✅ Data flowing to SigNoz

**Week 4+:** Full enterprise stack running
- VSCode panel for local view
- Alerts to Slack for threshold breaches
- SigNoz for enterprise dashboards

---

## Success Metrics

### Sprint 1
- [ ] VSCode panel loads in <500ms
- [ ] Overview stats match CLI output (100% accuracy)
- [ ] Zero setup required (pip install and go)

### Sprint 2
- [ ] Charts render in <200ms
- [ ] 10,000 records load in <1s
- [ ] Export to CSV works

### Sprint 3
- [ ] Alert wizard completes in <1 minute
- [ ] Webhook delivery success rate >99%
- [ ] OTEL export adds <10ms overhead

### Overall
- [ ] Default install requires 0 minutes setup
- [ ] Alert setup requires <2 minutes
- [ ] OTEL setup requires <3 minutes
- [ ] No YAML editing required
- [ ] 100+ GitHub stars within 1 month

---

## Technical Architecture (Simplified)

### Tier 1 (Default)
```
Workflow Execution → TelemetryStore (JSONL) → VSCode Panel
                                            ↘ CLI Dashboard
```

### Tier 2 (Opt-in)
```
Workflow Execution → MultiBackend → JSONL Store → VSCode/CLI
                                  ↘ OTEL Backend → SigNoz
                                  ↘ Alert Engine → Webhook/Email
```

---

## Migration from Complex to Simple

**If you have the old plan in mind:**

| Old Concept | New Concept |
|-------------|-------------|
| `.empathy/alerts.yaml` | `attune alerts init` wizard |
| `.empathy/monitoring.yaml` | Environment variables |
| Manual backend selection | Auto-enabled based on config |
| Start alert watcher manually | Auto-starts after wizard |
| Configure YAML | Answer 3 questions or set env var |

---

## Questions Answered

### Q: Do I need to configure anything?
**A:** No. `pip install attune-ai` and it works.

### Q: How do I see my telemetry?
**A:** Open VSCode extension or run `attune telemetry`

### Q: How do I enable alerts?
**A:** Run `attune alerts init` and answer 3 questions

### Q: How do I enable OTEL?
**A:** Set `ATTUNE_OTEL_ENDPOINT` and install `[otel]` extra

### Q: Do I need YAML files?
**A:** No. Use CLI wizard for alerts, env vars for OTEL

### Q: Will alerts run by default?
**A:** No. Only if you run `attune alerts init`

### Q: Will OTEL export by default?
**A:** No. Only if you set env vars and install `[otel]`

### Q: Is there a background process?
**A:** Only if you enable alerts

---

## Next Steps

1. **Review this summary** - Ensure alignment
2. **Approve to start Sprint 1** - Begin implementation
3. **I'll create the monitoring package** - Start coding

**Ready to proceed?**

---

## Files Created

- ✅ [MONITORING_SYSTEM_SPEC.md](./MONITORING_SYSTEM_SPEC.md) - Full technical specification (569 lines)
- ✅ [MONITORING_SPRINT_PLAN.md](./MONITORING_SPRINT_PLAN.md) - Detailed sprint tasks (600+ lines)
- ✅ [MONITORING_SUMMARY.md](./MONITORING_SUMMARY.md) - This document (executive summary)

**All documentation is complete and ready for implementation.**
