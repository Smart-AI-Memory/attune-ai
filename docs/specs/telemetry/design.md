# Spec: Telemetry System

## Phase 2: Design

**Status**: complete

### Architecture

Lightweight local telemetry with a single hook in `BaseWorkflow._call_llm()`, atomic JSON-Lines storage, and CLI aggregators. **Privacy-first, local storage, minimal overhead.**

```
┌────────────────────────────────────────────────────────┐
│ Workflow execution (BaseWorkflow._call_llm)            │
│         │                                              │
│         │ on response received                         │
│         ▼                                              │
│ UsageTracker.track(workflow, tier, model, ...)         │
│         │                                              │
│         │ atomic append (temp + rename)                │
│         ▼                                              │
│ ~/.empathy/telemetry/usage.jsonl  ← one JSON / line    │
│         │                                              │
│  rotation @ 10 MB → usage.jsonl.1, .2, ...             │
│  retention: 90 days                                    │
└────────────────────────────────────────────────────────┘
                       ▲
                       │ read
                       │
       attune telemetry {show,savings,compare,reset,export}
```

### API changes

This is a CLI surface, not an HTTP API. The shipped commands:

#### `attune telemetry show` — recent usage overview

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

#### `attune telemetry savings` — actual savings vs. baseline

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

#### `attune telemetry compare` — two-period diff

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

#### `attune telemetry reset` — clear all data

```
⚠️  Reset Telemetry Data

This will permanently delete all local telemetry data:
  - ~/.empathy/telemetry/usage.jsonl
  - All rotated log files

Proceed? [y/N]: y

✅ Telemetry data cleared
📊 New tracking starts now
```

#### `attune telemetry export` — CSV / JSON export

```bash
# Export to CSV
attune telemetry export --format csv --output usage.csv

# Export to JSON (pretty)
attune telemetry export --format json --output usage.json

# Export date range
attune telemetry export --from 2026-01-01 --to 2026-01-31
```

### Data model changes

#### JSON Lines schema v1.0

File location: `~/.empathy/telemetry/usage.jsonl`. Each line is a JSON object representing one LLM call:

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

#### Field definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `v` | string | Yes | Schema version (semantic versioning) |
| `ts` | string | Yes | ISO 8601 timestamp with milliseconds |
| `workflow` | string | Yes | Workflow name (e.g. "code-review") |
| `stage` | string | No | Workflow stage (e.g. "analysis") |
| `tier` | string | Yes | Tier used: "CHEAP", "CAPABLE", "PREMIUM" |
| `model` | string | Yes | Model ID (e.g. "claude-sonnet-4.5") |
| `provider` | string | Yes | "anthropic", "openai", "ollama", "hybrid" |
| `cost` | float | Yes | Cost in USD (accurate to 6 decimal places) |
| `tokens.input` | int | Yes | Input tokens consumed |
| `tokens.output` | int | Yes | Output tokens generated |
| `cache.hit` | bool | Yes | Whether cache was hit |
| `cache.type` | string | No | Cache type: "hash", "hybrid", or null on miss |
| `duration_ms` | int | Yes | Call duration in milliseconds |
| `user_id` | string | Yes | SHA-256 hash of user email/identifier (privacy) |

#### Example entries

```json
// Cache hit (hash-only)
{"v":"1.0","ts":"2026-01-07T07:30:45.123Z","workflow":"code-review","stage":"analysis","tier":"CAPABLE","model":"claude-sonnet-4.5","provider":"anthropic","cost":0.015,"tokens":{"input":1500,"output":500},"cache":{"hit":true,"type":"hash"},"duration_ms":5,"user_id":"abc123..."}

// Cache miss (fresh call)
{"v":"1.0","ts":"2026-01-07T07:31:12.456Z","workflow":"security-audit","stage":"scan","tier":"CHEAP","model":"claude-haiku-4","provider":"anthropic","cost":0.002,"tokens":{"input":800,"output":300},"cache":{"hit":false},"duration_ms":1850,"user_id":"abc123..."}

// Premium tier (architecture work)
{"v":"1.0","ts":"2026-01-07T07:35:20.789Z","workflow":"refactor-plan","stage":"design","tier":"PREMIUM","model":"claude-opus-4.5","provider":"anthropic","cost":0.135,"tokens":{"input":2000,"output":1500},"cache":{"hit":false},"duration_ms":4200,"user_id":"abc123..."}

// Hybrid cache hit (semantic match)
{"v":"1.0","ts":"2026-01-07T07:40:05.321Z","workflow":"bug-predict","stage":"analysis","tier":"CAPABLE","model":"gpt-4o","provider":"openai","cost":0.012,"tokens":{"input":1200,"output":400},"cache":{"hit":true,"type":"hybrid"},"duration_ms":120,"user_id":"abc123..."}
```

