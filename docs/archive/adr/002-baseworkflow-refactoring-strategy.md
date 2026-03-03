---
description: ADR-002: BaseWorkflow Refactoring Strategy: ## Status **Proposed** - January 26, 2026 ### Supersedes This ADR extends [ADR-001: Workflow Engine Architecture Rev
---

# ADR-002: BaseWorkflow Refactoring Strategy

## Status

**Proposed** - January 26, 2026

### Supersedes

This ADR extends [ADR-001: Workflow Engine Architecture Review](001-workflow-engine-architecture.md), which completed CachingMixin and TelemetryMixin extraction.

## Context

The `BaseWorkflow` class in `src/attune/workflows/base.py` remains a complex class at 2,300+ lines despite recent mixin extractions (CachingMixin, TelemetryMixin). While the public API is simple (subclasses only override `run_stage`), internal complexity creates maintenance challenges:

### Current Architecture Problems

| Issue | Impact | Lines | Severity |
|-------|--------|-------|----------|
| **Tier routing embedded in `_call_llm()`** | Hard to test routing logic | ~150 | HIGH |
| **12+ constructor parameters** | Poor discoverability | 1 method | MEDIUM |
| **File-based history** | No concurrency, slow queries | 217-364 | HIGH |
| **Mixed concerns in execute()** | Hard to reason about flow | ~200 | MEDIUM |
| **Dual ModelTier enums** | Confusing imports, technical debt | 83-92 | LOW |

### Deployment Context

- **Current**: Local development only
- **Future**: CI/CD pipelines with concurrent workflow execution
- **Scale**: 100+ workflow runs per day (projected)

### Why Now?

ADR-001 deferred BaseWorkflow refactoring, but recent analysis shows:

1. **Maintenance burden increasing**: 3 bugs in past 2 weeks related to tier routing
2. **Testing difficulty**: Integration tests pass, unit tests for routing logic don't exist
3. **Scaling blocked**: File-based history prevents concurrent execution
4. **Alignment with Anthropic patterns**: Claude Code uses Strategy pattern for task routing

## Decision

Implement a **phased refactoring** with four parallel tracks:

### Track 1: Extract Tier Routing (Priority: HIGH)
### Track 2: Migrate History to SQLite (Priority: HIGH)
### Track 3: Simplify Constructor (Priority: MEDIUM)
### Track 4: Remove Dual Enums (Priority: LOW)

Each track is independent and can be implemented/reverted separately.

---

## Track 1: Extract Tier Routing to Strategy Pattern

### Problem

Current tier routing is embedded in `_call_llm()`:

```python
# Current: Hard to test, hard to customize
def _call_llm(self, system: str, user_message: str, tier: ModelTier):
    # 150 lines of routing, caching, calling, telemetry
    model = self.get_model_for_tier(tier)
    # ... complex logic
```

### Solution: Strategy Pattern

