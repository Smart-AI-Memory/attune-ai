---
description: OOP Refactoring Plan - Architectural Consistency: **Date:** January 16, 2026 **Sprint:** Production Readiness - Phase 2B **Goal:** Refactor functional interface
---

# OOP Refactoring Plan - Architectural Consistency

**Date:** January 16, 2026
**Sprint:** Production Readiness - Phase 2B
**Goal:** Refactor functional interfaces to OOP for consistency, testability, and maintainability

---

## Executive Summary

**Problem:** Framework uses OOP throughout except for 3 critical modules that use functional design:
- `models/registry.py` - Dict + functions instead of class
- `memory/long_term.py` - No class interface
- `orchestration/meta_orchestrator.py` - Private methods reduce testability

**Solution:** Refactor to OOP while maintaining 100% backward compatibility

**Timeline:** 2 days (16 hours)
**Impact:** Enables 200+ architectural tests, improves testability, establishes consistency

---

## Refactoring Priorities

### 🔴 P0 - Critical (Day 1 Morning)
1. **Memory System** - Create proper class interfaces
   - Blocking 70+ tests
   - Critical for production

### 🟡 P1 - High (Day 1 Afternoon)
2. **Model Registry** - Wrap functional interface
   - Enables 50+ tests
   - Improves testability significantly

### 🟢 P2 - Medium (Day 2)
3. **Meta-Orchestrator** - Extract testable methods
   - Enables remaining orchestration tests
   - Better separation of concerns

---

## Refactoring #1: Memory System

**Current State:**
```python
# memory/long_term.py
# No LongTermMemory class exists!
# File contains: SecurePattern, PatternMetadata, Classification

# memory/unified.py
class UnifiedMemory:
    def __init__(self, ...):
        self.short_term = RedisShortTermMemory(...)
        self.long_term = ???  # What is this?
```

**Target State:**
```python
# memory/long_term.py
class LongTermMemory:
    """Persistent memory storage with classification."""

    def __init__(self, storage_path: str = "./memory"):
        self._storage_path = Path(storage_path)
        self._cache: dict[str, Any] = {}

    def store(self, key: str, data: dict, classification: str = "INTERNAL") -> None:
        """Store data with classification."""

    def retrieve(self, key: str) -> dict | None:
        """Retrieve data by key."""

    def delete(self, key: str) -> bool:
        """Delete data by key."""

    def list_keys(self, classification: str | None = None) -> list[str]:
        """List all keys, optionally filtered by classification."""

# memory/unified.py
class UnifiedMemory:
    """Two-tier memory with short-term (Redis) and long-term (persistent)."""

    def __init__(self, use_mock_redis: bool = False, storage_path: str = "./memory"):
        self.short_term = RedisShortTermMemory(use_mock=use_mock_redis)
        self.long_term = LongTermMemory(storage_path=storage_path)

    def store(self, key: str, data: dict, ttl: int | None = None) -> None:
        """Store in appropriate tier based on TTL."""
        if ttl:
            self.short_term.stash(key, data, ttl=ttl)
        else:
            self.long_term.store(key, data)

    def retrieve(self, key: str) -> dict | None:
        """Retrieve from short-term first, then long-term."""
        result = self.short_term.retrieve(key)
        if result is None:
            result = self.long_term.retrieve(key)
        return result

    def promote_to_long_term(self, key: str) -> bool:
        """Promote short-term memory to long-term."""
        data = self.short_term.retrieve(key)
        if data:
            self.long_term.store(key, data)
            return True
        return False

    def delete(self, key: str) -> bool:
        """Delete from both tiers."""
        st_deleted = self.short_term.delete(key)
        lt_deleted = self.long_term.delete(key)
        return st_deleted or lt_deleted
```

**Implementation Steps:**

1. **Create `LongTermMemory` class** (2 hours)
   ```bash
   # File: src/attune/memory/long_term.py

   - Move existing SecurePattern, PatternMetadata to separate file
   - Create LongTermMemory class with CRUD operations
   - Use JSON file storage for MVP
   - Add classification support
   - Add comprehensive docstrings
   ```

2. **Update `UnifiedMemory`** (1 hour)
   ```bash
   # File: src/attune/memory/unified.py

   - Initialize LongTermMemory in __init__
   - Implement store/retrieve/delete with tier logic
   - Add promote_to_long_term method
   - Add sync_tiers method
   - Document all public methods
   ```

3. **Add backward compatibility shims** (30 min)
   ```bash
   # If old code expects different interface
   # Add compatibility functions
   ```

