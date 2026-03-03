---
description: Development guidelines for Attune AI contributors. Level 3 anticipatory design principles, error handling patterns, and maintainability best practices.
---

# Attune AI Development Guidelines
**Purpose**: Guide contributors to maintain empathy principles in code
**Audience**: Contributors, maintainers, technical decision-makers
**Status**: Living document - update as patterns emerge

---

## Overview

The Attune AI is not just user-friendly - it operates at **Level 3 (Anticipatory)**, proactively handling production concerns so developers can focus on features. This document guides contributors to maintain these empathy principles.

---

## The Empathy Levels Framework

Every feature, API, and interaction in the Attune AI should be designed with empathy levels in mind:

### Level 1: Transactional
- Direct query → direct response
- No context awareness or anticipation
- **When appropriate**: Low-level utilities, atomic operations

### Level 2: Contextual
- Understands immediate context
- Provides relevant supporting information
- **When appropriate**: Error handling, reporting, environment detection

### Level 3: Anticipatory (Our Target)
- Predicts and addresses likely follow-up needs
- Prepares resources proactively
- **When appropriate**: Most user-facing APIs, production features

### Level 4: Adaptive
- Learns from patterns and personalizes behavior
- Adjusts based on individual usage
- **When appropriate**: Advanced features, optional personalization

### Level 5: Collaborative Meta-Awareness
- System and user jointly improve interaction
- Explicit reflection on process
- **When appropriate**: Configuration UI, feedback systems

---

## Design Principles

### 1. Anticipate Complete Workflows, Not Just Immediate Needs

**Bad** (Level 1):
```python
def create_cache():
    """Create a cache. User must install dependencies first."""
    return HybridCache()  # Crashes if dependencies missing
```

**Better** (Level 2):
```python
def create_cache():
    """Create a cache. Falls back if dependencies unavailable."""
    if HYBRID_AVAILABLE:
        return HybridCache()
    else:
        logger.warning("Install sentence-transformers for better caching")
        return HashOnlyCache()
```

**Best** (Level 3):
```python
def create_cache():
    """Create a cache. Auto-sets up dependencies if needed."""
    if HYBRID_AVAILABLE:
        return HybridCache()
    else:
        # Anticipate: User wants caching to work, may want to install deps
        if is_interactive_session():
            if prompt_user("Install cache dependencies for 70% savings? (y/n)"):
                install_dependencies()
                return HybridCache()
        logger.info("Using hash-only cache (install attune-ai[cache] for hybrid)")
        return HashOnlyCache()
```

**Why Level 3 is better**:
- Anticipates full workflow: want cache → need deps → offer install → configure
- Proactive but not presumptuous (asks before installing)
- Graceful fallback if user declines
- Clear guidance on improvement path

---

### 2. Provide Context, Not Just Data

**Bad** (Level 1):
```python
class WorkflowResult:
    cost: float  # Just the number
```

**Better** (Level 2):
```python
class WorkflowResult:
    cost: float
    by_tier: dict[str, float]  # Breakdown for analysis
```

**Best** (Level 3):
```python
class WorkflowResult:
    cost: float
    baseline_cost: float  # What it would cost without optimization
    savings: float
    savings_percent: float
    by_tier: dict[str, float]  # Where the cost went
    optimization_suggestions: list[OptimizationHint]  # Proactive guidance
```

**Why Level 3 is better**:
- Cost alone is trivia; comparison provides insight
- Breakdowns enable optimization decisions
- Suggestions anticipate user's next question: "How do I reduce this?"

---

### 3. Build Resilience In, Don't Make It Optional

**Bad** (Level 1):
```python
# User must add retry themselves
async def call_llm(prompt):
    return await provider.generate(prompt)  # Crashes on timeout
```

**Better** (Level 2):
```python
# Framework provides retry decorator
@retry(max_attempts=3)
async def call_llm(prompt):
    return await provider.generate(prompt)
```

**Best** (Level 3):
```python
# Resilience built into default executor
class WorkflowBase:
    def _get_executor(self):
        if self._executor is None:
            # Automatically wrap with resilience
            base = BaseExecutor()
            self._executor = ResilientExecutor(
                base,
                retry=True,  # 3 attempts with exponential backoff
                fallback=True,  # Alternative providers
                circuit_breaker=True  # Protect against cascading failures
            )
        return self._executor
```