```python
# New file: src/attune/workflows/routing.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RoutingContext:
    """Context for routing decisions."""
    task_type: str
    input_size: int  # Token count estimate
    complexity: str  # "simple" | "moderate" | "complex"
    budget_remaining: float  # USD
    latency_sensitivity: str  # "low" | "medium" | "high"

class TierRoutingStrategy(ABC):
    """Strategy for routing tasks to model tiers."""

    @abstractmethod
    def route(self, context: RoutingContext) -> ModelTier:
        """Route task to appropriate tier."""
        pass

    @abstractmethod
    def can_fallback(self, tier: ModelTier) -> bool:
        """Whether fallback to cheaper tier is allowed."""
        pass


class CostOptimizedRouting(TierRoutingStrategy):
    """Routes to cheapest tier that can handle the task.

    Default strategy. Prioritizes cost savings over speed.
    """

    def route(self, context: RoutingContext) -> ModelTier:
        # Simple: CHEAP
        # Moderate: CAPABLE
        # Complex: PREMIUM
        if context.complexity == "simple":
            return ModelTier.CHEAP
        elif context.complexity == "complex":
            return ModelTier.PREMIUM
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        return tier != ModelTier.CHEAP


class PerformanceOptimizedRouting(TierRoutingStrategy):
    """Routes to fastest tier regardless of cost.

    Use for latency-sensitive workflows (interactive tools).
    """

    def route(self, context: RoutingContext) -> ModelTier:
        if context.latency_sensitivity == "high":
            return ModelTier.PREMIUM  # Fastest
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        return False  # Never fallback for performance


class BalancedRouting(TierRoutingStrategy):
    """Balances cost and performance with budget awareness.

    Adjusts tier selection based on remaining budget.
    """

    def __init__(self, total_budget: float):
        self.total_budget = total_budget

    def route(self, context: RoutingContext) -> ModelTier:
        budget_ratio = context.budget_remaining / self.total_budget

        if budget_ratio < 0.2:  # <20% budget left
            return ModelTier.CHEAP
        elif budget_ratio > 0.7 and context.complexity == "complex":
            return ModelTier.PREMIUM
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        return True


class HybridRouting(TierRoutingStrategy):
    """Uses per-tier model configuration from workflows.yaml.

    Allows mixing providers (e.g., Haiku + GPT-4 + o1).
    """

    def __init__(self, tier_config: dict[str, str]):
        self.tier_config = tier_config

    def route(self, context: RoutingContext) -> ModelTier:
        # User explicitly configured tier mappings
        # Just return appropriate tier based on complexity
        if context.complexity == "simple":
            return ModelTier.CHEAP
        elif context.complexity == "complex":
            return ModelTier.PREMIUM
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        return True
```

### Integration with BaseWorkflow

```python
# In BaseWorkflow.__init__
def __init__(
    self,
    routing_strategy: TierRoutingStrategy | None = None,
    # ... other params
):
    self.routing = routing_strategy or CostOptimizedRouting()
    # ... rest of init


# In workflow execution
def _call_llm(self, system: str, user_message: str, task_type: str):
    # Prepare routing context
    context = RoutingContext(
        task_type=task_type,
        input_size=self._estimate_tokens(system + user_message),
        complexity=self._infer_complexity(task_type),
        budget_remaining=self._get_remaining_budget(),
        latency_sensitivity=self.config.latency_sensitivity,
    )

    # Route task
    tier = self.routing.route(context)
    model = self.get_model_for_tier(tier)

    # ... rest of LLM calling logic
```

### Benefits

1. **Testable in isolation**: Each strategy can be unit tested
2. **Pluggable**: Users can implement custom routing
3. **A/B testable**: Compare CostOptimized vs Balanced
4. **Fallback logic centralized**: `can_fallback()` clarifies policy

### Migration Path

1. Create `routing.py` with strategies
2. Add `routing_strategy` parameter to `BaseWorkflow.__init__` (default: `CostOptimizedRouting()`)
3. Refactor `_call_llm()` to use strategy
4. Add tests for each strategy
5. Document custom strategy implementation in docs

### Backwards Compatibility

✅ No breaking changes - default behavior unchanged.

---

## Track 2: Migrate History to SQLite

### Problem

Current file-based history (`workflow_runs.json`):

```python
# Current limitations:
# - No concurrent writes (race conditions)
# - Linear scan for queries (slow at 1000+ runs)
# - No filtering capability
# - No indexes
# - Limited to 100 runs (max_history)
```

### Solution: SQLite with Structured Storage

