---
description: Adaptive Routing Integration Guide integration guide. Connect external tools and services with Attune AI for enhanced AI capabilities.
---

# Adaptive Routing Integration Guide

**Created:** January 27, 2026
**Pattern:** Pattern 3 from AGENT_COORDINATION_ARCHITECTURE.md
**Status:** ✅ Core Implementation Complete (Day 1)
**Provider:** 🎯 Anthropic-native (automatically uses latest Claude models from registry)

---

## What Was Implemented

### 1. AdaptiveModelRouter Class

**Location:** [src/attune/models/adaptive_routing.py](../src/attune/models/adaptive_routing.py)

**Key Features:**
- ✅ Analyzes historical telemetry per model/workflow/stage
- ✅ Recommends best model based on success rate + cost efficiency
- ✅ Auto-detects when tier upgrades are needed (>20% failure rate)
- ✅ Respects cost and latency constraints
- ✅ Provides routing statistics and analytics
- ✅ **Dynamically fetches Anthropic models from registry** - when new Claude models are released, they're automatically used

**Main Methods:**
```python
# Get best model for a workflow stage
model = router.get_best_model(
    workflow="code-review",
    stage="analysis",
    max_cost=0.01,
    min_success_rate=0.9
)

# Check if tier should be upgraded
should_upgrade, reason = router.recommend_tier_upgrade(
    workflow="code-review",
    stage="analysis"
)

# Get routing statistics
stats = router.get_routing_stats(
    workflow="code-review",
    days=7
)
```

---

## How to Use It

### Quick Start (CLI Demo)

```bash
# Run the demo script (requires existing telemetry data)
python examples/adaptive_routing_demo.py
```

**Expected Output:**
```
====================================================================
ADAPTIVE MODEL ROUTING DEMONSTRATION
====================================================================

📊 Example 1: Get Best Model for Code Review
--------------------------------------------------------------------
✓ Selected model: claude-haiku-3.5
  Constraints: max_cost=$0.01, min_success_rate=90%

⚠️  Example 2: Check for Tier Upgrade Recommendations
--------------------------------------------------------------------
✓ No upgrade needed: Performance acceptable: 5.0% failure rate

📈 Example 3: Routing Statistics (Last 7 Days)
--------------------------------------------------------------------
Workflow: code-review
Total calls: 42
Average cost: $0.0023
Average success rate: 95.2%

Models used: claude-haiku-3.5, claude-sonnet-4.5

Per-Model Performance:
  claude-haiku-3.5:
    Calls: 38
    Success rate: 94.7%
    Avg cost: $0.0018
    Avg latency: 1247ms

  claude-sonnet-4.5:
    Calls: 4
    Success rate: 100.0%
    Avg cost: $0.0089
    Avg latency: 2341ms
```

### Integration with Workflows

#### Option A: Manual Integration (Immediate)

Add to any workflow's `execute()` method:

```python
from attune.models import AdaptiveModelRouter
from attune.telemetry import UsageTracker

class MyWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__()
        self.router = AdaptiveModelRouter(UsageTracker.get_instance())

    async def execute(self, input_data: dict):
        # Before executing a stage, check telemetry
        for stage in self.stages:
            # Check if we should upgrade tier
            should_upgrade, reason = self.router.recommend_tier_upgrade(
                workflow=self.name,
                stage=stage.name
            )

            if should_upgrade:
                logger.warning(f"⚠️ Upgrading {stage.name}: {reason}")
                stage.tier = ModelTier.CAPABLE  # Upgrade from CHEAP

            # Get best model for this stage
            recommended_model = self.router.get_best_model(
                workflow=self.name,
                stage=stage.name,
                max_cost=stage.max_cost,
                min_success_rate=0.85
            )

            logger.info(f"Using {recommended_model} for {stage.name}")

            # Execute stage...
            result = await self._execute_stage(stage, model=recommended_model)
```

#### Option B: Automated Integration (Day 2 Task)

Modify `BaseWorkflow` to automatically use adaptive routing:

```python
# In src/attune/workflows/base.py

class BaseWorkflow:
    def __init__(self, enable_adaptive_routing: bool = True):
        # ...
        if enable_adaptive_routing:
            self.router = AdaptiveModelRouter(UsageTracker.get_instance())
        else:
            self.router = None

    async def _execute_stage(self, stage: WorkflowStage):
        """Execute stage with optional adaptive routing."""

        # Use adaptive routing if enabled
        if self.router:
            # Check for tier upgrade recommendation
            should_upgrade, reason = self.router.recommend_tier_upgrade(
                workflow=self.name,
                stage=stage.name
            )

            if should_upgrade:
                old_tier = stage.tier
                stage.tier = self._upgrade_tier(stage.tier)
                logger.warning(
                    "adaptive_routing_upgrade",
                    stage=stage.name,
                    old_tier=old_tier.value,
                    new_tier=stage.tier.value,
                    reason=reason
                )

            # Get recommended model
            recommended_model = self.router.get_best_model(
                workflow=self.name,
                stage=stage.name,
                max_cost=stage.max_cost,
                min_success_rate=0.85
            )

            logger.info(
                "adaptive_routing_selected",
                stage=stage.name,
                model=recommended_model
            )

            # Override model selection
            # ... use recommended_model in API call

        # Execute stage normally
        result = await self._call_model(stage)
        return result

    def _upgrade_tier(self, current_tier: ModelTier) -> ModelTier:
        """Upgrade to next tier."""
        if current_tier == ModelTier.CHEAP:
            return ModelTier.CAPABLE
        elif current_tier == ModelTier.CAPABLE:
            return ModelTier.PREMIUM
        else:
            return current_tier  # Already at highest tier
```