4. **Enable memory architecture tests** (30 min)
   ```bash
   # tests/unit/memory/test_memory_architecture.py

   - Remove placeholder: LongTermMemory = None
   - Uncomment import
   - Run tests, fix failures
   ```

**Success Criteria:**
- ✅ `LongTermMemory` class exists with CRUD operations
- ✅ `UnifiedMemory` uses both tiers correctly
- ✅ 70+ memory tests pass
- ✅ No breaking changes to existing code

---

## Refactoring #2: Model Registry

**Current State:**
```python
# models/registry.py (functional design)

MODEL_REGISTRY: dict[str, dict[str, ModelInfo]] = {
    "anthropic": {
        "cheap": ModelInfo(...),
        "capable": ModelInfo(...),
        "premium": ModelInfo(...),
    },
    "openai": {...},
}

def get_model(provider: str, tier: str) -> ModelInfo | None:
    """Get model by provider and tier."""
    return MODEL_REGISTRY.get(provider, {}).get(tier)

def get_model_by_id(model_id: str) -> ModelInfo | None:
    """Get model by ID."""
    for provider_models in MODEL_REGISTRY.values():
        for model in provider_models.values():
            if model.id == model_id:
                return model
    return None
```

**Target State:**
```python
# models/registry.py (OOP design with backward compatibility)

class ModelRegistry:
    """Registry for LLM models with tier-based routing.

    Provides OOP interface for model management while maintaining
    backward compatibility with functional interface.
    """

    def __init__(self, registry: dict | None = None):
        """Initialize registry with model definitions.

        Args:
            registry: Optional custom registry (defaults to MODEL_REGISTRY)
        """
        self._registry = registry or MODEL_REGISTRY
        self._by_id_cache: dict[str, ModelInfo] = {}
        self._build_id_cache()

    def _build_id_cache(self) -> None:
        """Build cache for fast ID lookup."""
        for provider_models in self._registry.values():
            for model in provider_models.values():
                self._by_id_cache[model.id] = model

    def get_model(self, provider: str, tier: str) -> ModelInfo | None:
        """Get model by provider and tier.

        Args:
            provider: Provider name (anthropic, openai, etc.)
            tier: Model tier (cheap, capable, premium)

        Returns:
            ModelInfo if found, None otherwise
        """
        return self._registry.get(provider, {}).get(tier)

    def get_model_by_id(self, model_id: str) -> ModelInfo | None:
        """Get model by ID (fast O(1) lookup).

        Args:
            model_id: Model identifier (e.g., "claude-sonnet-3-5")

        Returns:
            ModelInfo if found, None otherwise
        """
        return self._by_id_cache.get(model_id)

    def get_all_models(self) -> dict[str, dict[str, ModelInfo]]:
        """Get all models grouped by provider and tier."""
        return self._registry

    def get_models_by_tier(self, tier: str) -> list[ModelInfo]:
        """Get all models for a specific tier across all providers.

        Args:
            tier: Model tier (cheap, capable, premium)

        Returns:
            List of ModelInfo for the tier
        """
        models = []
        for provider_models in self._registry.values():
            if tier in provider_models:
                models.append(provider_models[tier])
        return models

    def get_providers(self) -> list[str]:
        """Get list of available providers."""
        return list(self._registry.keys())

    def get_tiers(self) -> list[str]:
        """Get list of available tiers."""
        tiers = set()
        for provider_models in self._registry.values():
            tiers.update(provider_models.keys())
        return sorted(tiers)


# Backward compatibility - default instance
_default_registry = ModelRegistry()

def get_model(provider: str, tier: str) -> ModelInfo | None:
    """Get model by provider and tier (backward compatible).

    Args:
        provider: Provider name
        tier: Model tier

    Returns:
        ModelInfo if found, None otherwise
    """
    return _default_registry.get_model(provider, tier)

def get_model_by_id(model_id: str) -> ModelInfo | None:
    """Get model by ID (backward compatible).

    Args:
        model_id: Model identifier

    Returns:
        ModelInfo if found, None otherwise
    """
    return _default_registry.get_model_by_id(model_id)
```

**Implementation Steps:**

1. **Create `ModelRegistry` class** (2 hours)
   ```bash
   # File: src/attune/models/registry.py

   - Define ModelRegistry class
   - Move logic from functions to methods
   - Add ID cache for performance
   - Add utility methods (get_providers, get_tiers, etc.)
   - Comprehensive docstrings
   ```

2. **Add backward compatibility** (30 min)
   ```bash
   - Create _default_registry instance
   - Keep functional interface as wrappers
   - Ensure zero breaking changes
   ```

