# Behavioral Testing Quick Start Guide

**For:** Engineers implementing the remaining 133 behavioral tests
**Last Updated:** 2026-01-29
**See Also:** BEHAVIORAL_TEST_FINAL_REPORT.md

---

## Quick Reference

### File Locations
```
Templates:  tests/behavioral/generated/test_*_behavioral.py
Source:     src/attune/*.py
Patterns:   tests/behavioral/generated/ (batches 1-4 examples)
Docs:       BEHAVIORAL_TEST_FINAL_REPORT.md
```

### Run Tests
```bash
# Run all behavioral tests
pytest tests/behavioral/ -v

# Run specific module
pytest tests/behavioral/generated/test_pattern_library_behavioral.py -v

# Run with coverage
pytest tests/behavioral/generated/test_pattern_library_behavioral.py \
  --cov=src/attune/pattern_library --cov-report=term-missing -v

# Run quick (skip slow tests)
pytest tests/behavioral/ -v -m "not slow"
```

---

## Implementation Checklist

### Before You Start
- [ ] Read this guide
- [ ] Review 2-3 implemented examples (batches 1-4)
- [ ] Understand the module you're testing (read source code)
- [ ] Check for existing unit tests (may provide insights)

### Implementation Steps
1. [ ] Open template file (e.g., `test_pattern_library_behavioral.py`)
2. [ ] Read module source to understand behavior
3. [ ] Replace `pass` statements with actual tests
4. [ ] Follow Given-When-Then pattern
5. [ ] Add assertions for expected behavior
6. [ ] Test error paths (invalid input, edge cases)
7. [ ] Run tests locally: `pytest <file> -v`
8. [ ] Check coverage: `pytest <file> --cov=<module> --cov-report=term-missing`
9. [ ] Aim for 85%+ coverage
10. [ ] Commit with clear message

### After Implementation
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥85%
- [ ] Clear test names
- [ ] Good docstrings
- [ ] No skipped tests (unless documented)

---

## Testing Patterns

### Pattern 1: Given-When-Then

```python
def test_feature_returns_expected_value(self):
    """Test feature returns expected value for valid input."""
    # Given (Setup)
    obj = MyClass(config={"mode": "test"})
    input_data = {"id": "123", "name": "Test"}

    # When (Execute)
    result = obj.feature(input_data)

    # Then (Assert)
    assert result is not None
    assert result["status"] == "success"
    assert result["id"] == "123"
```

### Pattern 2: Error Testing

```python
def test_feature_raises_error_for_invalid_input(self):
    """Test feature raises ValueError for missing required field."""
    # Given
    obj = MyClass()
    invalid_input = {}  # Missing 'id'

    # When/Then
    with pytest.raises(ValueError, match="id is required"):
        obj.feature(invalid_input)
```

### Pattern 3: Mocking External Dependencies

```python
@patch('attune.pattern_library.redis_client')
def test_feature_with_redis_mock(self, mock_redis):
    """Test feature uses Redis correctly."""
    # Given
    mock_redis.get.return_value = b'{"cached": "data"}'
    obj = PatternLibrary()

    # When
    result = obj.get_from_cache("key123")

    # Then
    mock_redis.get.assert_called_once_with("key123")
    assert result == {"cached": "data"}
```

### Pattern 4: Async Testing

```python
@pytest.mark.asyncio
async def test_async_feature(self):
    """Test async feature completes successfully."""
    # Given
    obj = AsyncWorkflow()
    input_data = {"task": "test"}

    # When
    result = await obj.execute_async(input_data)

    # Then
    assert result["status"] == "completed"
```

### Pattern 5: Fixtures for Common Setup

```python
@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {
        "mode": "test",
        "timeout": 30,
        "retries": 3
    }

def test_feature_with_fixture(self, sample_config):
    """Test feature uses configuration correctly."""
    # Given
    obj = MyClass(config=sample_config)

    # When
    result = obj.initialize()

    # Then
    assert result["timeout"] == 30
```

---

## Common Mocking Scenarios

### Mocking Redis