```python
# New file: src/attune/workflows/history.py
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

class WorkflowHistoryStore:
    """SQLite-backed workflow history with migrations.

    Provides concurrent-safe storage with fast queries.
    """

    SCHEMA_VERSION = 1
    DEFAULT_DB = ".empathy/history.db"

    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        """Create schema if needed."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                success INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                baseline_cost REAL NOT NULL,
                savings REAL NOT NULL,
                savings_percent REAL NOT NULL,
                error TEXT,
                xml_parsed INTEGER DEFAULT 0,
                summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_stages (
                stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                tier TEXT NOT NULL,
                skipped INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0.0,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
            )
        """)

        # Indexes for common queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_name
            ON workflow_runs(workflow_name)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_started_at
            ON workflow_runs(started_at DESC)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider
            ON workflow_runs(provider)
        """)

        self.conn.commit()

    def record_run(self, run_id: str, workflow_name: str, provider: str, result: WorkflowResult):
        """Record a workflow execution."""
        cursor = self.conn.cursor()

        # Insert run record
        cursor.execute("""
            INSERT INTO workflow_runs (
                run_id, workflow_name, provider, success,
                started_at, completed_at, duration_ms,
                total_cost, baseline_cost, savings, savings_percent,
                error, xml_parsed, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            workflow_name,
            provider,
            1 if result.success else 0,
            result.started_at.isoformat(),
            result.completed_at.isoformat(),
            result.total_duration_ms,
            result.cost_report.total_cost,
            result.cost_report.baseline_cost,
            result.cost_report.savings,
            result.cost_report.savings_percent,
            result.error,
            1 if isinstance(result.final_output, dict) and result.final_output.get("xml_parsed") else 0,
            result.final_output.get("summary") if isinstance(result.final_output, dict) else None,
        ))

        # Insert stage records
        for stage in result.stages:
            cursor.execute("""
                INSERT INTO workflow_stages (
                    run_id, stage_name, tier, skipped, cost, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                stage.name,
                stage.tier.value,
                1 if stage.skipped else 0,
                stage.cost,
                stage.duration_ms,
            ))

        self.conn.commit()

    def query_runs(
        self,
        workflow_name: str | None = None,
        provider: str | None = None,
        since: datetime | None = None,
        success_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        """Query workflow runs with flexible filters."""
        query = "SELECT * FROM workflow_runs WHERE 1=1"
        params = []

        if workflow_name:
            query += " AND workflow_name = ?"
            params.append(workflow_name)

        if provider:
            query += " AND provider = ?"
            params.append(provider)

        if since:
            query += " AND started_at >= ?"
            params.append(since.isoformat())

        if success_only:
            query += " AND success = 1"

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        runs = []
        for row in cursor.fetchall():
            run = dict(row)

            # Fetch stages
            cursor.execute("""
                SELECT * FROM workflow_stages
                WHERE run_id = ?
                ORDER BY stage_id
            """, (run["run_id"],))

            run["stages"] = [dict(s) for s in cursor.fetchall()]
            runs.append(run)

        return runs

    def get_stats(self) -> dict:
        """Get aggregate statistics."""
        cursor = self.conn.cursor()

        # Total runs by workflow
        cursor.execute("""
            SELECT
                workflow_name,
                COUNT(*) as runs,
                SUM(total_cost) as cost,
                SUM(savings) as savings,
                SUM(success) as successful
            FROM workflow_runs
            GROUP BY workflow_name
        """)
        by_workflow = {row["workflow_name"]: dict(row) for row in cursor.fetchall()}

        # Total runs by provider
        cursor.execute("""
            SELECT
                provider,
                COUNT(*) as runs,
                SUM(total_cost) as cost
            FROM workflow_runs
            GROUP BY provider
        """)
        by_provider = {row["provider"]: dict(row) for row in cursor.fetchall()}

        # Total cost by tier
        cursor.execute("""
            SELECT
                tier,
                SUM(cost) as total_cost
            FROM workflow_stages
            WHERE skipped = 0
            GROUP BY tier
        """)
        by_tier = {row["tier"]: row["total_cost"] for row in cursor.fetchall()}

        # Recent runs
        cursor.execute("""
            SELECT * FROM workflow_runs
            ORDER BY started_at DESC
            LIMIT 10
        """)
        recent_runs = [dict(row) for row in cursor.fetchall()]

        # Totals
        cursor.execute("""
            SELECT
                COUNT(*) as total_runs,
                SUM(success) as successful_runs,
                SUM(total_cost) as total_cost,
                SUM(savings) as total_savings,
                AVG(CASE WHEN success = 1 THEN savings_percent ELSE NULL END) as avg_savings_percent
            FROM workflow_runs
        """)
        totals = dict(cursor.fetchone())

        return {
            "total_runs": totals["total_runs"] or 0,
            "successful_runs": totals["successful_runs"] or 0,
            "by_workflow": by_workflow,
            "by_provider": by_provider,
            "by_tier": by_tier,
            "recent_runs": recent_runs,
            "total_cost": totals["total_cost"] or 0.0,
            "total_savings": totals["total_savings"] or 0.0,
            "avg_savings_percent": totals["avg_savings_percent"] or 0.0,
        }

    def close(self):
        """Close database connection."""
        self.conn.close()
```

