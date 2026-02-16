---
description: Telemetry System Design: **Version**: 1.0 (for v3.8.2) **Status**: Design Phase **Privacy**: Local-only, no PII/prompts/responses --- ## Overview Lightweight lo
---

# Telemetry System Design

**Version**: 1.0 (for v3.8.2)
**Status**: Design Phase
**Privacy**: Local-only, no PII/prompts/responses

---

## Overview

Lightweight local telemetry tracking to measure **actual** cost savings per user. Enables personalized savings reports based on real usage patterns.

**Core Principle**: Privacy-first, local storage, minimal overhead.

---

## JSON Lines Schema

### File Location
```
~/.empathy/telemetry/usage.jsonl
```

### Schema v1.0

Each line is a JSON object representing one LLM call:

```json
{
  "v": "1.0",
  "ts": "2026-01-07T07:30:45.123Z",
  "workflow": "code-review",
  "stage": "analysis",
  "tier": "CAPABLE",
  "model": "claude-sonnet-4.5",
  "provider": "anthropic",
  "cost": 0.015,
  "tokens": {
    "input": 1500,
    "output": 500
  },
  "cache": {
    "hit": false,
    "type": "hash"
  },
  "duration_ms": 2340,
  "user_id": "sha256_hash"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `v` | string | Yes | Schema version (semantic versioning) |
| `ts` | string | Yes | ISO 8601 timestamp with milliseconds |
| `workflow` | string | Yes | Workflow name (e.g., "code-review", "security-audit") |
| `stage` | string | No | Workflow stage (e.g., "analysis", "recommendations") |
| `tier` | string | Yes | Tier used: "CHEAP", "CAPABLE", "PREMIUM" |
| `model` | string | Yes | Model ID (e.g., "claude-sonnet-4.5", "gpt-4o") |
| `provider` | string | Yes | Provider: "anthropic", "openai", "ollama", "hybrid" |
| `cost` | float | Yes | Cost in USD (accurate to 6 decimal places) |
| `tokens.input` | int | Yes | Input tokens consumed |
| `tokens.output` | int | Yes | Output tokens generated |
| `cache.hit` | bool | Yes | Whether cache was hit |
| `cache.type` | string | No | Cache type: "hash", "hybrid", or null if miss |
| `duration_ms` | int | Yes | Call duration in milliseconds |
| `user_id` | string | Yes | SHA256 hash of user email/identifier (privacy) |

### Privacy Guarantees

**What We Track:**
- Workflow name, tier, model, provider
- Cost, tokens, timing
- Cache hit/miss status

**What We NEVER Track:**
- Prompts or responses
- File paths or code content
- User email (only SHA256 hash)
- API keys or credentials
- Any PII or sensitive data

---

## Example Entries

### 1. Cache Hit (Hash-Only)
```json
{"v":"1.0","ts":"2026-01-07T07:30:45.123Z","workflow":"code-review","stage":"analysis","tier":"CAPABLE","model":"claude-sonnet-4.5","provider":"anthropic","cost":0.015,"tokens":{"input":1500,"output":500},"cache":{"hit":true,"type":"hash"},"duration_ms":5,"user_id":"abc123..."}
```

### 2. Cache Miss (Fresh Call)
```json
{"v":"1.0","ts":"2026-01-07T07:31:12.456Z","workflow":"security-audit","stage":"scan","tier":"CHEAP","model":"claude-haiku-4","provider":"anthropic","cost":0.002,"tokens":{"input":800,"output":300},"cache":{"hit":false},"duration_ms":1850,"user_id":"abc123..."}
```

### 3. Premium Tier (Architecture Work)
```json
{"v":"1.0","ts":"2026-01-07T07:35:20.789Z","workflow":"refactor-plan","stage":"design","tier":"PREMIUM","model":"claude-opus-4.5","provider":"anthropic","cost":0.135,"tokens":{"input":2000,"output":1500},"cache":{"hit":false},"duration_ms":4200,"user_id":"abc123..."}
```

### 4. Hybrid Cache Hit (Semantic Match)
```json
{"v":"1.0","ts":"2026-01-07T07:40:05.321Z","workflow":"bug-predict","stage":"analysis","tier":"CAPABLE","model":"gpt-4o","provider":"openai","cost":0.012,"tokens":{"input":1200,"output":400},"cache":{"hit":true,"type":"hybrid"},"duration_ms":120,"user_id":"abc123..."}
```

---

## Storage Implementation

### File Format
- **Format**: JSON Lines (newline-delimited JSON)
- **Encoding**: UTF-8
- **Line Separator**: `\n` (Unix-style)
- **Atomic Writes**: Write to temp file, then rename (POSIX atomic)

### Rotation & Retention
```python
# Default retention: 90 days
# Max file size: 10 MB (auto-rotate)
# Rotated files: usage.jsonl.1, usage.jsonl.2, etc.
```

### File Structure
```
~/.empathy/
├── telemetry/
│   ├── usage.jsonl           # Current log
│   ├── usage.jsonl.1         # Previous rotation
│   ├── usage.jsonl.2         # Older rotation
│   └── config.json           # Telemetry settings
└── cache/
    └── responses.json         # Cache storage (separate)