```python
from unittest.mock import patch, MagicMock

@patch('attune.module_name.redis_client')
def test_with_redis(self, mock_redis):
    # Setup Redis mock
    mock_redis.get.return_value = b'{"key": "value"}'
    mock_redis.set.return_value = True

    # Test uses mock
    obj = MyClass()
    result = obj.get_data("key")

    # Verify interactions
    mock_redis.get.assert_called_once()
```

### Mocking LLM Client

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_llm_mock(self):
    # Create async mock
    mock_client = AsyncMock()
    mock_client.generate.return_value = {
        "content": "Test response",
        "tokens": 50
    }

    # Inject mock
    workflow = MyWorkflow(llm_client=mock_client)
    result = await workflow.execute()

    # Verify
    assert result["content"] == "Test response"
    mock_client.generate.assert_called_once()
```

### Mocking File I/O

```python
from unittest.mock import mock_open, patch

def test_file_reading(self):
    # Mock file content
    mock_file = mock_open(read_data='{"test": "data"}')

    with patch('builtins.open', mock_file):
        result = MyClass.load_from_file("config.json")

    # Verify
    assert result["test"] == "data"
    mock_file.assert_called_once_with("config.json", "r")
```

---

## Test Organization

### Class-Based Tests

```python
class TestMyClass:
    """Behavioral tests for MyClass."""

    def test_initialization(self):
        """Test MyClass initializes with default config."""
        obj = MyClass()
        assert obj is not None
        assert obj.config is not None

    def test_feature_happy_path(self):
        """Test feature succeeds with valid input."""
        obj = MyClass()
        result = obj.feature({"id": "123"})
        assert result["status"] == "success"

    def test_feature_error_path(self):
        """Test feature handles errors gracefully."""
        obj = MyClass()
        with pytest.raises(ValueError):
            obj.feature({})  # Invalid input


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_helper_function(self):
        """Test helper function returns expected value."""
        result = my_helper("input")
        assert result == "expected_output"
```

---

## Coverage Guidelines

### What to Test

✅ **Do test:**
- Happy path (valid input → expected output)
- Error paths (invalid input → expected error)
- Edge cases (empty, None, boundary values)
- State changes (object state before/after)
- Side effects (calls to other services)

❌ **Don't over-test:**
- Private methods (test through public API)
- Third-party code (mock it instead)
- Trivial getters/setters (unless complex logic)

### Coverage Targets

```python
# Aim for these coverage levels
Critical modules:  90%+
High priority:     80%+
Medium priority:   70%+
Lower priority:    50%+
```

---

## Troubleshooting

### Issue: Import Errors

```python
# Problem
from attune.my_module import MyClass  # ModuleNotFoundError

# Solution: Check sys.path or use relative imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from attune.my_module import MyClass
```

### Issue: Async Tests Not Running

```python
# Problem
async def test_my_async_function():  # Doesn't run
    result = await my_async_function()
    assert result

# Solution: Add pytest.mark.asyncio
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result
```

### Issue: Mock Not Working

```python
# Problem
@patch('my_module.external_function')
def test_with_mock(mock_fn):
    my_function()  # Doesn't use mock

# Solution: Patch where it's used, not where it's defined
# If my_function does: from external import function
# Patch: 'my_module.function', not 'external.function'

@patch('my_module.function')  # Patch in namespace where used
def test_with_mock(mock_fn):
    my_function()  # Now uses mock
```

### Issue: Redis Tests Failing

```python
# Problem: Tests try to connect to real Redis

# Solution 1: Mock Redis client
@patch('attune.module.redis_client')
def test_with_mock_redis(mock_redis):
    # Redis is mocked
    pass

# Solution 2: Use fakeredis
import fakeredis
def test_with_fake_redis():
    fake_redis = fakeredis.FakeRedis()
    obj = MyClass(redis_client=fake_redis)
    # Works like real Redis, no network
