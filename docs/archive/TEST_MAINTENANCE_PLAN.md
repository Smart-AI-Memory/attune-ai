---
description: Test Suite Maintenance Plan: **Created:** 2026-01-24 **Status:** Active **Owner:** Engineering Team --- ## Executive Summary This document provides actionable p
---

# Test Suite Maintenance Plan

**Created:** 2026-01-24
**Status:** Active
**Owner:** Engineering Team

---

## Executive Summary

This document provides actionable plans for three critical test maintenance areas:
1. **Re-enabling ignored tests** in pytest.ini
2. **Resolving xfail tests** in test_composition_patterns.py
3. **Refactoring slow tests** that use time.sleep()

---

## Part 1: Re-enable Ignored Tests

### Current State

The following tests are **ignored** in `pytest.ini` (lines 25-33):

| File | Reason (Inferred) | Priority |
|------|------------------|----------|
| `tests/test_base_wizard_exceptions.py` | Unknown failure | P2 |
| `tests/test_wizard_api_integration.py` | Integration test | P3 |
| `tests/unit/memory/test_memory_architecture.py` | Architecture changes | P1 |
| `tests/unit/models/test_execution_and_fallback_architecture.py` | Model changes | P1 |
| `tests/unit/orchestration/test_composition_patterns.py` | Real agent dependencies | P0 |
| `tests/integration/` (entire directory) | Integration tests | P2 |
| `tests/test_llm_integration.py` | LLM API required | P3 |
| `tests/unit/orchestration/test_execution_strategies.py` | Real agent dependencies | P1 |
| `tests/unit/workflows/test_orchestrated_release_prep.py` | Workflow changes | P2 |

### Re-enablement Plan

#### Phase 1: Quick Wins (1-2 days)

**Step 1: Run each ignored file individually to diagnose**
```bash
# For each file, run to see actual errors
pytest tests/test_base_wizard_exceptions.py -v --no-header 2>&1 | head -50
pytest tests/unit/memory/test_memory_architecture.py -v --no-header 2>&1 | head -50
# ... repeat for each file
```

**Step 2: Categorize failures**
- Import errors -> Fix imports
- Missing fixtures -> Add to conftest
- Timing issues -> Mock time
- Real agent issues -> Add mocks

#### Phase 2: Mock Real Agents (3-5 days)

The main issue with `test_composition_patterns.py` and `test_execution_strategies.py` is they use **real agents** that:
- Make actual API calls
- Have unpredictable outputs
- Return `success=False` based on codebase state

**Solution: Create Mock Agent Factory**

```python
# tests/conftest.py or tests/fixtures/mock_agents.py

@pytest.fixture
def mock_agent_result():
    """Create predictable mock agent results."""
    return AgentResult(
        success=True,
        output={"analysis": "Mock analysis", "score": 0.85},
        confidence=0.9,
        agent_id="mock_agent",
        duration=0.1
    )

@pytest.fixture
def mock_agents(mock_agent_result):
    """Create mock agents that return predictable results."""
    agents = []
    for i in range(4):
        agent = Mock(spec=AgentTemplate)
        agent.id = f"mock_agent_{i}"
        agent.execute = AsyncMock(return_value=mock_agent_result)
        agents.append(agent)
    return agents
```

#### Phase 3: Integration Test Strategy (1 week)

For `tests/integration/` directory:
1. Mark with `@pytest.mark.integration`
2. Run separately in CI: `pytest -m integration`
3. Allow failures in nightly builds, not PR checks

**Update pytest.ini:**
```ini
# Remove --ignore=tests/integration/
# Add to markers:
markers =
    integration: integration tests (run separately)

# In CI, run unit tests by default:
# pytest -m "not integration"
```

#### Phase 4: LLM Tests (Separate CI Job)

For `tests/test_llm_integration.py`:
1. Create mock LLM responses for unit testing
2. Run real LLM tests only in nightly CI with API keys
3. Use `@pytest.mark.llm` marker

---

## Part 2: Resolve xfail Tests in test_composition_patterns.py

### Current xfail Tests (24 total)