3. **Enable model tests** (30 min)
   ```bash
   # tests/unit/models/test_execution_and_fallback_architecture.py

   - Remove placeholder: ModelRegistry = None
   - Import ModelRegistry
   - Update tests to use class
   - Run tests, fix failures
   ```

**Success Criteria:**
- ✅ `ModelRegistry` class with full API
- ✅ Functional interface still works (backward compatible)
- ✅ 50+ model tests pass
- ✅ Performance maintained (ID cache)

---

## Refactoring #3: Meta-Orchestrator

**Current State:**
```python
# orchestration/meta_orchestrator.py

class MetaOrchestrator:
    def analyze_and_compose(self, task: str, context: dict) -> ExecutionPlan:
        """Public entry point - does everything."""
        requirements = self._analyze_task(task, context)  # Private
        agents = self._select_agents(requirements)  # Private
        strategy = self._choose_composition_pattern(requirements, agents)  # Private

        # Plan creation embedded here
        plan = ExecutionPlan(
            agents=agents,
            strategy=strategy,
            quality_gates=requirements.quality_gates,
            estimated_cost=self._estimate_cost(agents),
            estimated_duration=self._estimate_duration(agents, strategy),
        )
        return plan
```

**Target State:**
```python
# orchestration/meta_orchestrator.py

class MetaOrchestrator:
    def analyze_and_compose(self, task: str, context: dict) -> ExecutionPlan:
        """Public entry point - orchestrates the full flow."""
        requirements = self.analyze_task(task, context)  # Now public
        plan = self.create_execution_plan(requirements)  # Extracted
        return plan

    def analyze_task(self, task: str, context: dict) -> TaskRequirements:
        """Analyze task to extract requirements (public for testing).

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            TaskRequirements with complexity, domain, capabilities
        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")

        complexity = self._classify_complexity(task)
        domain = self._classify_domain(task)
        capabilities = self._extract_capabilities(domain, context)

        return TaskRequirements(
            complexity=complexity,
            domain=domain,
            capabilities_needed=capabilities,
            parallelizable=self._is_parallelizable(task),
            quality_gates=self._extract_quality_gates(task, context),
            context=context,
        )

    def create_execution_plan(self, requirements: TaskRequirements) -> ExecutionPlan:
        """Create execution plan from analyzed requirements (testable).

        Args:
            requirements: Task requirements from analyze_task()

        Returns:
            ExecutionPlan with agents, strategy, costs
        """
        agents = self._select_agents(requirements)
        strategy = self._choose_composition_pattern(requirements, agents)

        return ExecutionPlan(
            agents=agents,
            strategy=strategy,
            quality_gates=requirements.quality_gates,
            estimated_cost=self._estimate_cost(agents),
            estimated_duration=self._estimate_duration(agents, strategy),
        )

    # Keep _classify_complexity, _classify_domain, etc. as private helpers
```

**Implementation Steps:**

1. **Extract `analyze_task()` public method** (1 hour)
   ```bash
   # File: src/attune/orchestration/meta_orchestrator.py

   - Rename _analyze_task to analyze_task (public)
   - Keep internal helpers private (_classify_complexity, etc.)
   - Add comprehensive docstrings
   - Update analyze_and_compose to use public method
   ```

2. **Extract `create_execution_plan()` method** (1 hour)
   ```bash
   - Create public create_execution_plan(requirements)
   - Move plan creation logic from analyze_and_compose
   - Update analyze_and_compose to call it
   - Add docstrings
   ```

3. **Enable orchestration tests** (1 hour)
   ```bash
   # tests/unit/orchestration/test_meta_orchestration_architecture.py

   - Update tests to use analyze_task() instead of _analyze_task()
   - Update tests to use create_execution_plan()
   - Remove @pytest.mark.skip decorators
   - Run tests, fix failures
   ```

**Success Criteria:**
- ✅ `analyze_task()` is public and testable
- ✅ `create_execution_plan()` is extracted
- ✅ 80+ orchestration tests pass
- ✅ No breaking changes to analyze_and_compose()

---

## Implementation Timeline

### Day 1 Morning (4 hours) - P0: Memory System

**9:00 AM - 11:00 AM: Create LongTermMemory**
- [ ] Create `src/attune/memory/long_term.py` (new implementation)
- [ ] Define `LongTermMemory` class with CRUD operations
- [ ] Implement JSON file storage
- [ ] Add classification support
- [ ] Write comprehensive docstrings