### Migration Script

```python
# New file: scripts/migrate_workflow_history.py
"""Migrate workflow history from JSON to SQLite."""
import json
from pathlib import Path
from datetime import datetime

from attune.workflows.history import WorkflowHistoryStore
from attune.workflows.base import WORKFLOW_HISTORY_FILE

def migrate():
    """Migrate JSON history to SQLite."""
    json_path = Path(WORKFLOW_HISTORY_FILE)

    if not json_path.exists():
        print("No JSON history found. Nothing to migrate.")
        return

    # Load JSON history
    with open(json_path) as f:
        history = json.load(f)

    print(f"Migrating {len(history)} workflow runs...")

    # Create SQLite store
    store = WorkflowHistoryStore()

    # Migrate each run
    for i, run in enumerate(history, 1):
        # Generate run_id from timestamp
        run_id = f"migrated_{run['started_at'].replace(':', '-')}"

        # Create minimal WorkflowResult-like structure
        from dataclasses import dataclass
        from attune.workflows.base import WorkflowResult, WorkflowStage, CostReport, ModelTier

        stages = [
            WorkflowStage(
                name=s["name"],
                tier=ModelTier(s["tier"]),
                skipped=s.get("skipped", False),
                cost=s.get("cost", 0.0),
                duration_ms=s.get("duration_ms", 0),
                input_tokens=0,
                output_tokens=0,
                skip_reason=None,
            )
            for s in run.get("stages", [])
        ]

        result = WorkflowResult(
            success=run.get("success", True),
            stages=stages,
            final_output={"summary": run.get("summary")} if run.get("xml_parsed") else {},
            cost_report=CostReport(
                total_cost=run.get("cost", 0.0),
                baseline_cost=run.get("baseline_cost", 0.0),
                savings=run.get("savings", 0.0),
                savings_percent=run.get("savings_percent", 0.0),
                by_tier={},
                cache_savings=0.0,
            ),
            started_at=datetime.fromisoformat(run["started_at"]),
            completed_at=datetime.fromisoformat(run["completed_at"]),
            total_duration_ms=run.get("duration_ms", 0),
            provider=run.get("provider", "unknown"),
            error=run.get("error"),
        )

        store.record_run(
            run_id=run_id,
            workflow_name=run["workflow"],
            provider=run.get("provider", "unknown"),
            result=result,
        )

        if i % 10 == 0:
            print(f"  Migrated {i}/{len(history)} runs...")

    store.close()

    # Backup JSON file
    backup_path = json_path.with_suffix(".json.backup")
    json_path.rename(backup_path)

    print(f"✅ Migration complete!")
    print(f"   - Migrated {len(history)} runs to {store.db_path}")
    print(f"   - JSON backup: {backup_path}")

if __name__ == "__main__":
    migrate()
```

### Integration with BaseWorkflow