| Test | Line | Root Cause | Fix Strategy |
|------|------|-----------|--------------|
| `test_parallel_execution_of_independent_agents` | 69-71 | Real agents return success=False | Use mock agents |
| `test_parallel_result_aggregation` | 104-106 | Real agents return success=False | Use mock agents |
| `test_parallel_performance_faster_than_sequential` | 144 | Timing assertions flaky | Remove timing assertion or widen tolerance |
| `test_sequential_execution_maintains_order` | 198-200 | Real agents return success=False | Use mock agents |
| `test_sequential_context_passing_between_agents` | 223-225 | Context snapshot timing | Fix context capture |
| `test_sequential_dependency_chain_validation` | 272-274 | Real agents return success=False | Use mock agents |
| `test_sequential_state_accumulation` | 293-295 | Real agents return success=False | Use mock agents |
| `test_refinement_iterative_refinement_of_results` | 326-328 | Real agents return success=False | Use mock agents |
| `test_refinement_quality_improvement_tracking` | 346-348 | Real agents return success=False | Use mock agents |
| `test_refinement_convergence_detection` | 367-369 | Real agents return success=False | Use mock agents |
| `test_refinement_max_iteration_limits` | 385-387 | Real agents return success=False | Use mock agents |
| `test_hierarchical_manager_worker_delegation` | 434-436 | Real agents return success=False | Use mock agents |
| `test_hierarchical_task_decomposition` | 457-459 | Real agents return success=False | Use mock agents |
| `test_hierarchical_result_synthesis` | 477-479 | Real agents return success=False | Use mock agents |
| `test_hierarchical_coordinator_role` | 497-499 | Real agents return success=False | Use mock agents |
| `test_hierarchical_subtask_distribution` | 517-519 | Real agents return success=False | Use mock agents |
| `TestDebateComposition` (class) | 546 | Real agents return success=False | Use mock agents |
| `TestVotingComposition` (class) | 655 | Real agents return success=False | Use mock agents |

### Resolution Strategy

**Option A: Complete Mock Refactor (Recommended)**

Replace all real agent calls with mocks:

```python
# Before (flaky)
@pytest.mark.xfail(reason="Uses real agents")
async def test_parallel_execution(self, test_agents, test_context):
    result = await strategy.execute(test_agents[:3], test_context)
    assert result.success  # Flaky!

# After (reliable)
async def test_parallel_execution(self, mock_agents, test_context):
    strategy = ParallelStrategy()
    result = await strategy.execute(mock_agents[:3], test_context)
    assert result.success  # Predictable
    assert len(result.outputs) == 3
```

**Option B: Separate Real Agent Tests**

Keep current tests but:
1. Create `tests/real_agent/` directory
2. Mark with `@pytest.mark.real_agent`
3. Run only in nightly CI
4. Remove xfail, add skip for CI: `@pytest.mark.skipif(os.getenv('CI'), reason="Real agents")`

### TODO Tracking

```
# GitHub Issues to Create:

[ ] Issue #XXX: Refactor test_composition_patterns.py to use mock agents
    - Priority: P0
    - Estimate: 3-5 days
    - Labels: testing, reliability

[ ] Issue #XXX: Create mock agent factory fixture
    - Priority: P0
    - Estimate: 1 day
    - Labels: testing, fixtures

[ ] Issue #XXX: Remove timing assertions from parallel tests
    - Priority: P1
    - Estimate: 2 hours
    - Labels: testing, flaky
```

---

## Part 3: Refactor Slow Tests (time.sleep)

### Files with time.sleep() (22 total)

| File | Sleep Count | Max Delay | Fix Strategy |
|------|-------------|-----------|--------------|
| `tests/test_timeout.py` | 2 | 1.0s | Mock time |
| `tests/test_control_panel_security.py` | 1 | 1.1s | Mock time |
| `tests/test_resilience.py` | 2 | 0.02s x 50 | Mock time |
| `tests/backend/test_auth_security.py` | 2 | 1.1s | Mock time |
| `tests/unit/cache/test_cache_modules.py` | 4 | 1.5s | Mock time |
| `tests/unit/cache/test_hybrid_cache.py` | 1 | 1.1s | Mock time |
| `tests/unit/cache/test_hash_cache.py` | 1 | Unknown | Mock time |
| `tests/unit/memory/test_short_term_failures.py` | 3 | 0.001s | Mock time |
| `tests/unit/memory/test_memory_architecture.py` | ? | Unknown | Mock time |
| `tests/unit/memory/test_control_panel.py` | ? | Unknown | Mock time |
| `tests/unit/meta_workflows/test_session_context.py` | ? | Unknown | Mock time |
| `tests/unit/meta_workflows/test_workflow.py` | ? | Unknown | Mock time |
| `tests/unit/meta_workflows/test_pattern_learner.py` | 1 | 1.1s | Mock time |
| `tests/unit/models/test_execution_and_fallback_architecture.py` | ? | Unknown | Mock time |
| `tests/unit/resilience/test_timeout.py` | ? | Unknown | Mock time |
| `tests/unit/resilience/test_circuit_breaker.py` | ? | Unknown | Mock time |
| `tests/unit/socratic/test_session.py` | ? | Unknown | Mock time |
| `tests/unit/workflows/test_workflow_execution.py` | ? | Unknown | Mock time |
| `tests/integration/test_meta_workflow_e2e.py` | ? | Unknown | Mock time |
| `tests/test_executor_integration.py` | ? | Unknown | Mock time |
| `tests/test_perf_audit_workflow.py` | ? | Unknown | Mock time |
| `tests/agents/test_compliance_db.py` | ? | Unknown | Mock time |