---

## Testing the Implementation

### Create Test Telemetry Data

If you don't have telemetry yet, generate some:

```python
# tests/test_adaptive_routing.py

from attune.models import AdaptiveModelRouter
from attune.telemetry import UsageTracker
from datetime import datetime

def test_adaptive_routing_with_mock_data():
    """Test adaptive routing with mock telemetry data."""

    # Create mock telemetry entries
    tracker = UsageTracker.get_instance()

    # Simulate 50 calls to code-review workflow
    for i in range(50):
        tracker.track_llm_call(
            workflow="code-review",
            stage="analysis",
            tier="CHEAP",
            model="claude-haiku-3.5",
            provider="anthropic",
            cost=0.0018,
            tokens={"input": 1000, "output": 500},
            cache_hit=False,
            cache_type=None,
            duration_ms=1200,
            # Simulate 10% failure rate
            success=(i % 10 != 0)
        )

    # Test router
    router = AdaptiveModelRouter(tracker)

    # Should recommend cheap model (90% success rate is good)
    model = router.get_best_model(
        workflow="code-review",
        stage="analysis",
        max_cost=0.01,
        min_success_rate=0.85
    )

    assert model == "claude-haiku-3.5"

    # Should NOT recommend upgrade (10% failure rate < 20% threshold)
    should_upgrade, reason = router.recommend_tier_upgrade(
        workflow="code-review",
        stage="analysis"
    )

    assert not should_upgrade
    assert "acceptable" in reason.lower()
```

Run the test:
```bash
pytest tests/test_adaptive_routing.py -v
```

---

## Next Steps (Day 2)

### Task 1: Integrate with BaseWorkflow

**Goal:** Make adaptive routing automatic for all workflows

**Files to modify:**
- `src/attune/workflows/base.py` - Add router initialization
- `src/attune/workflows/base.py` - Modify `_execute_stage()` method

**Estimated time:** 2-3 hours

### Task 2: Add CLI Commands

**Goal:** Expose routing stats via CLI

**Commands to add:**
```bash
# Show routing statistics
attune telemetry routing-stats --workflow code-review --days 7

# Show tier upgrade recommendations
attune telemetry routing-check --workflow code-review

# Show all workflows with upgrade recommendations
attune telemetry routing-check --all
```

**Files to create:**
- `src/attune/telemetry/routing_cli.py` - CLI commands

**Estimated time:** 2-3 hours

### Task 3: Add Tests

**Goal:** Comprehensive test coverage

**Tests to add:**
- Unit tests for AdaptiveModelRouter methods
- Integration tests with real telemetry data
- Edge case tests (no data, all models fail, etc.)

**Files to create:**
- `tests/unit/models/test_adaptive_routing.py` - Unit tests
- `tests/integration/test_adaptive_routing_integration.py` - Integration tests

**Estimated time:** 2-3 hours

---

## Configuration Options

### Disable Adaptive Routing

If you want to disable adaptive routing for specific workflows:

```python
class MyWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__(enable_adaptive_routing=False)
        # ... workflow will use static task-type routing
```

### Adjust Failure Threshold

Default threshold is 20%. To customize:

```python
router = AdaptiveModelRouter(telemetry)
router.FAILURE_RATE_THRESHOLD = 0.15  # 15% threshold
```

### Adjust Minimum Sample Size

Default is 10 calls. To customize:

```python
router = AdaptiveModelRouter(telemetry)
router.MIN_SAMPLE_SIZE = 20  # Require 20 calls before making decisions
```

---

## Benefits

1. **Cost Optimization** - Uses cheapest model that meets requirements
2. **Self-Improving** - Learns from experience, no manual tuning
3. **Failure Reduction** - Automatically upgrades tier when failure rate is high
4. **Constraint Awareness** - Respects cost and latency limits
5. **Zero Configuration** - Works out of the box with existing telemetry

---

## FAQ

**Q: What happens if there's no telemetry data?**
A: Router falls back to default cheap model (`claude-haiku-3.5`)

**Q: How often does it check for tier upgrades?**
A: Every time a workflow stage executes (if adaptive routing is enabled)

**Q: Can I force a specific model even with adaptive routing?**
A: Yes, set `enable_adaptive_routing=False` or override model selection

**Q: Does this replace task-type routing?**
A: No, it complements it. Adaptive routing learns which tier works best for each task over time.

**Q: How much telemetry data is needed?**
A: Minimum 10 calls per workflow/stage to make routing decisions

---

## Related Documentation

- [AGENT_COORDINATION_ARCHITECTURE.md](./AGENT_COORDINATION_ARCHITECTURE.md) - Full pattern descriptions
- [Telemetry Documentation](./telemetry.md) - How telemetry tracking works
- [Model Registry Documentation](./models.md) - Available models and tiers

---

**Status:** ✅ Day 1 Complete
**Next:** Day 2 - Workflow Integration + CLI Commands