```

---

## Priority Order for Implementation

### Week 1-2: Critical (16 modules)
Start with these - they're core framework functionality:

1. `test_pattern_library_behavioral.py` ⭐⭐⭐
2. `test_core_behavioral.py` ⭐⭐⭐
3. `test_exceptions_behavioral.py` ⭐⭐⭐
4. `test_coordination_behavioral.py` ⭐⭐⭐
5. `test_persistence_behavioral.py` ⭐⭐⭐
6. `test_platform_utils_behavioral.py` ⭐⭐
7. `test_trust_building_behavioral.py` ⭐⭐
8. `test_emergence_behavioral.py` ⭐⭐
9. `test_discovery_behavioral.py` ⭐⭐
10. `test_pattern_cache_behavioral.py` ⭐⭐
11. `test_workflow_behavioral.py` ⭐⭐⭐
12. `test_base_behavioral.py` ⭐⭐⭐
13. `test_circuit_breaker_behavioral.py` ⭐⭐
14. `test_tier_recommender_behavioral.py` ⭐⭐
15. `test_risk_analyzer_behavioral.py` ⭐⭐
16. `test_generator_behavioral.py` ⭐⭐

### Week 3-4: High Priority - Memory (12 modules)
Memory systems are complex but critical:

17. `test_unified_behavioral.py`
18. `test_graph_behavioral.py`
19. `test_nodes_behavioral.py`
20. `test_edges_behavioral.py`
21. `test_short_term_behavioral.py`
22. `test_long_term_behavioral.py`
23. `test_cross_session_behavioral.py`
24. `test_file_session_behavioral.py`
25. `test_control_panel_behavioral.py`
26. `test_claude_memory_behavioral.py`
27. `test_redis_memory_behavioral.py`
28. `test_redis_bootstrap_behavioral.py`

### Week 3-4: High Priority - Routing (5 modules)

29. `test_smart_router_behavioral.py`
30. `test_classifier_behavioral.py`
31. `test_chain_executor_behavioral.py`
32. `test_models_behavioral.py`
33. `test_workflow_registry_behavioral.py`

---

## Example: Complete Implementation

Here's a full example showing before/after:

### Before (Template)

```python
"""Behavioral tests for pattern_library.py - AUTO-GENERATED TEMPLATE."""
import pytest
from attune.pattern_library import PatternLibrary

class TestPatternLibrary:
    def test_match(self):
        """Test PatternLibrary.match() behavior."""
        # TODO: Implement test
        pass  # Remove after implementing
```

### After (Implemented)

```python
"""Behavioral tests for pattern_library.py."""
import pytest
from unittest.mock import patch, MagicMock
from attune.pattern_library import PatternLibrary, Pattern


class TestPatternLibrary:
    """Behavioral tests for PatternLibrary class."""

    def test_initializes_with_empty_patterns(self):
        """Test PatternLibrary initializes with empty pattern list."""
        # Given/When
        library = PatternLibrary()

        # Then
        assert library is not None
        assert len(library.patterns) == 0

    def test_add_pattern_increases_count(self):
        """Test adding pattern increases pattern count."""
        # Given
        library = PatternLibrary()
        pattern = Pattern(id="test1", name="Test Pattern", regex="test.*")

        # When
        library.add_pattern(pattern)

        # Then
        assert len(library.patterns) == 1
        assert library.patterns[0].id == "test1"

    def test_match_returns_matching_patterns(self):
        """Test match returns patterns that match input."""
        # Given
        library = PatternLibrary()
        pattern1 = Pattern(id="p1", regex="error.*")
        pattern2 = Pattern(id="p2", regex="success.*")
        library.add_pattern(pattern1)
        library.add_pattern(pattern2)

        # When
        matches = library.match("error occurred")

        # Then
        assert len(matches) == 1
        assert matches[0].id == "p1"

    def test_match_returns_empty_for_no_matches(self):
        """Test match returns empty list when no patterns match."""
        # Given
        library = PatternLibrary()
        pattern = Pattern(id="p1", regex="error.*")
        library.add_pattern(pattern)

        # When
        matches = library.match("success")

        # Then
        assert matches == []

    def test_match_raises_error_for_none_input(self):
        """Test match raises ValueError for None input."""
        # Given
        library = PatternLibrary()

        # When/Then
        with pytest.raises(ValueError, match="input cannot be None"):
            library.match(None)

    @patch('attune.pattern_library.redis_client')
    def test_caches_patterns_in_redis(self, mock_redis):
        """Test pattern matching results are cached in Redis."""
        # Given
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.set.return_value = True
        library = PatternLibrary(cache_enabled=True)
        pattern = Pattern(id="p1", regex="test.*")
        library.add_pattern(pattern)

        # When
        matches = library.match("test input")

        # Then
        assert mock_redis.set.called
        cache_key = mock_redis.set.call_args[0][0]
        assert "test input" in cache_key
