---
type: task
name: task-code-migration
tags: [migration, python, upgrade, compatibility]
source: developer-guidance
---

# How to Migrate Your Python Version

A step-by-step guide to upgrading from one Python version
to another. This applies to any minor version jump (3.9 to
3.10, 3.10 to 3.11, etc.) and scales to major transitions.

## Prerequisites

- A working test suite (the higher the coverage, the
  safer the migration)
- Access to install the target Python version locally
- CI that runs tests on the current version

## Steps

### 1. Assess your starting point

Before changing anything, understand what you're working
with:

```
python --version
pip list --format=columns | wc -l
pytest --co -q | tail -1
```

Record your current Python version, number of installed
packages, and number of tests. These are your baseline.

Check your `pyproject.toml` or `setup.cfg` for the
declared Python version constraint:

```toml
[project]
requires-python = ">=3.9"
```

### 2. Check compatibility

Run `pyupgrade` in check-only mode to see what needs to
change:

```
pip install pyupgrade
pyupgrade --py310-plus --check src/**/*.py
```

Review deprecation warnings in your current test suite:

```
pytest -W default::DeprecationWarning 2>&1 | grep -i deprecat
```

Check each dependency for compatibility with the target
version:

| What to check | How | Red flag |
|---|---|---|
| Your dependencies | `pip install --dry-run -e '.'` on new Python | Install failures |
| C extensions | Look for `*.so`/`*.pyd` in your deps | Binary packages without target-version wheels |
| Removed stdlib modules | Check "Removed" in the What's New doc | `import cgi`, `import imp`, etc. |
| Changed defaults | Check "Changed" in the What's New doc | `datetime.utcnow()` deprecation, etc. |

### 3. Set up the target environment

Install the new Python version alongside the current one.
Do not replace it yet:

```
# With pyenv
pyenv install 3.12.0
pyenv local 3.12.0

# Verify
python --version
```

Create a fresh virtual environment:

```
python -m venv .venv-312
source .venv-312/bin/activate
pip install -e '.[dev]'
```

### 4. Run your test suite on the new version

```
pytest
```

Categorize any failures:

| Failure type | Action | Urgency |
|---|---|---|
| `SyntaxError` | Fix syntax incompatibility | Must fix before proceeding |
| `DeprecationWarning` now an error | Replace deprecated API | Must fix |
| `ModuleNotFoundError` | Removed stdlib module -- find replacement | Must fix |
| Behavioral change (test logic correct) | Update code to new behavior | Must fix |
| Behavioral change (test assertion wrong) | Update the test | Fix alongside code |
| Dependency not yet compatible | Check for newer version or alternative | May block migration |

### 5. Apply codemods for mechanical changes

Use automated tools to handle the repetitive parts:

```
# Upgrade syntax to target version
pyupgrade --py312-plus src/**/*.py

# Fix import sorting (may change with new stdlib)
ruff check --select I --fix src/

# Auto-fix deprecated patterns
ruff check --select UP --fix src/
```

Review the changes before committing. Codemods handle
syntax but not semantics -- they won't catch a behavior
change in `datetime.fromisoformat()`.

### 6. Handle deprecations explicitly

For each deprecation warning:

1. Read the deprecation message -- it tells you what to
   use instead
2. Find all occurrences: `grep -r "deprecated_function" src/`
3. Replace with the recommended alternative
4. Test the replacement

Common deprecation patterns:

```python
# Before (deprecated in 3.12)
from datetime import datetime
now = datetime.utcnow()

# After
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

```python
# Before (removed in 3.12)
import imp
imp.reload(module)

# After
import importlib
importlib.reload(module)
```

### 7. Update CI to test both versions

Add the new version to your CI matrix while keeping the
old one:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.12"]
```

Run both until the migration is complete and all tests
pass on the new version.

### 8. Update project metadata

Once all tests pass on the new version:

```toml
[project]
requires-python = ">=3.12"
```

Update classifiers:

```toml
classifiers = [
    "Programming Language :: Python :: 3.12",
]
```

Remove the old version from your CI matrix if you no
longer support it.

### 9. Clean up compatibility layers

Remove any shims, `try`/`except ImportError` blocks, or
`sys.version_info` checks that were only needed for the
old version. These are dead code now.

Search for them:

```
grep -r "sys.version_info" src/
grep -r "except ImportError" src/ | grep -v "optional"
```

## Verification

After completing the migration:

- [ ] All tests pass on the new Python version
- [ ] No deprecation warnings from your own code
- [ ] `pyproject.toml` reflects the new minimum version
- [ ] CI runs on the new version
- [ ] Compatibility shims for the old version are removed
- [ ] Dependencies all support the new version

## What to do next

| Goal | What to say |
|---|---|
| Review migrated code quality | "run a code review" |
| Check test coverage | "find test gaps" |
| Plan a framework migration | "help me plan a refactor" |
| Scan for deprecated patterns | "run code quality check" |

## Want to learn more?

- Say **"what are migration strategies?"** for the concept
  overview -- incremental vs big-bang, risk assessment,
  and compatibility layers
- Say **"show me the migration reference"** for per-version
  checklists, codemod tools, and common pitfalls
- Say **"I need to upgrade Python"** for the 5-minute
  quickstart
- Ask **"/code-quality"** to scan for deprecated patterns
  and style issues after migrating
- Ask **"/smart-test"** to verify test coverage on the
  migrated code