#### Storage layout

```
~/.empathy/
├── telemetry/
│   ├── usage.jsonl           # Current log
│   ├── usage.jsonl.1         # Previous rotation
│   ├── usage.jsonl.2         # Older rotation
│   └── config.json           # Telemetry settings
└── cache/
    └── responses.json        # Cache storage (separate)
```

- **Format:** JSON Lines (newline-delimited JSON), UTF-8, `\n` line separator
- **Atomic writes:** write to temp file, then `rename()` (POSIX atomic)
- **Rotation:** 10 MB max per file; up to 9 rotations kept
- **Retention:** 90 days default

### UI/UX

CLI-only in v3.8.x (see "API changes" section above for command output mockups). Future v3.9.0+ enhancements include a real-time dashboard in a VSCode extension — out of scope for this spec.

### Cross-layer impact

attune-ai only.

- **Storage:** new module `src/attune/telemetry/` containing `UsageTracker`.
- **Workflows hook:** one call site in `src/attune/workflows/base.py::_call_llm()`.
- **CLI:** new commands under `attune telemetry …`.

No changes to attune-rag, attune-gui, attune-help, or attune-author.

### Tradeoffs & alternatives

#### Privacy guarantees

**What we track:** workflow name, tier, model, provider, cost, tokens, timing, cache hit/miss.
**What we never track:** prompts or responses, file paths or code content, user email (only SHA-256 hash), API keys or credentials, any PII or sensitive data.

✅ **GDPR Compliant** — local storage only, no transmission
✅ **No PII** — user IDs hashed with SHA-256
✅ **No content** — prompts / responses never stored
✅ **User control** — easy reset / export / disable
✅ **Transparent** — clear docs on what's tracked

| Option | Pros | Cons | Chosen? |
|---|---|---|---|
| Local JSON Lines, append-only | Simple, atomic, debuggable, no daemon | Requires rotation logic; growing file size | **Yes** |
| Local SQLite | Indexable, ACID | Schema migrations; harder to inspect by hand | No |
| Remote ingestion (S3 / Postgres / SaaS) | Cross-machine aggregation | Privacy nightmare; transmission risk; out of scope | No |
| In-process metrics only (Prometheus / OTel) | Standard tooling | Requires external collector; non-trivial setup | No |
| SHA-256 hashed user_id | Stable per-user, irreversible | None of consequence | **Yes** |
| Plain user email | Aggregates across machines | PII; immediate compliance problem | No |
| No user id | Simplest | Can't deduplicate same user across rotations | No |

#### Configuration

`~/.empathy/telemetry/config.json`:

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

### Implementation reference

`UsageTracker` class lives at `src/attune/telemetry/usage_tracker.py` (locations updated in shipped code; see top-of-spec drift note). Original design sketch:

```python
class UsageTracker:
    """Privacy-first local telemetry tracking."""

    def __init__(
        self,
        storage_path: Path | None = None,
        retention_days: int = 90,
        max_file_size_mb: int = 10,
    ):
        self.storage_path = storage_path or Path.home() / ".empathy" / "telemetry"
        self.log_file = self.storage_path / "usage.jsonl"
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb
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
        stage: str | None = None,
        user_id: str | None = None,
    ): ...

    def _hash_user_id(self, user_id: str) -> str:
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    async def _append_entry(self, entry: dict): ...
    async def _rotate_if_needed(self): ...
    async def get_entries(self, since=None, until=None) -> list[dict]: ...
    async def calculate_savings(self, since=None) -> dict: ...
```

Hook in `BaseWorkflow._call_llm()`:

```python
async def _call_llm(self, prompt: str, stage: str = None) -> dict:
    start_time = time.time()

    cache_hit = False
    if self.cache:
        cached = self.cache.get(cache_key)
        if cached:
            cache_hit = True
            # ... return cached

    response = await self.llm.call(prompt)

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
            duration_ms=int((time.time() - start_time) * 1000),
        )

    return response
```
