# Progressive Tier Escalation System

**Version:** 4.1.0
**Status:** Framework available; `ProgressiveTestGenWorkflow` removed in v6.3.0
**Test Coverage:** 86.58% (123 tests)

> **Note (v6.3.0):** The concrete `ProgressiveTestGenWorkflow`
> class referenced in the examples below was deprecated in v5.3.0
> and removed in v6.3.0. The underlying framework
> (`ProgressiveWorkflow` base class, `EscalationConfig`, `Tier`,
> CQS scoring, telemetry, reports) is unchanged and available for
> new subclasses. For test generation, use
> `ParallelTestGenerationWorkflow` via
> `attune workflow run test-gen-parallel` — it is the canonical,
> production path and is not a progressive workflow. The examples
> below illustrate the framework API; substitute your own
> `ProgressiveWorkflow` subclass.

## Overview

The Progressive Tier Escalation System is an intelligent cost optimization framework that automatically routes tasks through multiple AI model tiers (cheap → capable → premium) based on quality metrics, providing 70-85% cost savings compared to using premium models for all tasks.

## Key Features

- ✅ **Multi-tier execution**: Automatic progression from cheap to premium models
- ✅ **Composite Quality Score (CQS)**: Multi-signal failure detection
- ✅ **Smart escalation**: Only failed items escalate, successful ones stay at current tier
- ✅ **Cost management**: Budget controls with approval prompts
- ✅ **Privacy-preserving telemetry**: Local tracking with hashed user IDs
- ✅ **Comprehensive analytics**: Historical cost savings analysis
- ✅ **CLI tools**: Manage and analyze workflow results

## Quick Start

```python
from attune.workflows.progressive import (
    ProgressiveTestGenWorkflow,
    EscalationConfig,
    Tier
)

# Configure escalation
config = EscalationConfig(
    enabled=True,
    tiers=[Tier.CHEAP, Tier.CAPABLE, Tier.PREMIUM],
    max_cost=10.00,
    auto_approve_under=1.00,
    abort_on_budget_exceeded=True
)

# Create workflow
workflow = ProgressiveTestGenWorkflow(config)

# Execute with automatic tier progression
result = workflow.execute(target_file="src/myapp/calculator.py")

# View results
print(result.generate_report())
print(f"Cost: ${result.total_cost:.2f}")
print(f"Savings: ${result.cost_savings:.2f} ({result.cost_savings_percent:.0f}%)")

# Save results for analytics
result.save_to_disk()
```

## Architecture

### Tier Progression

```
┌─────────────────────────────────────────────────────────────┐
│                     PROGRESSIVE ESCALATION                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   CHEAP TIER    │
                    │  (gpt-4o-mini)  │
                    │   $0.003/item   │
                    │   1 agent       │
                    └────────┬────────┘
                             │
                    CQS < 75? ───No──> SUCCESS
                             │
                            Yes
                             │
                             ▼
                    ┌─────────────────┐
                    │  CAPABLE TIER   │
                    │ (claude-3-5-s)  │
                    │   $0.015/item   │
                    │   2 agents      │
                    └────────┬────────┘
                             │
                    CQS < 85? ───No──> SUCCESS
                             │
                            Yes
                             │
                             ▼
                    ┌─────────────────┐
                    │  PREMIUM TIER   │
                    │ (claude-opus-4) │
                    │   $0.05/item    │
                    │   3 agents      │
                    └────────┬────────┘
                             │
                             ▼
                         FINAL RESULT
```

### Composite Quality Score (CQS)

Quality is measured using a weighted multi-signal metric:

```
CQS = (0.40 × test_pass_rate +
       0.25 × code_coverage +
       0.20 × assertion_quality +
       0.15 × llm_confidence) × syntax_penalty
```

**Thresholds:**
- **CHEAP tier**: CQS ≥ 75 (pass), < 75 (escalate)
- **CAPABLE tier**: CQS ≥ 85 (pass), < 85 (escalate)
- **PREMIUM tier**: CQS ≥ 90 (target), no escalation

**Syntax Penalty:** 50% reduction if syntax errors detected

## Core Components

### 1. EscalationConfig

Configuration for tier escalation behavior:

```python
config = EscalationConfig(
    enabled=True,                    # Enable progressive escalation
    tiers=[Tier.CHEAP, Tier.CAPABLE, Tier.PREMIUM],
    cheap_min_attempts=2,            # Try cheap tier 2× before escalating
    capable_min_attempts=1,          # Try capable tier 1× before escalating
    max_cost=10.00,                  # Abort if cost exceeds $10
    auto_approve_under=1.00,         # Auto-approve costs < $1
    abort_on_budget_exceeded=True,   # Abort vs warn on budget exceeded
    warn_on_budget_exceeded=False,
    stagnation_threshold=0.05,       # 5% improvement threshold
    stagnation_window=2,             # Over 2 consecutive runs
)
```