**11:00 AM - 12:00 PM: Update UnifiedMemory**
- [ ] Update `src/attune/memory/unified.py`
- [ ] Initialize LongTermMemory in constructor
- [ ] Implement tier logic (store, retrieve, delete)
- [ ] Add promote_to_long_term, sync_tiers methods

**12:00 PM - 1:00 PM: Enable Memory Tests**
- [ ] Lunch + fix test imports
- [ ] Enable memory architecture tests
- [ ] Run tests, fix failures
- [ ] Verify 70+ tests pass

### Day 1 Afternoon (4 hours) - P1: Model Registry

**1:00 PM - 3:00 PM: Create ModelRegistry**
- [ ] Update `src/attune/models/registry.py`
- [ ] Define `ModelRegistry` class
- [ ] Implement all methods (get_model, get_model_by_id, etc.)
- [ ] Add ID cache for performance
- [ ] Write comprehensive docstrings

**3:00 PM - 3:30 PM: Backward Compatibility**
- [ ] Create _default_registry instance
- [ ] Keep functional interface as wrappers
- [ ] Test backward compatibility

**3:30 PM - 5:00 PM: Enable Model Tests**
- [ ] Enable model architecture tests
- [ ] Fix test failures
- [ ] Verify 50+ tests pass
- [ ] Run coverage report

### Day 2 Morning (4 hours) - P2: Meta-Orchestrator

**9:00 AM - 10:00 AM: Extract analyze_task()**
- [ ] Make `_analyze_task()` public
- [ ] Update analyze_and_compose to call it
- [ ] Add docstrings

**10:00 AM - 11:00 AM: Extract create_execution_plan()**
- [ ] Create `create_execution_plan()` method
- [ ] Move logic from analyze_and_compose
- [ ] Update analyze_and_compose to call it

**11:00 AM - 1:00 PM: Enable Orchestration Tests**
- [ ] Update tests to use public methods
- [ ] Remove @pytest.mark.skip decorators
- [ ] Fix test failures
- [ ] Verify 80+ tests pass

### Day 2 Afternoon (4 hours) - Validation & Documentation

**1:00 PM - 3:00 PM: Full Test Suite**
- [ ] Run ALL 200+ architectural tests
- [ ] Fix remaining failures
- [ ] Verify coverage improvement

**3:00 PM - 4:00 PM: Coverage Measurement**
- [ ] Run pytest with coverage on all 3 modules
- [ ] Generate HTML report
- [ ] Document coverage improvements

**4:00 PM - 5:00 PM: Documentation**
- [ ] Update ARCHITECTURAL_GAPS_ANALYSIS.md (mark as resolved)
- [ ] Create REFACTORING_RESULTS.md
- [ ] Update CRITICAL_TEST_GAPS.md with new coverage

---

## Testing Strategy

### Backward Compatibility Testing

```bash
# Test that old code still works

# Memory
python -c "from attune.memory.unified import UnifiedMemory; m = UnifiedMemory()"

# Models (functional interface)
python -c "from attune.models.registry import get_model; print(get_model('anthropic', 'cheap'))"

# Orchestrator
python -c "from attune.orchestration.meta_orchestrator import MetaOrchestrator; o = MetaOrchestrator(); p = o.analyze_and_compose('test task')"
```

### New API Testing

```bash
# Test new OOP interfaces

# Memory
python -c "from attune.memory.long_term import LongTermMemory; m = LongTermMemory(); m.store('key', {'data': 'value'})"

# Models (class interface)
python -c "from attune.models.registry import ModelRegistry; r = ModelRegistry(); print(r.get_model('anthropic', 'cheap'))"

# Orchestrator (public methods)
python -c "from attune.orchestration.meta_orchestrator import MetaOrchestrator; o = MetaOrchestrator(); r = o.analyze_task('test task', {})"
```

### Architectural Tests

```bash
# Run all architectural tests
pytest tests/unit/orchestration/test_meta_orchestration_architecture.py -v
pytest tests/unit/memory/test_memory_architecture.py -v
pytest tests/unit/models/test_execution_and_fallback_architecture.py -v

# Expected results:
# - 200+ tests executable
# - 180+ tests passing (90%+)
# - 20 tests skipped (fallback policies, etc.)
```

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation:**
- Keep all functional interfaces as wrappers
- Create _default_registry instances
- Comprehensive backward compatibility tests

**Rollback Plan:**
- All changes in feature branch
- Can revert easily if issues arise
- Old functional interfaces never removed

### Risk 2: Performance Regression
**Mitigation:**
- Add caching where needed (ModelRegistry ID cache)
- Profile before/after
- Benchmark critical paths

