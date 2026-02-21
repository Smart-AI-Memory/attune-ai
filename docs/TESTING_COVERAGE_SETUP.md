---
description: Testing & Coverage Setup Guide: **Purpose:** Ensure test coverage measurement works correctly and doesn't break again.
---

# Testing & Coverage Setup Guide

**Purpose:** Ensure test coverage measurement works correctly and doesn't break again.

**Last Updated:** January 29, 2026
**Status:** ✅ VERIFIED WORKING

---

## Quick Start

```bash
# 1. Install in editable mode (REQUIRED)
pip uninstall attune-ai -y
rm -rf ~/.pyenv/versions/*/lib/python*/site-packages/attune  # Remove old remnants
pip install -e .

# 2. Verify editable install
python -c "import attune; print(attune.__file__)"
# Should print: /path/to/attune-ai/src/attune/__init__.py
# NOT site-packages!

# 3. Run tests with coverage (sequential, no parallel)
pytest --cov=src --cov-report=term --cov-report=html -n 0

# 4. View coverage report
open htmlcov/index.html
```

---

## Why Coverage Was Broken

### Problem 1: Package Not in Editable Mode

**Symptoms:**
- `pytest --cov=src` shows "No data to report"
- Tests pass but coverage is 0%

**Root cause:**
- Tests import from `/site-packages/attune` (installed package)
- Coverage measures `/local/src/attune` (local source)
- They're measuring different code!

**Fix:**
```bash
pip install -e .  # Install in editable mode
```

**Verify:**
```bash
python -c "import attune.config; print(attune.config.__file__)"
# GOOD: /path/to/attune-ai/src/attune/config/__init__.py
# BAD:  /path/to/site-packages/attune/config/__init__.py
```

---

### Problem 2: Leftover Package Remnants

**Symptoms:**
- Even after `pip install -e .`, imports fail
- `ImportError: cannot import name 'X' from 'attune' (unknown location)`
- `attune.__file__` is `None`

**Root cause:**
- Old `attune/` directory in site-packages wasn't removed
- Python creates namespace package, mixing old + new
- Lazy imports via `__getattr__` fail

**Fix:**
```bash
# Completely uninstall and clean
pip uninstall attune-ai -y
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/attune*

# Reinstall in editable mode
pip install -e .
```

---

### Problem 3: Parallel Execution Breaks Coverage

**Symptoms:**
- `pytest-xdist` workers crash with coverage errors
- "Data file doesn't seem to be a coverage data file"
- Coverage data corruption

**Root cause:**
- `pytest.ini` has `-n auto` (runs 12 parallel workers)
- pytest-xdist (parallel) + pytest-cov (coverage) conflict
- Each worker creates own coverage file, combining fails

**Fix:**
```bash
# For coverage runs, ALWAYS use -n 0 (sequential)
pytest --cov=src -n 0

# For fast test runs (no coverage), use parallel
pytest -n auto
```

---

## Proper Coverage Workflow

### Daily Development (Fast Tests)

```bash
# Run tests in parallel (fast, no coverage)
pytest -n auto
```

### Coverage Analysis (Slower, Complete)

```bash
# Run with coverage (sequential, complete)
pytest --cov=src --cov-report=html --cov-report=term -n 0

# View HTML report
open htmlcov/index.html
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-report=term -n 0

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

---

## Configuration Files

### `.coveragerc` (Coverage Settings)

```ini
[run]
source = src
parallel = false
concurrency = thread

[report]
precision = 2
show_missing = true
skip_covered = false
fail_under = 70

[html]
directory = htmlcov

[paths]
source =
    src/
    */site-packages/
```

### `pytest.ini` (Test Settings)

```ini
[pytest]
# Default: parallel execution (fast, no coverage)
addopts =
    --verbose
    --tb=short
    -n auto
    --dist=loadfile
    --maxfail=5

# For coverage runs, override with: pytest -n 0
```

---

## Coverage Targets

| Module Category | Target | Priority |
|-----------------|--------|----------|
| Core workflows (base.py) | 90%+ | P0 |
| Memory operations | 85%+ | P0 |
| Security functions | 90%+ | P0 |
| Config/CLI | 80%+ | P1 |
| Utilities/helpers | 70%+ | P2 |

---

## Writing Behavioral Tests (Not Just Structure Tests)

### ❌ BAD: Structure Tests (Don't Increase Coverage)

```python
def test_config_has_user_id_attribute():
    """Test that EmpathyConfig has user_id attribute."""
    assert hasattr(EmpathyConfig, 'user_id')  # Doesn't execute code!

def test_model_tier_enum_values():
    """Test enum values."""
    assert ModelTier.CHEAP.value == "cheap"  # Doesn't execute logic!
```

### ✅ GOOD: Behavioral Tests (Execute Code, Increase Coverage)

```python
def test_config_to_yaml_creates_valid_file(tmp_path):
    """Test that to_yaml() actually creates and writes a file."""
    config = EmpathyConfig(user_id="test")
    output = tmp_path / "config.yaml"

    # BEHAVIORAL: Actually call the method
    result = config.to_yaml(str(output))

    # Verify behavior
    assert output.exists()  # File was created
    content = output.read_text()
    assert "user_id: test" in content  # Content is correct

def test_validate_file_path_blocks_traversal():
    """Test that _validate_file_path() actually blocks attacks."""
    from attune.security.path_validation import _validate_file_path

    # BEHAVIORAL: Actually call with malicious input
    with pytest.raises(ValueError, match="system directory"):
        _validate_file_path("/etc/passwd")
```

**Key Differences:**
- Behavioral tests **CALL methods** and **verify outcomes**
- Structure tests only **check attributes exist**
- Behavioral tests increase coverage, structure tests don't

---

## Troubleshooting

### Issue: Coverage shows 0% but tests pass

**Diagnosis:**
```bash
python -c "import attune; print(attune.__file__)"
```

**If None or site-packages:**
```bash
pip uninstall attune-ai -y
rm -rf $(python -c "import site; print(site.getsitepackages()[0])")/attune*
pip install -e .
```

---

### Issue: "Data file doesn't seem to be a coverage data file"

**Cause:** Parallel execution conflict

**Fix:**
```bash
# Remove corrupted coverage data
rm -f .coverage*

# Run sequential
pytest --cov=src -n 0
```

---

### Issue: Tests import old code after changes

**Diagnosis:**
```bash
# Check what's being imported
python -c "from attune.config import EmpathyConfig; import inspect; print(inspect.getfile(EmpathyConfig))"
```

**Fix:** Reinstall in editable mode (see above)

---

## Pre-Commit Hook (Optional)

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Run coverage check before commit

pytest --cov=src --cov-report=term -n 0 --cov-fail-under=70 || {
    echo "❌ Coverage below 70%"
    exit 1
}
```

---

## Summary Checklist

Before running coverage:
- [ ] Package installed in editable mode (`pip install -e .`)
- [ ] Verified imports from local src/ (not site-packages)
- [ ] No old package remnants in site-packages
- [ ] Using `-n 0` (sequential execution)
- [ ] `.coveragerc` exists with correct settings

---

## Links

- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [pytest-xdist documentation](https://pytest-xdist.readthedocs.io/)

---

**Last Verified:** January 29, 2026
**Verified Coverage:** 1.72% (increasing with behavioral tests)