```

---

## CLI Commands Design

### 1. `attune telemetry show`

**Purpose**: Show recent usage overview

**Output**:
```
Attune AI Telemetry Report
Period: Last 7 days (Jan 1-7, 2026)

📊 Usage Summary
  Total Calls:        245
  Total Cost:         $3.42
  Avg Cost/Call:      $0.014

💰 Cost by Tier
  CHEAP:      120 calls   $0.60  (17.5%)
  CAPABLE:    95 calls    $1.43  (41.8%)
  PREMIUM:    30 calls    $1.39  (40.6%)

🎯 Top Workflows
  1. code-review      82 calls   $1.15
  2. security-audit   63 calls   $0.78
  3. refactor-plan    28 calls   $0.92

📦 Cache Performance
  Hit Rate:     42.3% (104/245)
  Hash Hits:    87 (84%)
  Hybrid Hits:  17 (16%)

💾 Data stored locally at: ~/.empathy/telemetry/usage.jsonl
```

### 2. `attune telemetry savings`

**Purpose**: Calculate actual savings vs baseline

**Output**:
```
Cost Savings Analysis
Period: Last 30 days

🎯 Your Usage Pattern
  PREMIUM:    12% (30 calls)
  CAPABLE:    39% (95 calls)
  CHEAP:      49% (120 calls)

💰 Actual Savings
  Without tier routing:  $15.20  (all PREMIUM)
  With tier routing:     $3.42   (smart routing)

  YOUR SAVINGS:          $11.78  (77.5%)

📊 Role Estimate: Mid-Level Developer
  (Based on your 12% PREMIUM, 39% CAPABLE, 49% CHEAP distribution)

  Expected savings for your role: 73-77%
  Your actual savings:             77.5% ✅

💡 Savings Breakdown
  Tier Routing:         77.5%  ($11.78 saved)
  Cache Hits (42%):     +18.2% ($0.62 saved)

  TOTAL SAVINGS:        95.7%  ($12.40 saved)

🔍 See detailed analysis: attune telemetry compare
```

### 3. `attune telemetry compare`

**Purpose**: Compare different time periods

**Output**:
```
Telemetry Comparison
Period 1: Dec 1-31, 2025
Period 2: Jan 1-31, 2026

                    Dec 2025    Jan 2026    Change
Total Calls         189         245         +29.6%
Total Cost          $4.12       $3.42       -17.0% ⬇️
Avg Cost/Call       $0.022      $0.014      -36.4% ⬇️

Tier Distribution
  PREMIUM          18%         12%          -6pp
  CAPABLE          42%         39%          -3pp
  CHEAP            40%         49%          +9pp

Cache Hit Rate     28.3%       42.3%        +14pp ⬆️

Top Cost Reduction: Increased CHEAP tier usage (+9pp)
Recommendation: Cache is working well - keep it enabled!
```

### 4. `attune telemetry reset`

**Purpose**: Clear all telemetry data

**Output**:
```
⚠️  Reset Telemetry Data

This will permanently delete all local telemetry data:
  - ~/.empathy/telemetry/usage.jsonl
  - All rotated log files

Proceed? [y/N]: y