```

---

## Common Pitfalls

### ❌ Pitfall 1: Testing Implementation, Not Behavior

```python
# Bad: Tests implementation details
def test_uses_specific_algorithm():
    obj = MyClass()
    assert obj._internal_method() == "specific_value"

# Good: Tests behavior
def test_produces_correct_result():
    obj = MyClass()
    result = obj.public_method({"input": "data"})
    assert result["output"] == "expected"
```

### ❌ Pitfall 2: Brittle Assertions

```python
# Bad: Too specific, breaks on minor changes
assert result == {
    "timestamp": "2026-01-29T12:00:00",
    "status": "success",
    "details": "Processing completed at 12:00 PM"
}

# Good: Tests important properties
assert result["status"] == "success"
assert "timestamp" in result
assert "details" in result
```

### ❌ Pitfall 3: Missing Error Tests

```python
# Bad: Only tests happy path
def test_feature_works(self):
    result = my_function({"valid": "input"})
    assert result["status"] == "success"

# Good: Tests both paths
def test_feature_succeeds_with_valid_input(self):
    result = my_function({"valid": "input"})
    assert result["status"] == "success"

def test_feature_raises_error_for_invalid_input(self):
    with pytest.raises(ValueError):
        my_function({})  # Missing required field
```

---

## Resources

### Documentation
- Pytest docs: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html

### Internal Resources
- Implemented examples: `tests/behavioral/generated/` (batches 1-4)
- Final report: `BEHAVIORAL_TEST_FINAL_REPORT.md`
- Status tracking: `BEHAVIORAL_TEST_STATUS.md`

### Getting Help
- Review implemented tests for patterns
- Ask in team chat
- Consult with batch 1-4 implementers

---

## Quick Commands

```bash
# Run specific test
pytest tests/behavioral/generated/test_pattern_library_behavioral.py::TestPatternLibrary::test_match -v

# Run with coverage
pytest tests/behavioral/generated/test_pattern_library_behavioral.py \
  --cov=src/attune/pattern_library \
  --cov-report=html \
  --cov-report=term-missing

# View coverage report
open htmlcov/index.html

# Run all behavioral tests
pytest tests/behavioral/ -v

# Run fast tests only
pytest tests/behavioral/ -v -m "not slow"

# Run with parallel execution (faster)
pytest tests/behavioral/ -n auto

# Debug failing test
pytest tests/behavioral/generated/test_pattern_library_behavioral.py::test_specific -vv --pdb
```

---

## Checklist Template

Copy this for each module you implement:

```markdown
## Test Implementation: [Module Name]

### Planning
- [ ] Read source code
- [ ] Identify public API
- [ ] List test scenarios
- [ ] Check for dependencies to mock

### Implementation
- [ ] Happy path tests
- [ ] Error path tests
- [ ] Edge case tests
- [ ] Async tests (if applicable)
- [ ] Mock external dependencies

### Validation
- [ ] All tests pass
- [ ] Coverage ≥85%
- [ ] Clear test names
- [ ] Good docstrings
- [ ] No skipped tests

### Cleanup
- [ ] Remove all `pass` statements
- [ ] Remove TODO comments
- [ ] Format code (black)
- [ ] Commit with message: "test: Implement behavioral tests for [module]"
```

---

**Last Updated:** 2026-01-29
**Maintained By:** Engineering Team
**Questions?** See BEHAVIORAL_TEST_FINAL_REPORT.md or ask in team chat
