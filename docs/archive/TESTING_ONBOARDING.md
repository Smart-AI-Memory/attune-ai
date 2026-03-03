---
description: Testing Onboarding Guide: ## Welcome to the Attune AI Test Suite **Audience**: New team members, contributors **Time to Complete**: 30-60 minutes **Prer
---

# Testing Onboarding Guide
## Welcome to the Attune AI Test Suite

**Audience**: New team members, contributors
**Time to Complete**: 30-60 minutes
**Prerequisites**: Python 3.10+, pytest installed

This guide will help you get up to speed with our testing approach and start contributing quality tests.

---

## Quick Start (5 minutes)

### Run All Tests

```bash
# From project root
cd /path/to/Empathy-framework

# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=src/attune --cov-report=term-missing
```

**Expected Results**:
```
============================= test session starts ==============================
collected 307 items

tests/unit/... PASSED                                                    [100%]

============================= 307 passed in 3.75s ===============================

---------- coverage: platform darwin, python 3.10.11-final-0 -----------
TOTAL                                                       18310  14407   5908    100  17.64%
```

### Run Specific Test Files

```bash
# Test workflows only
pytest tests/unit/workflows/ -v

# Test memory subsystem only
pytest tests/unit/memory/ -v

# Test models only
pytest tests/unit/models/ -v

# Test security features only
pytest tests/unit/memory/security/ -v
```

### Run Individual Test Classes

```bash
# Run specific test class
pytest tests/unit/memory/security/test_pii_scrubber.py::TestPIIDetection -v

# Run specific test function
pytest tests/unit/memory/security/test_pii_scrubber.py::TestPIIDetection::test_scrub_email_address -v
```

---

## Test Suite Structure (10 minutes)

### Directory Layout

```
tests/unit/
├── workflows/                    # Phase 1: Workflow helper functions
│   ├── test_bug_predict_helpers.py
│   ├── test_code_review_helpers.py
│   └── test_security_audit_helpers.py
├── memory/                       # Phase 2: Memory subsystem
│   ├── test_short_term.py       # Redis short-term memory
│   ├── test_long_term.py        # Persistent long-term memory
│   └── security/
│       └── test_pii_scrubber.py # Phase 3: Security
└── models/                       # Phase 4: Models & providers
    └── test_registry.py         # Model registry
```

### Test Organization by Phase

| Phase | Focus | Tests | Coverage Target |
|-------|-------|-------|-----------------|
| 1 | Workflow Helpers | 83 | Foundation patterns |
| 2 | Memory & State | 44 | State management |
| 3 | Security | 32 | PII detection |
| 4 | Models | 30 | Architecture |
| **Total** | **All** | **307** | **17.64%** |

---

## Understanding Our Testing Philosophy (10 minutes)

### 1. Educational Focus

Every test has a **"Teaching Pattern"** docstring:

```python
def test_scrub_email_address(self, scrubber):
    \"\"\"
    Teaching Pattern: Testing email scrubbing.

    Common PII type that must be detected and scrubbed.
    \"\"\"
    text = "Contact me at user@example.com for details"
    scrubbed, detections = scrubber.scrub(text)

    assert len(detections) >= 1
    assert "user@example.com" not in scrubbed or "[EMAIL]" in scrubbed
```

**Why?** Tests serve as documentation and learning material for the team.

### 2. Progressive Difficulty

Tests are organized from beginner to expert:

```
Beginner     → Phase 1 (Workflows)
Intermediate → Phase 2 (Memory)
Advanced     → Phase 3 (Security)
Expert       → Phase 4 (Models)
```

### 3. Real-World Scenarios

We test realistic use cases, not just happy paths:

```python
def test_multiple_pii_in_single_text(self, scrubber):
    \"\"\"Real-world text often contains multiple PII types.\"\"\"
    text = "Contact John at john@test.com or 555-1234, SSN: 123-45-6789"
    scrubbed, detections = scrubber.scrub(text)

    # Should detect email, phone, and SSN
    pii_types = {d.pii_type for d in detections}
    assert "email" in pii_types
```

---

## Writing Your First Test (15 minutes)

### Step 1: Choose a Pattern

See [TESTING_PATTERNS.md](./TESTING_PATTERNS.md) for 20+ reusable patterns.

**For beginners, start with**:
- Pattern #1: File I/O Mocking with tmp_path
- Pattern #2: Parametrized Pattern Matching
- Pattern #22: Fixture Reuse

### Step 2: Create a Test File

```python
\"\"\"
Educational Tests for [Feature Name]

Learning Objectives:
- [What developers will learn]
- [Key testing concepts demonstrated]
- [Patterns used]

Key Patterns:
- [Pattern type 1]
- [Pattern type 2]
\"\"\"

import pytest

@pytest.mark.unit
class Test[FeatureName]:
    \"\"\"Educational tests for [feature].\"\"\"

    @pytest.fixture
    def my_fixture(self):
        \"\"\"Fixture description.\"\"\"
        return MyClass()

    def test_basic_functionality(self, my_fixture):
        \"\"\"
        Teaching Pattern: [Pattern name].

        [Explanation of what this test teaches]
        \"\"\"
        # Arrange
        input_data = "test"

        # Act
        result = my_fixture.process(input_data)

        # Assert
        assert result == "expected"
```