**Why Level 3 is better**:
- Production needs resilience - make it the default
- User doesn't think about it, it just works
- Still customizable (can provide custom executor)

---

### 4. Make Complexity Transparent

**Bad** (Hidden complexity):
```python
# User has no idea what's happening
result = workflow.execute(data)
# Is it caching? Retrying? What tier?
```

**Good** (Visible but not intrusive):
```python
result = workflow.execute(data)

# Check what happened
print(f"Cost: ${result.cost_report.total_cost:.4f}")
print(f"Cache hits: {result.cost_report.cache_hit_rate:.1f}%")
print(f"Retries: {result.resilience_report.retry_count}")

# Telemetry captures everything automatically
# Dashboard shows: tier usage, cache effectiveness, failure rates
```

**Why this is better**:
- Automatic by default (Level 3 anticipation)
- Observable when needed (support debugging, optimization)
- Telemetry enables monitoring without instrumentation

---

## Code Review Checklist

When reviewing code, ask these questions:

### For New Features

**❓ What empathy level is this feature?**
- [ ] Level 1 (Transactional) - Is this appropriate for a low-level utility?
- [ ] Level 2 (Contextual) - Does it provide context and relevant information?
- [ ] Level 3 (Anticipatory) - Does it anticipate and prepare proactively?
- [ ] Level 4 (Adaptive) - Does it learn from patterns? (optional, advanced)

**❓ Does it anticipate the complete user workflow?**
- [ ] What's the user's goal (not just immediate request)?
- [ ] What are the likely next steps?
- [ ] What could go wrong?
- [ ] Are there reasonable fallbacks?

**❓ Does it provide context, not just data?**
- [ ] Are comparisons provided (baseline, target, historical)?
- [ ] Are breakdowns included (by component, by type)?
- [ ] Is guidance offered (what to do with this information)?

**❓ Is resilience built-in?**
- [ ] Does it handle transient failures (retry)?
- [ ] Are there fallback options?
- [ ] Does it fail gracefully if everything fails?
- [ ] Is it observable (telemetry for monitoring)?

**❓ Is complexity transparent?**
- [ ] Can users see what's happening if needed?
- [ ] Is the simple path obvious?
- [ ] Are advanced options available but not required?

---

### For Bug Fixes

**❓ What caused the bug?**
- [ ] Lack of context awareness? (Level 1 → 2 upgrade needed)
- [ ] Missing anticipation? (Level 2 → 3 upgrade needed)
- [ ] Edge case not handled? (add to fallback chain)
- [ ] Poor error messages? (add context, classification)

**❓ How can we prevent similar bugs?**
- [ ] Should we add error classification?
- [ ] Should we add validation earlier in the flow?
- [ ] Should we add telemetry to detect issues?
- [ ] Should we improve documentation?

---

## Common Patterns

### Pattern 1: Lazy Initialization with Auto-Setup

**When**: Feature needs setup that might not always be needed

**Template**:
```python
class Feature:
    def __init__(self, enable_feature=True):
        self._enable_feature = enable_feature
        self._feature_instance = None
        self._setup_attempted = False

    def _maybe_setup_feature(self):
        """Set up feature lazily on first use."""
        if not self._enable_feature:
            return

        if self._setup_attempted:
            return  # Idempotent

        self._setup_attempted = True

        if self._feature_instance is not None:
            return  # Already provided

        # Auto-setup with fallback chain
        try:
            self._feature_instance = auto_setup_feature()
        except DependencyError:
            # Fallback to simpler version
            logger.info("Using fallback (install X for full features)")
            self._feature_instance = fallback_feature()
        except Exception:
            # Graceful degradation
            logger.warning("Feature setup failed, continuing without it")
            self._enable_feature = False
```