### Refactoring Strategy

#### Install pytest-freezegun

```bash
pip install pytest-freezegun
```

#### Pattern 1: TTL/Expiration Testing

```python
# Before (slow - 1.5s wait)
def test_cache_ttl_expiration(self):
    cache.set("key", "value", ttl=1)
    time.sleep(1.5)  # Wait for expiration
    assert cache.get("key") is None

# After (instant)
from freezegun import freeze_time
from datetime import datetime, timedelta

def test_cache_ttl_expiration(self):
    with freeze_time("2026-01-24 12:00:00") as frozen:
        cache.set("key", "value", ttl=1)
        frozen.move_to("2026-01-24 12:00:02")  # Jump 2 seconds
        assert cache.get("key") is None
```

#### Pattern 2: Timeout Testing

```python
# Before (slow - waits for timeout)
def test_request_timeout(self):
    start = time.time()
    with pytest.raises(TimeoutError):
        make_request(timeout=1.0)  # Waits 1 second
    assert time.time() - start >= 1.0

# After (instant with mock)
from unittest.mock import patch, AsyncMock

def test_request_timeout(self):
    with patch('module.time.sleep'):  # Skip actual sleep
        with patch('module.make_request', side_effect=TimeoutError):
            with pytest.raises(TimeoutError):
                make_request(timeout=1.0)
```

#### Pattern 3: Rate Limiting

```python
# Before (slow - tests rate limit with real delays)
def test_rate_limiter(self):
    for i in range(10):
        time.sleep(0.1)  # 1 second total
        limiter.check()

# After (mock time advancement)
@patch('module.time.time')
def test_rate_limiter(self, mock_time):
    mock_time.return_value = 1000.0
    for i in range(10):
        mock_time.return_value += 0.1  # Advance time
        limiter.check()
```

### Priority Order for Refactoring

1. **High Impact (>1s delay)**
   - `test_cache_modules.py` (1.5s x 4 = 6s)
   - `test_control_panel_security.py` (1.1s)
   - `test_auth_security.py` (1.1s x 2 = 2.2s)
   - `test_hybrid_cache.py` (1.1s)
   - `test_pattern_learner.py` (1.1s)
   - `test_timeout.py` (1.0s x 2 = 2s)

2. **Medium Impact (0.1-1s)**
   - `test_resilience.py` (0.02s x 50 = 1s)

3. **Low Impact (<0.1s)**
   - `test_short_term_failures.py` (0.001s - negligible)

### Estimated Savings

| Category | Current | After | Savings |
|----------|---------|-------|---------|
| High Impact | ~13s | <0.5s | 12.5s |
| Medium Impact | ~1s | <0.1s | 0.9s |
| Total | ~14s | <1s | **~13s per run** |

---

## Implementation Checklist

### Week 1: Foundation

- [ ] Create mock agent factory fixture
- [ ] Refactor 5 highest-priority xfail tests
- [ ] Install and configure pytest-freezegun
- [ ] Refactor top 3 slow test files

### Week 2: Re-enablement

- [ ] Run and diagnose all ignored test files
- [ ] Fix import/fixture issues
- [ ] Re-enable tests/unit/memory/test_memory_architecture.py
- [ ] Re-enable tests/unit/models/test_execution_and_fallback_architecture.py

### Week 3: Completion

- [ ] Complete all xfail test refactoring
- [ ] Remove --ignore entries from pytest.ini
- [ ] Set up integration test CI job
- [ ] Document testing patterns

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Ignored test files | 8+ | 0 |
| xfail tests | 24 | 0 |
| time.sleep() in tests | 22 files | <5 files |
| Test suite duration | ~5 min | <3 min |
| CI reliability | ~85% | >98% |

---

## Related Documents

- [TESTING_PATTERNS.md](./TESTING_PATTERNS.md)
- [TESTING_ONBOARDING.md](./TESTING_ONBOARDING.md)
- [CODING_STANDARDS.md](./CODING_STANDARDS.md)