```python
# In base.py - Update to use WorkflowHistoryStore

from .history import WorkflowHistoryStore

# Global singleton (lazy-initialized)
_history_store: WorkflowHistoryStore | None = None

def _get_history_store() -> WorkflowHistoryStore:
    """Get or create history store singleton."""
    global _history_store
    if _history_store is None:
        _history_store = WorkflowHistoryStore()
    return _history_store


def _save_workflow_run(
    workflow_name: str,
    provider: str,
    result: WorkflowResult,
    run_id: str | None = None,
) -> None:
    """Save a workflow run to history (SQLite)."""
    import uuid

    if run_id is None:
        run_id = str(uuid.uuid4())

    store = _get_history_store()
    store.record_run(run_id, workflow_name, provider, result)


def get_workflow_stats() -> dict:
    """Get workflow statistics (from SQLite)."""
    store = _get_history_store()
    return store.get_stats()
```

### Benefits

1. **Concurrent-safe**: SQLite handles locking
2. **Fast queries**: Indexed for common patterns
3. **Unlimited history**: No 100-run limit
4. **Flexible filtering**: Query by workflow, provider, date
5. **Analytics ready**: SQL enables complex queries

### Migration Path

1. Create `history.py` with `WorkflowHistoryStore`
2. Create migration script
3. Run migration: `python scripts/migrate_workflow_history.py`
4. Update `base.py` to use SQLite
5. Deprecate JSON functions (keep for 1 release cycle)
6. Remove JSON functions in v5.0

### Backwards Compatibility

⚠️ **Breaking change for direct JSON access**

Mitigation: Provide `get_workflow_stats()` wrapper that maintains API.

---

## Track 3: Simplify Constructor (Priority: MEDIUM)

### Problem

BaseWorkflow has 12+ constructor parameters:

```python
def __init__(
    self,
    config: WorkflowConfig | None = None,
    executor: LLMExecutor | None = None,
    provider: UnifiedModelProvider | None = None,
    cache: BaseCache | None = None,
    enable_cache: bool = True,
    enable_telemetry: bool = True,
    telemetry_backend: TelemetryBackend | None = None,
    progress_callback: ProgressCallback | None = None,
    tier_tracker: WorkflowTierTracker | None = None,
    routing_strategy: TierRoutingStrategy | None = None,  # NEW
    # ... more params
):
```

### Solution: Builder Pattern

```python
# New: WorkflowBuilder
class WorkflowBuilder:
    """Builder for complex workflow configuration."""

    def __init__(self, workflow_class: type[BaseWorkflow]):
        self.workflow_class = workflow_class
        self._config: WorkflowConfig | None = None
        self._routing: TierRoutingStrategy | None = None
        self._cache: BaseCache | None = None
        # ... other fields

    def with_config(self, config: WorkflowConfig) -> WorkflowBuilder:
        self._config = config
        return self

    def with_routing(self, strategy: TierRoutingStrategy) -> WorkflowBuilder:
        self._routing = strategy
        return self

    def with_cache(self, cache: BaseCache) -> WorkflowBuilder:
        self._cache = cache
        return self

    def build(self) -> BaseWorkflow:
        """Build configured workflow."""
        return self.workflow_class(
            config=self._config,
            routing_strategy=self._routing,
            cache=self._cache,
            # ... other params
        )

# Usage:
workflow = (
    WorkflowBuilder(TestGenerationWorkflow)
    .with_config(config)
    .with_routing(BalancedRouting(budget=10.0))
    .build()
)
```

**Alternative**: Keep constructor as-is, builder is optional convenience.

---

## Track 4: Remove Dual ModelTier Enums (Priority: LOW)

### Problem

`ModelTier` defined in two places:
- `src/attune/models/registry.py:20` (canonical)
- `src/attune/workflows/base.py:83` (backward compatibility)

### Solution: Deprecate and Remove

```python
# Phase 1 (v4.8): Add deprecation warning
class ModelTier(Enum):
    """DEPRECATED: Use attune.models.ModelTier instead.

    This enum will be removed in v5.0.

    Migration:
        # Old:
        from attune.workflows.base import ModelTier

        # New:
        from attune.models import ModelTier
    """

    def __init__(self, value):
        import warnings
        warnings.warn(
            "workflows.base.ModelTier is deprecated. "
            "Use attune.models.ModelTier instead. "
            "This will be removed in v5.0.",
            DeprecationWarning,
            stacklevel=3,
        )
        super().__init__()

# Phase 2 (v5.0): Remove local enum entirely
# Just import from models:
from attune.models import ModelTier
```