**Acceptance:**
- < 5% performance degradation acceptable
- If > 5%, optimize or revert

### Risk 3: Test Failures Reveal Bugs
**Mitigation:**
- This is GOOD - find bugs now, not in production
- Fix bugs as discovered
- Document learnings

**Acceptance:**
- Finding bugs is success, not failure
- Better now than in production

---

## Success Metrics

### Coverage Improvement

**Before Refactoring:**
- Meta-orchestrator: 22.53%
- Memory (unified): 27.39%
- Memory (short-term): 18.80%
- Memory (long-term): N/A (no class)
- Models (registry): 60.87%
- Models (fallback): 21.07%
- **Overall Critical Paths: ~25%**

**After Refactoring (Target):**
- Meta-orchestrator: 75%+ (enable 80 tests)
- Memory (unified): 85%+ (enable 70 tests)
- Memory (long-term): 80%+ (new class)
- Models (registry): 85%+ (enable 50 tests)
- **Overall Critical Paths: 80%+**

**Expected Overall Framework Coverage:**
- Before: 54.67%
- After: 70-75% (+15-20 points)

### Test Enablement

- 200+ architectural tests written
- 180+ tests passing
- 20 tests skipped (documented gaps)
- **0 placeholder classes** (ModelRegistry = None, etc.)

### Architectural Quality

- ✅ OOP consistency across all modules
- ✅ Testable public APIs
- ✅ Backward compatibility maintained
- ✅ Clear separation of concerns
- ✅ Comprehensive documentation

---

## Deliverables

### Code Changes

1. **`src/attune/memory/long_term.py`** (NEW)
   - LongTermMemory class with CRUD operations

2. **`src/attune/memory/unified.py`** (MODIFIED)
   - Initialize LongTermMemory
   - Complete tier logic

3. **`src/attune/models/registry.py`** (MODIFIED)
   - ModelRegistry class
   - Backward compatible functional wrappers

4. **`src/attune/orchestration/meta_orchestrator.py`** (MODIFIED)
   - Public analyze_task()
   - Extracted create_execution_plan()

### Test Changes

5. **`tests/unit/memory/test_memory_architecture.py`** (ENABLED)
   - Remove placeholders
   - Enable 70+ tests

6. **`tests/unit/models/test_execution_and_fallback_architecture.py`** (ENABLED)
   - Remove placeholders
   - Enable 50+ tests

7. **`tests/unit/orchestration/test_meta_orchestration_architecture.py`** (ENABLED)
   - Remove @pytest.mark.skip
   - Enable 80+ tests

### Documentation

8. **`docs/REFACTORING_RESULTS.md`** (NEW)
   - Before/after metrics
   - Coverage improvements
   - Lessons learned

9. **`docs/ARCHITECTURAL_GAPS_ANALYSIS.md`** (UPDATED)
   - Mark gaps as resolved
   - Document solutions

10. **`docs/CRITICAL_TEST_GAPS.md`** (UPDATED)
    - Update coverage numbers
    - Mark P0 items complete

---

## Rollout Plan

### Phase 1: Memory System (Day 1 Morning)
- Create LongTermMemory
- Update UnifiedMemory
- Enable memory tests
- **Checkpoint:** 70+ memory tests passing

### Phase 2: Model Registry (Day 1 Afternoon)
- Create ModelRegistry class
- Add backward compatibility
- Enable model tests
- **Checkpoint:** 50+ model tests passing

### Phase 3: Meta-Orchestrator (Day 2 Morning)
- Extract public methods
- Enable orchestration tests
- **Checkpoint:** 80+ orchestration tests passing

### Phase 4: Validation (Day 2 Afternoon)
- Run full test suite (200+ tests)
- Measure coverage improvement
- Create documentation
- **Checkpoint:** Coverage at 70-75%, production ready

---

## Post-Refactoring

### Immediate Next Steps
- Continue with Phase 3 of original sprint plan
- Test CLI integration
- Test workflow base class
- Test real tools integration

### Future Improvements
- Add FallbackPolicy class (P1 gap)
- Implement learning loop (P2)
- Add advanced caching (P2)
- Performance optimization (P3)

---

**Status:** ✅ Plan Complete - Ready for Execution
**Estimated Effort:** 16 hours over 2 days
**Expected ROI:** +15-20 percentage points coverage, 200+ tests enabled
**Risk Level:** Low (backward compatible, can rollback)

---

**Approval Required:** YES
**Ready to Start:** YES
**Next Action:** Execute Day 1 Morning - Create LongTermMemory class