### 2. Meta-Orchestration

Dynamic agent team creation based on tier:

| Tier     | Agents | Strategy                              |
|----------|--------|---------------------------------------|
| CHEAP    | 1      | Single agent, fast iteration          |
| CAPABLE  | 2      | Planner + executor, collaborative     |
| PREMIUM  | 3      | Architect + executor + reviewer, deep |

### 3. Telemetry

Privacy-preserving usage tracking:

```python
from attune.workflows.progressive import ProgressiveTelemetry

# Initialize telemetry
telemetry = ProgressiveTelemetry(
    workflow_name="test-gen",
    user_id="user@example.com"  # SHA256 hashed for privacy
)

# Track tier execution
telemetry.track_tier_execution(tier_result, attempt=1, escalated=False)

# Track escalation
telemetry.track_escalation(
    from_tier=Tier.CHEAP,
    to_tier=Tier.CAPABLE,
    reason="Low CQS (65)",
    item_count=10,
    current_cost=0.30
)

# Track workflow completion
telemetry.track_workflow_completion(result)
```

**Data Stored:**
- Workflow name, tier, model, cost, tokens
- Quality metrics (CQS, test pass rate, coverage)
- Escalation reasons and patterns
- Timestamps and durations

**Privacy:**
- User IDs are SHA256 hashed
- No prompts, responses, or PII stored
- Local-only storage (~/.attune/telemetry/)

### 4. CLI Tools

Manage and analyze saved results:

```bash
# List all workflow results
empathy progressive list

# Show detailed report for specific run
empathy progressive show test-gen-20260117-120000

# Show JSON output
empathy progressive show test-gen-20260117-120000 --json

# Generate cost analytics
empathy progressive analytics

# Cleanup old results (30 day retention)
empathy progressive cleanup --retention-days 30

# Dry run cleanup (preview)
empathy progressive cleanup --retention-days 30 --dry-run

# Custom storage path
empathy progressive list --storage-path ./my-results
```

## Usage Examples

### Example 1: Test Generation with Escalation

```python
from attune.workflows.progressive import ProgressiveTestGenWorkflow

workflow = ProgressiveTestGenWorkflow()
result = workflow.execute(target_file="src/auth.py")

# View tier progression
for tier_result in result.tier_results:
    print(f"{tier_result.tier.value}: CQS={tier_result.failure_analysis.calculate_quality_score():.1f}")
    if tier_result.escalated:
        print(f"  → Escalated: {tier_result.escalation_reason}")

# Output:
# cheap: CQS=68.5
#   → Escalated: Low CQS (68.5)
# capable: CQS=92.0
```

### Example 2: Cost Analysis

```python
from attune.workflows.progressive.reports import generate_cost_analytics

analytics = generate_cost_analytics()

print(f"Total runs: {analytics['total_runs']}")
print(f"Total cost: ${analytics['total_cost']:.2f}")
print(f"Total savings: ${analytics['total_savings']:.2f}")
print(f"Avg savings: {analytics['avg_savings_percent']:.1f}%")
print(f"Escalation rate: {analytics['escalation_rate']:.1%}")
print(f"Success rate: {analytics['success_rate']:.1%}")

# Per-workflow breakdown
for workflow, stats in analytics['workflow_stats'].items():
    print(f"\n{workflow}:")
    print(f"  Runs: {stats['runs']}")
    print(f"  Avg cost: ${stats['avg_cost']:.2f}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
```

### Example 3: Custom Escalation Logic

```python
from attune.workflows.progressive import ProgressiveWorkflow, Tier

class CustomWorkflow(ProgressiveWorkflow):
    def _should_escalate_custom(self, tier_result):
        """Custom escalation logic."""
        # Example: Escalate if any syntax errors
        if tier_result.failure_analysis.syntax_errors:
            return True, "Syntax errors detected"

        # Example: Escalate if test pass rate < 90%
        if tier_result.failure_analysis.test_pass_rate < 0.90:
            return True, f"Low test pass rate ({tier_result.failure_analysis.test_pass_rate:.1%})"

        return False, None

    def _execute_tier_impl(self, tier, items, context):
        """Implement tier execution logic."""
        # Your custom implementation
        pass

workflow = CustomWorkflow()
result = workflow.execute(items=my_items)
```

## Performance Characteristics

### Cost Savings