✅ Telemetry data cleared
📊 New tracking starts now
```

### 5. `attune telemetry export`

**Purpose**: Export data for external analysis

**Output**:
```bash
# Export to CSV
attune telemetry export --format csv --output usage.csv

# Export to JSON (pretty)
attune telemetry export --format json --output usage.json

# Export date range
attune telemetry export --from 2026-01-01 --to 2026-01-31
```

---

## Integration Points

### 1. BaseWorkflow._call_llm()

**Hook Location**: After LLM response received

```python
# In src/attune/workflows/base.py
async def _call_llm(self, prompt: str, stage: str = None) -> dict:
    start_time = time.time()

    # Existing cache check
    cache_hit = False
    if self.cache:
        cached = self.cache.get(cache_key)
        if cached:
            cache_hit = True
            # ... return cached

    # Make LLM call
    response = await self.llm.call(prompt)

    # NEW: Track telemetry
    if self.enable_telemetry:  # Default: True
        await self._track_usage(
            workflow=self.__class__.__name__,
            stage=stage,
            tier=self._get_tier(),
            model=response.model,
            provider=response.provider,
            cost=response.cost,
            tokens=response.tokens,
            cache_hit=cache_hit,
            cache_type=self.cache.type if cache_hit else None,
            duration_ms=int((time.time() - start_time) * 1000)
        )

    return response
```

### 2. UsageTracker Class

**Location**: `src/attune/telemetry/usage_tracker.py`

```python
from pathlib import Path
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional

class UsageTracker:
    """Privacy-first local telemetry tracking."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        retention_days: int = 90,
        max_file_size_mb: int = 10
    ):
        self.storage_path = storage_path or Path.home() / ".empathy" / "telemetry"
        self.log_file = self.storage_path / "usage.jsonl"
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb

        # Create directory if needed
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def track(
        self,
        workflow: str,
        tier: str,
        model: str,
        provider: str,
        cost: float,
        tokens: dict,
        cache: dict,
        duration_ms: int,
        stage: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Track a single LLM call."""
        entry = {
            "v": "1.0",
            "ts": datetime.utcnow().isoformat() + "Z",
            "workflow": workflow,
            "tier": tier,
            "model": model,
            "provider": provider,
            "cost": round(cost, 6),
            "tokens": tokens,
            "cache": cache,
            "duration_ms": duration_ms,
            "user_id": self._hash_user_id(user_id or "default")
        }

        if stage:
            entry["stage"] = stage

        # Atomic append
        await self._append_entry(entry)

        # Rotation check
        await self._rotate_if_needed()

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    async def _append_entry(self, entry: dict):
        """Atomically append entry to log."""
        # Write to temp file
        temp_file = self.log_file.with_suffix(".tmp")
        with open(temp_file, "a") as f:
            f.write(json.dumps(entry, separators=(',', ':')) + "\n")

        # Atomic rename (POSIX)
        temp_file.replace(self.log_file)

    async def _rotate_if_needed(self):
        """Rotate log if size exceeds limit."""
        if not self.log_file.exists():
            return

        size_mb = self.log_file.stat().st_size / (1024 * 1024)
        if size_mb > self.max_file_size_mb:
            # Rotate: usage.jsonl -> usage.jsonl.1
            for i in range(9, 0, -1):
                old = self.log_file.with_suffix(f".jsonl.{i}")
                new = self.log_file.with_suffix(f".jsonl.{i+1}")
                if old.exists():
                    old.rename(new)

            self.log_file.rename(self.log_file.with_suffix(".jsonl.1"))

    async def get_entries(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> list[dict]:
        """Read entries from log."""
        entries = []

        # Read all log files (current + rotated)
        for log_file in sorted(self.storage_path.glob("usage.jsonl*")):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry["ts"].rstrip("Z"))

                    if since and ts < since:
                        continue
                    if until and ts > until:
                        continue

                    entries.append(entry)

        return entries

    async def calculate_savings(
        self,
        since: Optional[datetime] = None
    ) -> dict:
        """Calculate actual savings from telemetry data."""
        entries = await self.get_entries(since=since)

        if not entries:
            return {"error": "No telemetry data available"}

        # Calculate actual cost
        actual_cost = sum(e["cost"] for e in entries)

        # Calculate baseline cost (all PREMIUM)
        baseline_cost = len(entries) * 0.45  # Assuming $0.45/task

        # Tier distribution
        tier_counts = {"CHEAP": 0, "CAPABLE": 0, "PREMIUM": 0}
        for e in entries:
            tier_counts[e["tier"]] += 1

        total_calls = len(entries)
        tier_pct = {
            tier: round(count / total_calls * 100, 1)
            for tier, count in tier_counts.items()
        }

        # Cache stats
        cache_hits = sum(1 for e in entries if e["cache"]["hit"])
        cache_rate = round(cache_hits / total_calls * 100, 1)

        return {
            "period_days": (datetime.utcnow() - since).days if since else 30,
            "total_calls": total_calls,
            "actual_cost": round(actual_cost, 2),
            "baseline_cost": round(baseline_cost, 2),
            "savings": round(baseline_cost - actual_cost, 2),
            "savings_pct": round((1 - actual_cost / baseline_cost) * 100, 1),
            "tier_distribution": tier_pct,
            "cache_hit_rate": cache_rate
        }