**Examples in codebase**:
- `_maybe_setup_cache()` - [base.py:455](src/attune/workflows/base.py#L455)
- `_get_executor()` - [base.py:960](src/attune/workflows/base.py#L960)

---

### Pattern 2: Graceful Fallback Chain

**When**: Feature has multiple quality levels (best → good → minimal → disabled)

**Template**:
```python
def create_feature(quality="auto"):
    """Create feature with graceful fallback chain."""

    # Try best option first
    if quality in ("auto", "best"):
        if can_create_best():
            try:
                return BestFeature()
            except Exception:
                logger.info("Best version unavailable, trying good...")

    # Fall back to good option
    if quality in ("auto", "good"):
        if can_create_good():
            try:
                return GoodFeature()
            except Exception:
                logger.info("Good version unavailable, using minimal...")

    # Fall back to minimal
    if quality in ("auto", "minimal"):
        try:
            return MinimalFeature()
        except Exception:
            logger.warning("Minimal version failed, feature disabled")

    # Gracefully disable if everything fails
    return DisabledFeature()  # No-op placeholder
```

**Examples in codebase**:
- Cache: Hybrid → Hash-only → Disabled
- Executor: Resilient → Basic → (error)
- Prompts: XML → Plain text

---

### Pattern 3: Proactive Event Emission

**When**: Long-running operation needs progress visibility

**Template**:
```python
class LongOperation:
    def __init__(self, callback=None):
        self._callback = callback

    def _emit(self, event_type, **data):
        """Emit event to callback if provided."""
        if self._callback is None:
            return  # No overhead if not used

        event = Event(type=event_type, timestamp=now(), **data)
        try:
            self._callback(event)
        except Exception:
            # Callback errors shouldn't crash operation
            logger.debug("Callback error", exc_info=True)

    async def execute(self):
        self._emit("start", total_steps=len(self.steps))

        for i, step in enumerate(self.steps):
            self._emit("step_start", step=step, index=i)
            result = await self._run_step(step)
            self._emit("step_complete", step=step, result=result)

        self._emit("complete", results=self.results)
```

**Examples in codebase**:
- Progress tracking - [base.py:717](src/attune/workflows/base.py#L717)
- Telemetry emission - [base.py:1033](src/attune/workflows/base.py#L1033)

---

### Pattern 4: Error Classification for User Guidance

**When**: Errors need different responses (retry vs. fix config vs. investigate)

**Template**:
```python
def classify_error(error: Exception) -> ErrorInfo:
    """Classify error to guide user response."""
    error_str = str(error).lower()

    # Transient errors (retry reasonable)
    if any(word in error_str for word in ["timeout", "rate limit", "503", "502"]):
        return ErrorInfo(
            type="transient",
            severity="warning",
            transient=True,
            suggestion="Retry in a few moments. This is likely temporary."
        )

    # Configuration errors (fix config)
    if any(word in error_str for word in ["config", "api key", "not found"]):
        return ErrorInfo(
            type="config",
            severity="error",
            transient=False,
            suggestion="Check configuration: API keys, model names, providers."
        )

    # Input validation errors (fix input)
    if any(word in error_str for word in ["invalid", "validation", "malformed"]):
        return ErrorInfo(
            type="validation",
            severity="error",
            transient=False,
            suggestion="Check input data format and requirements."
        )

    # Unknown errors (investigate)
    return ErrorInfo(
        type="unknown",
        severity="error",
        transient=False,
        suggestion="Unexpected error - check logs for details."
    )
```

**Examples in codebase**:
- Workflow error classification - [base.py:828](src/attune/workflows/base.py#L828)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Silent Failures

**Bad**:
```python
try:
    result = expensive_operation()
except Exception:
    pass  # Silently ignore errors
```

**Good**:
```python
try:
    result = expensive_operation()
except Exception as e:
    logger.warning(f"Operation failed: {e}")
    result = fallback_value()
    # Still continue, but observable
```

**Why**: Silent failures hide problems. Always log, emit telemetry, or notify user.

---

### Anti-Pattern 2: Throwing Raw Exceptions

**Bad**:
```python
if api_key is None:
    raise ValueError("API key required")
```

**Good**:
```python
if api_key is None:
    raise ConfigurationError(
        "API key required. Set ANTHROPIC_API_KEY environment variable "
        "or add to .env file. See: docs.attune-ai.com/setup"
    )
```

**Why**: Context and guidance help users fix the problem.

---

### Anti-Pattern 3: Forcing Users to Configure Everything

**Bad**:
```python
# User must configure all the things
workflow = Workflow(
    cache=create_cache(...),
    executor=create_executor(...),
    telemetry=create_telemetry(...),
    progress=create_progress_tracker(...),
    # ... 10 more required configs
)
```

**Good**:
```python
# Sensible defaults, customize if needed
workflow = Workflow()  # Everything auto-configured

# Or customize specific parts
workflow = Workflow(
    cache=my_custom_cache,  # Override just this
    # Everything else: automatic
)
```

**Why**: Level 3 means anticipating needs and providing defaults. Advanced users can customize, beginners get "it just works."

---

### Anti-Pattern 4: Making Users Think About Infrastructure

**Bad**:
```python
# User must think about:
# - Which tier for each call
# - Retry logic
# - Cost tracking
# - Caching
# - Telemetry

result1 = call_llm(prompt1, tier="cheap", retry=True, cache_key="...")
cost_tracker.log(result1.cost)
telemetry.emit("llm_call", cost=result1.cost)

result2 = call_llm(prompt2, tier="capable", retry=True, cache_key="...")
# ... repeat for every call
```

**Good**:
```python
# User thinks about domain logic
class MyWorkflow(BaseWorkflow):
    async def run_stage(self, stage_name, tier, input_data):
        # Just call LLM - framework handles:
        # ✓ Tier routing (from tier_map)
        # ✓ Retry (automatic)
        # ✓ Caching (automatic)
        # ✓ Cost tracking (automatic)
        # ✓ Telemetry (automatic)
        response, tokens_in, tokens_out = await self._call_llm(
            tier=tier,
            system="You are a helpful assistant",
            user_message=input_data["prompt"]
        )
        return response, tokens_in, tokens_out
```

**Why**: Users want to build features, not infrastructure. Framework should handle plumbing automatically.

---

## Testing Empathy Levels

### Testing Level 1 (Transactional)
```python
def test_simple_getter():
    workflow = MyWorkflow()
    tier = workflow.get_tier_for_stage("analyze")
    assert tier == ModelTier.CAPABLE  # Direct mapping
```

### Testing Level 2 (Contextual)
```python
def test_error_classification():
    error = Exception("Timeout connecting to API")
    error_info = classify_error(error)

    assert error_info.type == "transient"
    assert error_info.transient == True  # Tells user: retry
    assert "retry" in error_info.suggestion.lower()

def test_cost_report_context():
    result = await workflow.execute(...)

    assert result.cost_report.total_cost > 0
    assert result.cost_report.baseline_cost > result.cost_report.total_cost  # Savings shown
    assert result.cost_report.savings_percent > 0  # Efficiency metric
```

### Testing Level 3 (Anticipatory)
```python
def test_cache_auto_setup(mocker):
    # Mock user declining dependency install
    mocker.patch("builtins.input", return_value="n")

    workflow = MyWorkflow(enable_cache=True)
    await workflow.execute(...)

    # Should fall back to hash-only, not crash
    assert workflow._cache is not None
    assert isinstance(workflow._cache, HashOnlyCache)

def test_resilience_built_in(mocker):
    # Mock transient failure followed by success
    mock_llm = mocker.patch("provider.generate")
    mock_llm.side_effect = [
        TimeoutError("Timeout"),  # First call fails
        "Success"  # Second call succeeds
    ]

    result = await workflow.execute(...)

    # Should automatically retry and succeed
    assert result.success == True
    assert mock_llm.call_count == 2  # Retry happened

def test_progress_updates():
    events = []

    def callback(event):
        events.append(event)

    workflow = MyWorkflow(progress_callback=callback)
    await workflow.execute(...)

    # Should emit start, stage start/complete for each stage, workflow complete
    assert any(e.type == "workflow_start" for e in events)
    assert any(e.type == "stage_start" for e in events)
    assert any(e.type == "stage_complete" for e in events)
    assert any(e.type == "workflow_complete" for e in events)
```

---

## Documentation Standards

### For New Features

Every new feature should include:

**1. Empathy Level Declaration**
```python
def new_feature():
    """Do something useful.

    Empathy Level: 3 (Anticipatory)
    - Automatically detects environment
    - Provides fallback if dependencies missing
    - Emits telemetry for monitoring
    """
```

**2. User Journey Documentation**
```markdown
## User Journey

**Without this feature**:
1. User manually checks environment
2. User installs dependencies
3. User configures settings
4. User monitors manually
Time: 30 minutes

**With this feature**:
1. User enables feature
2. Framework handles setup automatically
Time: 30 seconds
```

**3. Code Examples**
```markdown
## Basic Usage (Level 3 - Auto)
\`\`\`python
# Just enable, framework handles rest
workflow = Workflow(enable_feature=True)
\`\`\`

## Advanced Usage (Custom)
\`\`\`python
# Customize if needed
workflow = Workflow(
    feature=CustomFeature(
        setting=value
    )
)
\`\`\`
```

---

## Decision Framework

When designing a new feature, ask:

### 1. What empathy level should this be?

**Default to Level 3** unless:
- Low-level utility (Level 1 appropriate)
- Environment/configuration only (Level 2 appropriate)
- Advanced feature with learning (Level 4)

### 2. What's the complete user workflow?

Map out:
1. User's goal (what they're trying to achieve)
2. Steps required (what they must do currently)
3. Likely next steps (what usually follows)
4. Edge cases (what could go wrong)
5. Fallbacks (how to handle failures)

### 3. How can we anticipate needs?

- What will user likely need next?
- What configuration is usually needed?
- What errors commonly occur?
- What monitoring would help?

### 4. How do we make it transparent?

- Simple API for common case
- Observable for debugging
- Configurable for advanced users
- Telemetry for monitoring

---

## Contribution Workflow

### 1. Design Phase
- [ ] Identify empathy level target (default Level 3)
- [ ] Map complete user workflow
- [ ] Design automatic setup/fallback chain
- [ ] Plan telemetry/observability
- [ ] Document in design doc

### 2. Implementation Phase
- [ ] Implement core functionality
- [ ] Add automatic setup logic
- [ ] Implement fallback chain
- [ ] Add telemetry emission
- [ ] Add progress tracking (if long-running)
- [ ] Add error classification

### 3. Testing Phase
- [ ] Test happy path (Level 3 auto-setup)
- [ ] Test fallback chain (dependencies missing)
- [ ] Test edge cases (failures, errors)
- [ ] Test observability (telemetry, progress)
- [ ] Load test (if performance-critical)

### 4. Documentation Phase
- [ ] Add empathy level declaration
- [ ] Document user journey (before/after)
- [ ] Add code examples (basic + advanced)
- [ ] Update CHANGELOG
- [ ] Add to appropriate guide

---

## Examples to Study

**Excellent Level 3 implementations in codebase**:

1. **Cache auto-setup** - [base.py:455](src/attune/workflows/base.py#L455)
   - Lazy initialization
   - Dependency detection
   - User prompting (interactive sessions)
   - Fallback chain (hybrid → hash → disabled)

2. **Resilient executor** - [base.py:937](src/attune/workflows/base.py#L937)
   - Automatic retry with exponential backoff
   - Fallback providers
   - Circuit breaker
   - Built-in by default

3. **Progress tracking** - [base.py:717](src/attune/workflows/base.py#L717)
   - Proactive event emission
   - Optional (no overhead if unused)
   - Rich event data
   - Real-time updates

4. **Error classification** - [base.py:828](src/attune/workflows/base.py#L828)
   - Transient detection
   - User guidance
   - Observable (error_type field)

---

## Questions?

**Attune AI Philosophy**:
> "Build for the developer you wish you had as a teammate - anticipate their needs, prepare resources proactively, communicate clearly, fail gracefully, and make complexity transparent."

When in doubt:
1. Ask: "What would a Level 3 (Anticipatory) version look like?"
2. Study existing Level 3 patterns in codebase
3. Discuss in GitHub issue or PR
4. Reference this guide

---

**Last updated**: 2026-01-06
**Maintainer**: Patrick Roebuck
**Feedback**: [GitHub Issues](https://github.com/empathy-ai/attune-ai/issues)
