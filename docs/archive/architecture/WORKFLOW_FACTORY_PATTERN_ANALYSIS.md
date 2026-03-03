---
description: Workflow Factory Pattern Analysis: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Workflow Factory Pattern Analysis

**Date:** 2025-01-05
**Analyzed:** 17 workflows in `src/attune/workflows/`

---

## Identified Patterns

### Pattern 1: Multi-Stage Workflow (most common)

**Examples:** bug_predict, code_review, pr_review, security_audit

**Characteristics:**
- Multiple sequential stages with tier mapping
- Each stage uses specific ModelTier (CHEAP/CAPABLE/PREMIUM)
- Conditional stage skipping based on results
- Custom `run_stage()` implementation for each stage

**Template Structure:**
```python
class MyWorkflow(BaseWorkflow):
    name = "my-workflow"
    description = "..."
    stages = ["stage1", "stage2", "stage3"]
    tier_map = {
        "stage1": ModelTier.CHEAP,
        "stage2": ModelTier.CAPABLE,
        "stage3": ModelTier.PREMIUM,
    }

    def should_skip_stage(self, stage_name, input_data):
        # Conditional logic
        pass

    async def run_stage(self, stage_name, tier, input_data):
        if stage_name == "stage1":
            return await self._stage1(input_data, tier)
        # ...
```

**Usage:** 70% of workflows (12/17)

---

### Pattern 2: Crew-Wrapper Workflow

**Examples:** health_check, security_audit (crew mode), code_review (crew mode)

**Characteristics:**
- Wraps CrewAI crew for multi-agent collaboration
- Simple stage routing (diagnose/fix or analyze/report)
- Crew initialization and availability checking
- Result aggregation from crew output

**Template Structure:**
```python
class MyCrewWorkflow(BaseWorkflow):
    name = "my-crew-workflow"
    description = "..."
    stages = ["diagnose", "fix"]
    tier_map = {
        "diagnose": ModelTier.CAPABLE,
        "fix": ModelTier.CAPABLE,
    }

    def __init__(self, auto_fix=False, **kwargs):
        super().__init__(**kwargs)
        self._crew = None

    async def _initialize_crew(self):
        from attune_llm.agent_factory.crews import MyCrew
        self._crew = MyCrew(...)
```

**Usage:** 30% of workflows (5/17)

---

### Pattern 3: Configuration-Driven Workflow

**Examples:** bug_predict, health_check, security_audit

**Characteristics:**
- Loads config from empathy.config.yml
- Configurable thresholds and options
- Default fallbacks if no config

**Template Structure:**
```python
def _load_config():
    defaults = {"threshold": 0.7}
    for config_path in ["empathy.config.yml", ".empathy.yml"]:
        if Path(config_path).exists():
            config = yaml.safe_load(open(config_path))
            return config.get("my_workflow", defaults)
    return defaults

class MyWorkflow(BaseWorkflow):
    def __init__(self, threshold=None, **kwargs):
        super().__init__(**kwargs)
        config = _load_config()
        self.threshold = threshold or config["threshold"]
```

**Usage:** 50% of workflows (8/17)

---

### Pattern 4: Result Dataclass

**Examples:** health_check, release_prep

**Characteristics:**
- Structured output with dataclass
- Standard fields (success, metadata, cost, duration)
- Domain-specific fields

**Template Structure:**
```python
@dataclass
class MyWorkflowResult:
    success: bool
    score: float
    issues: list[dict]
    fixes: list[dict]
    duration_seconds: float
    cost: float
    metadata: dict = field(default_factory=dict)
```

**Usage:** 40% of workflows (7/17)

---

### Pattern 5: Conditional Tier Routing

**Examples:** bug_predict, code_review, pr_review

**Characteristics:**
- Dynamically adjust tiers based on complexity
- Skip expensive stages for simple cases
- Downgrade from PREMIUM to CAPABLE when appropriate

**Template Structure:**
```python
def should_skip_stage(self, stage_name, input_data):
    if stage_name == "premium_review":
        if self._complexity_score < self.complexity_threshold:
            # Downgrade instead of skip
            self.tier_map["premium_review"] = ModelTier.CAPABLE
            return False, None
    return False, None
```

**Usage:** 60% of workflows (10/17)

---

### Pattern 6: Custom Validators/Scanners

**Examples:** bug_predict, security_audit, test_gen

**Characteristics:**
- Helper functions for code analysis
- Pattern matching and detection
- File exclusion logic

**Template Structure:**
```python
def _should_exclude_file(file_path, patterns):
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

def _scan_for_pattern(content, pattern_type):
    # Custom detection logic
    pass
```

**Usage:** 35% of workflows (6/17)

---

### Pattern 7: Progress Tracking Integration

**Examples:** Most workflows via BaseWorkflow

**Characteristics:**
- Uses ProgressCallback for real-time updates
- Emits stage progress events
- Integrates with telemetry

**Template Structure:**
```python
# Inherited from BaseWorkflow
# Progress automatically tracked during execute()
```

**Usage:** 100% of workflows (inherited)

---

## Pattern Combinations

Common combinations:
- **Multi-Stage + Configuration** (60%)
- **Multi-Stage + Conditional Tier** (55%)
- **Crew-Wrapper + Result Dataclass** (25%)
- **Multi-Stage + Custom Validators** (30%)

---

## File Organization Patterns

All workflows follow:
```
src/attune/workflows/
  my_workflow.py         # Main workflow class
  base.py                # BaseWorkflow parent
  config.py              # WorkflowConfig
  step_config.py         # WorkflowStepConfig
  progress.py            # Progress tracking
```

Tests follow:
```
tests/unit/workflows/
  test_my_workflow.py
  fixtures_my_workflow.py
```

---

## Extracted Pattern Library

Based on this analysis, the Workflow Factory should support:

1. **single-stage** - Simple one-tier workflow
2. **multi-stage** - Multiple sequential stages
3. **crew-based** - Wraps CrewAI crew
4. **config-driven** - Loads from empathy.config.yml
5. **result-dataclass** - Structured output format
6. **conditional-tier** - Dynamic tier routing
7. **code-scanner** - File scanning and analysis
8. **progress-tracking** - Real-time progress (built-in)
9. **telemetry** - Cost and usage tracking (built-in)

---

## Next Steps

1. Create Pydantic models for each pattern
2. Build Jinja2 templates for code generation
3. Create scaffolding CLI
4. Integrate with test generator
5. Add to empathy CLI

---

**Last Updated:** 2025-01-05
**Workflows Analyzed:** 17/17
**Patterns Identified:** 9 core patterns