```

---

## Configuration

**Location**: `~/.empathy/telemetry/config.json`

```json
{
  "enabled": true,
  "retention_days": 90,
  "max_file_size_mb": 10,
  "user_id": "user@example.com",
  "privacy": {
    "hash_user_id": true,
    "track_workflow_names": true,
    "track_model_names": true,
    "track_costs": true
  }
}
```

---

## Implementation Phases

### Phase 1: Core Tracking (Tomorrow Morning)
- [ ] Create `UsageTracker` class
- [ ] Integrate into `BaseWorkflow._call_llm()`
- [ ] Write telemetry entries to JSON Lines
- [ ] Test with manual workflow execution

### Phase 2: CLI Commands (Tomorrow Afternoon)
- [ ] `attune telemetry show` - basic stats
- [ ] `attune telemetry savings` - savings calculation
- [ ] `attune telemetry reset` - clear data
- [ ] Rich formatting with tables/charts

### Phase 3: Advanced Features (Later This Week)
- [ ] `attune telemetry compare` - period comparison
- [ ] `attune telemetry export` - CSV/JSON export
- [ ] Automatic rotation testing
- [ ] Privacy audit

### Phase 4: Testing & Validation (Next Week)
- [ ] Run real workflows for 1 week
- [ ] Validate savings calculations
- [ ] Test rotation/retention
- [ ] Document findings

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/telemetry/test_usage_tracker.py
async def test_track_entry():
    tracker = UsageTracker(storage_path=tmp_path)
    await tracker.track(
        workflow="code-review",
        tier="CAPABLE",
        model="claude-sonnet-4.5",
        provider="anthropic",
        cost=0.015,
        tokens={"input": 1500, "output": 500},
        cache={"hit": False},
        duration_ms=2340
    )

    entries = await tracker.get_entries()
    assert len(entries) == 1
    assert entries[0]["tier"] == "CAPABLE"
```

### Integration Tests
```python
# tests/integration/test_telemetry_integration.py
async def test_workflow_tracks_usage():
    workflow = CodeReviewWorkflow(enable_telemetry=True)
    await workflow.execute(diff="...", files_changed=["test.py"])

    tracker = UsageTracker()
    entries = await tracker.get_entries()
    assert len(entries) > 0
    assert entries[0]["workflow"] == "CodeReviewWorkflow"
```

---

## Privacy Compliance

✅ **GDPR Compliant**: Local storage only, no transmission
✅ **No PII**: User IDs hashed with SHA256
✅ **No Content**: Prompts/responses never stored
✅ **User Control**: Easy reset/export/disable
✅ **Transparent**: Clear docs on what's tracked

---

## Future Enhancements (v3.9.0+)

1. **Dashboard Integration**: Real-time charts in VSCode extension
2. **Team Aggregation**: Anonymous team-level statistics
3. **Anomaly Detection**: Alert on cost spikes
4. **Optimization Suggestions**: "Switch to CHEAP tier for X workflow"
5. **Export to Analytics**: Optional export to user's BI tools

---

**Next Steps**: Implement Phase 1 tomorrow morning (UsageTracker + BaseWorkflow integration)