Based on production usage:

| Scenario              | Cheap % | Capable % | Premium % | Savings |
|-----------------------|---------|-----------|-----------|---------|
| Simple tasks          | 80%     | 15%       | 5%        | 85%     |
| Medium complexity     | 60%     | 30%       | 10%       | 72%     |
| High complexity       | 40%     | 40%       | 20%       | 60%     |
| **Average**           | **60%** | **28%**   | **12%**   | **72%** |

### Execution Time

Progressive execution adds minimal latency:

- **Cheap tier**: ~5-10s per item (baseline)
- **Capable tier**: ~10-20s per item (+5-10s overhead)
- **Premium tier**: ~20-40s per item (+10-20s overhead)

**Parallel escalation**: Failed items escalate in parallel, reducing total time.

## Troubleshooting

### Issue: Excessive Escalation

**Symptoms:** Most items escalate to premium tier

**Causes:**
- CQS thresholds too strict
- Input items too complex for cheap/capable tiers
- Stagnation detection too sensitive

**Solutions:**
```python
# Lower CQS thresholds
config = EscalationConfig(
    cheap_cqs_threshold=70,  # Down from 75
    capable_cqs_threshold=80  # Down from 85
)

# Increase stagnation threshold
config = EscalationConfig(
    stagnation_threshold=0.10,  # 10% improvement required
    stagnation_window=3  # Over 3 runs
)

# Increase min attempts
config = EscalationConfig(
    cheap_min_attempts=3,  # Try 3× before escalating
    capable_min_attempts=2
)
```

### Issue: Budget Exceeded Errors

**Symptoms:** `BudgetExceededError` raised frequently

**Solutions:**
```python
# Increase budget
config = EscalationConfig(max_cost=20.00)

# Warn instead of abort
config = EscalationConfig(
    abort_on_budget_exceeded=False,
    warn_on_budget_exceeded=True
)

# Increase auto-approve threshold
config = EscalationConfig(auto_approve_under=5.00)
```

### Issue: Poor Quality Results

**Symptoms:** Final CQS < 85

**Causes:**
- Insufficient premium tier attempts
- Input quality issues
- Test assertion depth too low

**Solutions:**
```python
# Force premium tier for critical tasks
config = EscalationConfig(
    tiers=[Tier.PREMIUM],  # Skip cheap/capable
    enabled=False  # Disable escalation
)

# Increase premium min attempts
config = EscalationConfig(
    premium_min_attempts=2
)
```

## API Reference

### Core Classes

- `Tier`: Enum defining tier levels (CHEAP, CAPABLE, PREMIUM)
- `EscalationConfig`: Configuration for tier escalation
- `FailureAnalysis`: Quality metrics and failure signals
- `TierResult`: Results from a single tier execution
- `ProgressiveWorkflowResult`: Complete multi-tier execution results

### Base Classes

- `ProgressiveWorkflow`: Abstract base for progressive workflows
- `MetaOrchestrator`: Tier escalation decision logic

### Workflows

- `ProgressiveTestGenWorkflow`: Test generation with progressive escalation

### Utilities

- `ProgressiveTelemetry`: Usage tracking and analytics
- `generate_cost_analytics()`: Analyze historical cost savings
- `cleanup_old_results()`: Retention policy enforcement

## Testing

Run progressive workflow tests:

```bash
# All progressive tests
pytest tests/unit/workflows/progressive/ -v

# Specific test modules
pytest tests/unit/workflows/progressive/test_core.py -v
pytest tests/unit/workflows/progressive/test_orchestrator.py -v
pytest tests/unit/workflows/progressive/test_cost_telemetry.py -v
pytest tests/unit/workflows/progressive/test_reports_analytics.py -v
pytest tests/unit/workflows/progressive/test_test_gen.py -v

# With coverage
pytest tests/unit/workflows/progressive/ --cov=src/attune/workflows/progressive --cov-report=term-missing
```

**Test Coverage:** 86.58% (123 tests)

## Contributing

When adding new progressive workflows:

1. **Inherit from `ProgressiveWorkflow`**
2. **Implement `_execute_tier_impl()`** for tier-specific execution logic
3. **Define quality metrics** in `_analyze_quality()`
4. **Add comprehensive tests** (aim for 85%+ coverage)
5. **Document usage** with examples

See `ProgressiveTestGenWorkflow` for a complete implementation example.

## License

Apache License 2.0 0.9

## Version History

- **4.1.0** (2026-01-17): Initial release with test generation workflow
- **4.1.0-alpha**: Development version

## Support

- **Documentation**: [Attune AI Docs](https://attune-ai.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions)
