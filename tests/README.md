# Test Suite Documentation

**Attune AI Test Suite**
**Last Updated:** January 30, 2026
**Test Count:** 1,382+ tests
**Coverage:** ~82%

---

## 📁 Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── workflows/          # Workflow module tests
│   ├── models/             # Model and provider tests
│   ├── memory/             # Memory system tests
│   ├── meta_workflows/     # Meta-orchestration tests
│   └── telemetry/          # Telemetry and tracking tests
├── behavioral/             # Behavioral tests (user-facing)
│   ├── generated/          # Auto-generated behavioral tests
│   │   ├── batch11/       # test_gen module tests (128 tests)
│   │   ├── batch12/       # document_gen module tests (50 tests)
│   │   └── batch13/       # cli_commands module tests (131 tests)
│   └── *.py               # Handwritten behavioral tests
├── integration/            # Integration tests (cross-component)
│   └── test_*.py           # incl. auth-gated real-API tests (nightly job)
├── utils/                  # Test utilities and helpers
│   ├── cli_test_helpers.py # CLI mocking utilities
│   └── __init__.py
└── conftest.py            # Shared pytest fixtures
```

---

## 🚀 Running Tests

### Quick Commands

```bash
# Run all tests
pytest

# Run specific category
pytest tests/unit/
pytest tests/behavioral/
pytest tests/integration/

# Run specific refactored module tests
pytest tests/behavioral/generated/batch11/  # test_gen
pytest tests/behavioral/generated/batch12/  # document_gen
pytest tests/behavioral/generated/batch13/  # cli_commands

# Run with coverage
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"

# Run only refactored module tests
pytest -m refactored

# Run tests in parallel (faster)
pytest -n auto
```

---

## 🔧 Test Utilities

Located in `tests/utils/cli_test_helpers.py` - provides mocking utilities for CLI commands.

See [docs/TESTING_IMPROVEMENT_PLAN.md](../docs/TESTING_IMPROVEMENT_PLAN.md) for detailed usage.

---

**More documentation:** [TESTING_IMPROVEMENT_PLAN.md](../docs/TESTING_IMPROVEMENT_PLAN.md)