### Step 3: Follow the AAA Pattern

**Arrange → Act → Assert**:

```python
def test_ttl_strategy_enum_values():
    \"\"\"Testing TTL strategy enum values.\"\"\"

    # Arrange (setup)
    # (None needed for enum test)

    # Act (execute)
    working_ttl = TTLStrategy.WORKING_RESULTS.value
    staged_ttl = TTLStrategy.STAGED_PATTERNS.value

    # Assert (verify)
    assert working_ttl == 3600      # 1 hour
    assert staged_ttl == 86400      # 24 hours
```

### Step 4: Add Teaching Documentation

```python
def test_my_feature(self):
    \"\"\"
    Teaching Pattern: [Pattern Name]

    [2-3 sentences explaining WHAT this tests and WHY it matters]

    Example: This tests that email addresses are correctly detected
    and scrubbed, which is critical for GDPR compliance.
    \"\"\"
    # ... test code ...
```

### Step 5: Run Your Test

```bash
# Run your new test
pytest tests/unit/path/to/test_file.py::TestClass::test_my_feature -v

# Verify it passes
# Add to coverage report
pytest tests/unit/ --cov=src/attune --cov-report=term-missing
```

---

## Common Testing Patterns (10 minutes)

### Pattern 1: Using tmp_path for File I/O

```python
def test_config_loading(tmp_path, monkeypatch):
    \"\"\"Test configuration file loading.\"\"\"
    # Create test file
    config_file = tmp_path / "config.yml"
    config_file.write_text("key: value")

    # Change to test directory
    monkeypatch.chdir(tmp_path)

    # Test
    config = load_config()
    assert config["key"] == "value"
```

### Pattern 2: Parametrized Testing

```python
@pytest.mark.parametrize("input,expected", [
    ("test@example.com", True),
    ("not-an-email", False),
    ("user+tag@domain.co.uk", True),
])
def test_email_validation(input, expected):
    \"\"\"Test email validation with multiple cases.\"\"\"
    result = is_valid_email(input)
    assert result == expected
```

### Pattern 3: Mocking External Services

```python
@patch('module.external_service')
def test_with_mock(mock_service):
    \"\"\"Test with mocked external dependency.\"\"\"
    # Setup mock
    mock_service.return_value = {"status": "success"}

    # Test
    result = my_function()

    # Verify
    assert result["status"] == "success"
    mock_service.assert_called_once()
```

### Pattern 4: Testing Exceptions

```python
def test_invalid_input_raises_error():
    \"\"\"Test that invalid input raises appropriate error.\"\"\"
    with pytest.raises(ValueError, match="Invalid input"):
        process_data(None)
```

---

## Test Quality Checklist (5 minutes)

Before committing your test, verify:

- [ ] **Clear docstring** with "Teaching Pattern" explanation
- [ ] **AAA pattern** (Arrange, Act, Assert) followed
- [ ] **Descriptive names** (`test_email_detection_with_multiple_formats` not `test_1`)
- [ ] **Isolated** (doesn't depend on other tests)
- [ ] **Fast** (< 1 second per test)
- [ ] **Deterministic** (same result every time)
- [ ] **Tests one thing** (focused, not testing multiple features)
- [ ] **Good assertions** (specific, not just `assert result`)

### Good vs Bad Examples

**❌ Bad**:
```python
def test_stuff():
    x = do_thing()
    assert x
```

**✅ Good**:
```python
def test_email_scrubbing_removes_pii_from_text(self, scrubber):
    \"\"\"
    Teaching Pattern: Testing PII scrubbing.

    Email addresses must be detected and replaced to comply with GDPR.
    \"\"\"
    # Arrange
    text_with_email = "Contact me at user@example.com"

    # Act
    scrubbed_text, detections = scrubber.scrub(text_with_email)

    # Assert
    assert "user@example.com" not in scrubbed_text
    assert "[EMAIL]" in scrubbed_text
    assert len(detections) == 1
    assert detections[0].pii_type == "email"
```

---

## Debugging Failed Tests (5 minutes)

### Use pytest's Verbose Mode

```bash
# See full error messages
pytest tests/unit/path/to/test.py -v

# See even more detail
pytest tests/unit/path/to/test.py -vv

# Show print statements
pytest tests/unit/path/to/test.py -s
```

### Use pytest's Debug Mode

```bash
# Drop into debugger on failure
pytest tests/unit/path/to/test.py --pdb

# Drop into debugger on errors (not failures)
pytest tests/unit/path/to/test.py --pdbcls=IPython.terminal.debugger:Pdb
```

### Add Debug Prints

```python
def test_something(self):
    result = complex_function()
    print(f"DEBUG: result = {result}")  # Will show with pytest -s
    assert result == expected
```

### Check Fixtures

```python
def test_something(self, my_fixture):
    print(f"DEBUG: fixture = {my_fixture}")  # Check fixture state
    assert my_fixture.is_valid()
```

---

## Coverage Goals (5 minutes)

### Current Coverage

```
Module                      Coverage    Status
-------------------------   ---------   ------
pii_scrubber.py             86.49%      ✅ Excellent
registry.py                 100.00%     ✅ Complete
short_term.py               25.21%      🟡 Good
long_term.py                16.55%      🟡 Baseline
bug_predict.py              36.24%      🟡 Good
code_review.py              25.17%      🟡 Good
security_audit.py           21.98%      🟡 Good
```

### What to Test First

**High Priority** (user-facing, security-critical):
1. Security features (PII, secrets detection)
2. User-facing APIs (workflows, executors)
3. Data integrity (memory, persistence)

**Medium Priority** (internal, but important):
1. Configuration loading
2. Error handling
3. Retry logic

**Low Priority** (nice to have):
1. Utility functions (fully covered by integration tests)
2. Logging (tested manually)
3. CLI commands (integration tested)

---

## Getting Help (2 minutes)

### Resources

1. **Pattern Library**: [TESTING_PATTERNS.md](./TESTING_PATTERNS.md) - 20+ copy-paste patterns
2. **Phase Completion Report**: `PHASE_3_4_COMPLETION.md` - Detailed examples
3. **pytest Documentation**: https://docs.pytest.org/
4. **Existing Tests**: Browse `tests/unit/` for examples

### Ask Questions

- **Slack**: #testing channel
- **Code Review**: Add `[testing-question]` label
- **Pair Programming**: Schedule with testing lead

### Common Questions

**Q: How do I test async code?**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected
```

**Q: How do I test private methods?**
A: Test public methods that call them. If you must test private methods directly, use `obj._private_method()`.

**Q: How do I skip a test temporarily?**
```python
@pytest.mark.skip(reason="Blocked by issue #123")
def test_something():
    pass
```

**Q: How do I mark tests as slow?**
```python
@pytest.mark.slow
def test_expensive_operation():
    pass

# Run non-slow tests: pytest -m "not slow"
```

---

## Next Steps

### Level Up Your Testing Skills

1. **Week 1**: Read [TESTING_PATTERNS.md](./TESTING_PATTERNS.md) and try Pattern #1, #2, #22
2. **Week 2**: Write 3-5 tests using parametrized testing
3. **Week 3**: Write tests for a security feature (PII, secrets)
4. **Week 4**: Write tests for a complex feature (state management, workflows)

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-tests`)
3. Write tests following this guide
4. Run full test suite (`pytest tests/unit/`)
5. Submit pull request with test coverage report

### Test Suite Roadmap

**Completed**:
- ✅ Phase 1: Workflow helpers (83 tests)
- ✅ Phase 2: Memory subsystem (44 tests)
- ✅ Phase 3: Security (32 tests)
- ✅ Phase 4: Models (30 tests)

**Next Steps** (Optional):
- 📋 Expand Phase 3 security tests (secrets detection, control panel)
- 📋 Expand Phase 4 model tests (provider config, workflow base)
- 📋 Phase 5: Documentation consolidation (tutorials, blog posts)

---

## Quick Reference

### Run Commands

```bash
# All tests
pytest tests/unit/

# With coverage
pytest tests/unit/ --cov=src/attune --cov-report=html

# Specific file
pytest tests/unit/memory/security/test_pii_scrubber.py

# Specific test
pytest tests/unit/memory/security/test_pii_scrubber.py::TestPIIDetection::test_scrub_email_address

# Failed tests only
pytest tests/unit/ --lf

# Verbose mode
pytest tests/unit/ -vv

# With debugger
pytest tests/unit/ --pdb
```

### Useful Markers

```python
@pytest.mark.unit          # Unit test (default)
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow test (skip in CI)
@pytest.mark.skip          # Skip test
@pytest.mark.parametrize   # Parametrized test
```

### Assertion Helpers

```python
assert x == y              # Equality
assert x != y              # Inequality
assert x in y              # Membership
assert x > y               # Comparison
assert callable(x)         # Type check
assert len(x) == 5         # Length
assert "text" in str(x)    # String contains

# Advanced
with pytest.raises(ValueError):
    function_that_raises()

with pytest.warns(UserWarning):
    function_that_warns()
```

---

## Success Metrics

You'll know you're successful when you can:

- ✅ Run the full test suite and understand the output
- ✅ Write a basic test with fixtures and assertions
- ✅ Use parametrized testing for multiple scenarios
- ✅ Mock external dependencies (files, Redis, APIs)
- ✅ Add coverage for a new feature
- ✅ Debug failing tests efficiently
- ✅ Follow the team's testing patterns and conventions

**Welcome to the team! Happy testing!** 🎉

---

**Last Updated**: 2026-01-04
**Maintainer**: Testing Team
**Questions?**: See "Getting Help" section above