---

## Implementation Timeline

### Phase 1: Week 1 (High Priority Tracks)

**Days 1-2: Track 2 (SQLite History)**
- [ ] Create `WorkflowHistoryStore` class
- [ ] Create migration script
- [ ] Test migration with existing history
- [ ] Update `base.py` to use SQLite

**Days 3-5: Track 1 (Tier Routing)**
- [ ] Create `routing.py` with strategies
- [ ] Unit tests for each strategy
- [ ] Integrate with `BaseWorkflow`
- [ ] Integration tests

### Phase 2: Week 2 (Polish)

**Days 1-2: Testing & Documentation**
- [ ] End-to-end tests for refactored components
- [ ] Performance benchmarks (before/after)
- [ ] Update documentation
- [ ] Migration guides

**Days 3-4: Track 3 (Constructor - Optional)**
- [ ] Create `WorkflowBuilder` class
- [ ] Examples in docs
- [ ] Tests

**Day 5: Track 4 (Deprecate Enum)**
- [ ] Add deprecation warnings
- [ ] Update internal uses
- [ ] Schedule v5.0 removal

### Phase 3: Week 3 (Validation)

- Run on real workloads
- Gather feedback
- Fix issues
- Prepare v4.8 release

---

## Success Metrics

| Metric | Before | Target | Measured How |
|--------|--------|--------|--------------|
| **Tier routing test coverage** | 0% | 95% | pytest --cov |
| **History query speed** | O(n) | O(log n) | Benchmark script |
| **Concurrent workflow safety** | ❌ | ✅ | Parallel execution test |
| **Constructor complexity** | 12 params | 5 core + builder | Line count |
| **Enum duplication** | 2 | 1 | grep analysis |

---

## Risks & Mitigation

### Risk 1: SQLite Migration Data Loss

**Likelihood**: LOW
**Impact**: HIGH

**Mitigation**:
- Backup JSON before migration
- Validation step compares record counts
- Rollback script to restore JSON

### Risk 2: Strategy Pattern Over-Engineering

**Likelihood**: MEDIUM
**Impact**: LOW

**Mitigation**:
- Start with 3 concrete strategies
- Don't expose strategy interface publicly until v5.0
- Default behavior unchanged

### Risk 3: Breaking Changes for External Users

**Likelihood**: MEDIUM
**Impact**: MEDIUM

**Mitigation**:
- Maintain backward compatibility for 1 release
- Deprecation warnings with migration examples
- Comprehensive migration guide

---

## Alternatives Considered

### Alternative 1: Leave BaseWorkflow As-Is

**Rejected** - Technical debt is growing, blocking scaling and testing.

### Alternative 2: Complete Rewrite

**Rejected** - Too risky, too much churn. Phased approach is safer.

### Alternative 3: PostgreSQL Instead of SQLite

**Rejected** - Over-engineering for local development. SQLite → Postgres is easy migration later.

### Alternative 4: NoSQL (MongoDB, Redis) for History

**Rejected** - SQL is better for analytics queries. No need for document flexibility.

---

## Related Documents

- [ADR-001: Workflow Engine Architecture Review](001-workflow-engine-architecture.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [BaseWorkflow Implementation](../../src/attune/workflows/base.py)
- [Model Registry](../../src/attune/models/registry.py)

---

## Review & Approval

This ADR will be reviewed after Track 1 and Track 2 implementation.

**Expected Outcomes:**
1. Tier routing is testable and customizable
2. Workflow history is concurrent-safe and queryable
3. No regressions in existing workflows
4. Path cleared for CI/CD scaling

---

**Author:** Claude Sonnet 4.5 (Attune AI Redesign)
**Created:** January 26, 2026
**Status:** Proposed (awaiting implementation)
**Next Review:** After Phase 1 completion
