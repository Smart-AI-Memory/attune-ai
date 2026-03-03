# Testing Improvement Plan - Evening Session

**Created:** January 30, 2026
**Status:** Planned for evening implementation
**Priority:** Focus on testing quality, not new features

---

## 🎯 Goals

Enhance test coverage, quality, and maintainability for the refactored codebase without adding new features.

---

## ✅ Completed Today (Afternoon)

1. **Bug Fixes**
   - Fixed None handling in [report_formatter.py:115](../src/attune/workflows/document_gen/report_formatter.py#L115)
   - Fixed audience formatting (underscore → space conversion)
   - Result: All 50 batch12 tests passing (100%)

2. **Cleanup**
   - Removed 240+ broken test files
   - Cleared import conflicts
   - Result: Clean test discovery

3. **Test Generation**
   - Batch 11: 128 tests (test_gen) - 100% passing
   - Batch 12: 50 tests (document_gen) - 100% passing
   - Batch 13: 131 tests (cli_commands) - scaffolding created

**Current Status:** 1,393 tests passing (99.7% pass rate)

---

## 📋 Planned for Tonight

### Phase 1: Batch13 CLI Test Enhancement (1-2 hours)

**Goal:** Make batch13 CLI tests pass with proper mocking

#### 1.1 Create CLI Test Utilities

**File:** `tests/utils/cli_test_helpers.py`

```python
"""Test utilities for CLI command testing."""

from typing import Any, Callable
from unittest.mock import MagicMock, patch
import typer
from typer.testing import CliRunner


class MockTyperContext:
    """Mock Typer context for CLI tests."""

    def __init__(self, obj: dict | None = None):
        self.obj = obj or {}
        self.parent = None


def mock_cli_command(
    command_func: Callable,
    args: list[str] | None = None,
    mock_dependencies: dict[str, Any] | None = None
) -> tuple[Any, MockTyperContext]:
    """
    Mock a Typer CLI command for testing.

    Args:
        command_func: The command function to test
        args: Command line arguments
        mock_dependencies: Dependencies to mock (file ops, API calls, etc.)

    Returns:
        Tuple of (result, context)
    """
    runner = CliRunner()
    ctx = MockTyperContext()

    # Apply mocks if provided
    mocks = []
    if mock_dependencies:
        for target, mock_value in mock_dependencies.items():
            mocks.append(patch(target, mock_value))

    # Execute with all mocks active
    with patch.multiple('sys', argv=args or []):
        for mock in mocks:
            mock.start()

        try:
            result = command_func()
            return result, ctx
        finally:
            for mock in mocks:
                mock.stop()


def mock_file_operations():
    """Mock file operations for CLI tests."""
    return {
        'pathlib.Path.exists': MagicMock(return_value=True),
        'pathlib.Path.read_text': MagicMock(return_value="mock content"),
        'pathlib.Path.write_text': MagicMock(),
        'builtins.open': MagicMock(),
    }


def mock_workflow_execution():
    """Mock workflow execution for CLI tests."""
    return {
        'attune.workflows.base.BaseWorkflow.execute': MagicMock(
            return_value={"status": "success", "result": "mock result"}
        ),
    }
```

#### 1.2 Update Batch13 Tests Pattern

**Example for template_commands tests:**

```python
# Before (failing - no mocks)
def test_list_templates_command():
    result = list_templates()
    assert result is not None

# After (passing - with mocks)
from tests.utils.cli_test_helpers import mock_cli_command, mock_file_operations

def test_list_templates_command():
    result, ctx = mock_cli_command(
        list_templates,
        mock_dependencies=mock_file_operations()
    )
    assert result is not None
    assert "templates" in str(result).lower()
```

#### 1.3 Fix Tests by Category

| Module | Tests | Strategy |
|--------|-------|----------|
| template_commands | ~20 | Mock file system, template registry |
| workflow_commands | ~24 | Mock workflow execution, LLM calls |
| analytics_commands | ~22 | Mock database/storage, metrics |
| memory_commands | ~20 | Mock Redis, file session |
| config_commands | ~19 | Mock config files, migrations |
| agent_commands | ~26 | Mock agent creation, templates |

**Expected Outcome:** 70-80% of batch13 tests passing (90-105 tests)

---

### Phase 2: Test Coverage Analysis (30 min)

#### 2.1 Run Coverage Report

```bash
# Overall coverage
pytest --cov=src --cov-report=term-missing --cov-report=html

# Refactored modules specifically
pytest --cov=src/attune/workflows/test_gen \
       --cov=src/attune/workflows/document_gen \
       --cov=src/attune/meta_workflows/cli_commands \
       --cov-report=html
```

#### 2.2 Identify Coverage Gaps

**Focus areas:**
- Error handling paths
- Edge cases in refactored modules
- Integration between package modules
- Backward compatibility entry points

#### 2.3 Generate Additional Tests

Create targeted tests for uncovered code paths using the test generator:

```python
# For specific uncovered modules
from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

modules_to_cover = [
    {"file": "path/to/uncovered.py", "description": "..."}
]

gen = AutonomousTestGenerator(
    agent_id="coverage_boost",
    batch_num=14,
    modules=modules_to_cover
)
gen.generate_all()
```

---

### Phase 3: Test Quality Improvements (30 min)

#### 3.1 Add Test Documentation

**File:** `tests/README.md`

```markdown
# Test Suite Overview

## Structure
- `unit/` - Unit tests (isolated component testing)
- `behavioral/` - Behavioral tests (user-facing behavior)
- `integration/` - Integration tests (cross-component)
- `utils/` - Test utilities and helpers

## Running Tests
```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/behavioral/generated/batch11/

# With coverage
pytest --cov=src --cov-report=html
```

## Test Generation
See [scripts/generate_refactored_tests.py](../scripts/generate_refactored_tests.py)
```

#### 3.2 Add Pytest Markers

**File:** `pytest.ini` (update)

```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    behavioral: Behavioral tests (generated)
    integration: Integration tests (slower, cross-component)
    cli: CLI command tests (require mocking)
    slow: Slow tests (can be skipped for quick runs)
    refactored: Tests for refactored modules
```

**Usage:**
```bash
# Run only fast tests
pytest -m "unit and not slow"

# Run only refactored module tests
pytest -m refactored

# Skip CLI tests (if mocks aren't ready)
pytest -m "not cli"
```

#### 3.3 Add Test Fixtures for Common Patterns

**File:** `tests/conftest.py` (enhance)

```python
"""Shared pytest fixtures for all tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def mock_llm_response():
    """Mock LLM API response for testing."""
    def _mock_response(content: str = "mock response"):
        return {
            "content": content,
            "role": "assistant",
            "model": "claude-3-5-sonnet",
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }
    return _mock_response


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with common structure."""
    project = tmp_path / "project"
    project.mkdir()

    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "docs").mkdir()

    # Create sample files
    (project / "src" / "__init__.py").touch()
    (project / "README.md").write_text("# Test Project")

    return project


@pytest.fixture
def mock_workflow_config():
    """Mock workflow configuration."""
    return {
        "tier_routing": True,
        "max_tokens": 4000,
        "cache_enabled": True,
        "telemetry_enabled": False
    }
```

---

### Phase 4: Performance Testing (30 min - optional)

#### 4.1 Add Performance Benchmarks

**File:** `tests/performance/test_refactored_performance.py`

```python
"""Performance tests for refactored modules."""

import pytest
from attune.workflows.test_gen import TestGenerationWorkflow
from attune.workflows.document_gen import DocumentGenerationWorkflow


@pytest.mark.benchmark
class TestRefactoredModulePerformance:
    """Benchmark refactored modules vs original."""

    def test_test_gen_initialization_speed(self, benchmark):
        """Test TestGenerationWorkflow initialization speed."""
        def initialize():
            return TestGenerationWorkflow()

        result = benchmark(initialize)
        assert result is not None

    def test_document_gen_initialization_speed(self, benchmark):
        """Test DocumentGenerationWorkflow initialization speed."""
        def initialize():
            return DocumentGenerationWorkflow()

        result = benchmark(initialize)
        assert result is not None

    def test_cli_commands_registration_speed(self, benchmark):
        """Test CLI command registration speed."""
        def register():
            from attune.meta_workflows.cli_meta_workflows import meta_workflow_app
            return meta_workflow_app

        result = benchmark(register)
        assert len(result.registered_commands) == 16
```

**Run:**
```bash
pytest tests/performance/ --benchmark-only
```

---

## 📊 Success Metrics

**Target for Tonight:**

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Total Tests Passing | 1,393 | 1,470+ | 🎯 Target |
| Batch13 Pass Rate | 8% | 70-80% | 🎯 Target |
| Test Coverage | ~82% | 85%+ | 🎯 Target |
| Failing Tests | 5 | 2-3 | 🎯 Target |
| Test Execution Time | 22s | <25s | ✅ Good |

**Quality Goals:**
- ✅ All refactored modules have 100% passing tests
- ✅ CLI commands properly mocked and tested
- ✅ Test utilities available for future work
- ✅ Documentation updated

---

## 🚫 Explicitly NOT Doing Tonight

- **No new features** - Only testing improvements
- **No refactoring** - Focus on testing existing code
- **No architecture changes** - Keep current structure
- **No performance optimizations** - Test first, optimize later

---

## 📝 Implementation Order (Tonight)

1. **First 30 min:** Create CLI test utilities ([tests/utils/cli_test_helpers.py](../tests/utils/cli_test_helpers.py))
2. **Next 60 min:** Fix batch13 tests with mocking (aim for 70%+ passing)
3. **Next 30 min:** Run coverage analysis and identify gaps
4. **Next 30 min:** Add test documentation and pytest markers
5. **Final 15 min:** Run full test suite, commit all improvements

**Total Time:** ~2.5 hours
**Expected Outcome:** ~1,470 tests passing, 85%+ coverage, clean test suite

---

## 📌 Notes

- Focus on **testing quality**, not quantity
- Mock external dependencies properly
- Keep tests fast and reliable
- Document patterns for future contributors
- Commit frequently with clear messages

---

## 🔄 Next Steps After Tonight

**For tomorrow or next session:**
1. Generate tests for any remaining uncovered code
2. Consider refactoring [core.py](../src/attune/core.py) (1,511 lines) using mixin pattern
3. Add integration tests for full workflow pipelines
4. Set up CI/CD test automation

---

**Plan Status:** 🟡 Ready for Implementation
**Estimated Completion:** Tonight, 2.5 hours
**Owner:** Development Team
