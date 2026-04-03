---
type: quickstart
name: task-code-migration
tags: [migration, python, upgrade, compatibility]
source: developer-guidance
---

# Quickstart: Upgrade Your Python Version

The fastest path from "I need to upgrade Python" to
"tests passing on the new version."

## 5 steps

**1. Check what needs to change**

Run pyupgrade in check-only mode to see how many files
are affected:

```
pyupgrade --py312-plus --check src/**/*.py
```

Or use ruff, which is faster:

```
ruff check --select UP src/
```

If nothing is flagged, your code may already be
compatible. Proceed to step 3 to verify.

**2. Apply automated fixes**

Let the tools handle the mechanical changes:

```
pyupgrade --py312-plus src/**/*.py
ruff check --select UP --fix src/
ruff check --select I --fix src/
```

Review the diff before committing. Codemods handle
syntax but not behavior changes.

**3. Run your tests on the new version**

Install the target Python and run your suite:

```
pyenv install 3.12.0
pyenv local 3.12.0
python -m venv .venv-312
source .venv-312/bin/activate
pip install -e '.[dev]'
pytest
```

If everything passes, skip to step 5.

**4. Fix what the tests caught**

Common fixes:

- `datetime.utcnow()` -- replace with
  `datetime.now(timezone.utc)`
- `ModuleNotFoundError` -- a stdlib module was removed,
  find the replacement
- `DeprecationWarning` now an error -- replace the
  deprecated API

Search for remaining deprecations:

```
pytest -W error::DeprecationWarning
```

**5. Update project metadata**

```toml
[project]
requires-python = ">=3.12"
```

Add the new version to your CI matrix. Remove the old
version if you no longer support it.

## What you just did

- Scanned your codebase for incompatibilities
- Applied automated syntax upgrades
- Verified with your test suite
- Updated your project's Python version constraint

## Next steps

- Say **"tell me more"** for the full migration guide --
  compatibility assessment, deprecation handling, and CI
  setup
- Say **"show me the migration reference"** for
  per-version change tables, codemod tools, and common
  pitfalls
- Say **"what are migration strategies?"** to learn about
  incremental vs big-bang approaches and risk assessment
- Ask **"/code-quality"** to review the migrated code for
  style issues
- Ask **"/smart-test"** to find any test gaps exposed by
  the upgrade

## Related Topics

- **Concept**: Code migration -- strategies, risk
  assessment, compatibility layers
- **Task**: Code migration -- full step-by-step version
  upgrade guide
- **Reference**: Code migration -- per-version checklists,
  codemods, and pitfall tables
