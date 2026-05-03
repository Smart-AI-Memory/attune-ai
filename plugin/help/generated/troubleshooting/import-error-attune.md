---
name: import-error-attune
source: CLAUDE.md Lessons Learned
summary: This template provides troubleshooting guidance for resolving `ModuleNotFoundError`
  exceptions when importing `attune` submodules, covering diagnosis steps to identify
  when a local directory shadows the installed package, fixes to remove the conflicting
  directory and reinstall the package, and prevention strategies to avoid the issue
  in the future.
tags:
- imports
- python
- setup
type: troubleshooting
---

# Troubleshooting: `ModuleNotFoundError` for `attune` Submodules

## Symptom

You see an error similar to:

```
ModuleNotFoundError: No module named 'attune.workflows'
```

This typically occurs when a local directory shadows the installed package.

## Diagnosis

Run the following checks in order to identify the root cause.

**1. Check for a shadowing directory at the repo root:**

```bash
ls -d attune/ 2>/dev/null
```

If this returns a result, a local `attune/` directory is overriding the installed package.

**2. Verify the package is installed:**

```bash
pip show attune-ai
```

Confirm that `attune-ai` appears in the output with the expected version.

**3. Check which `attune` module Python is importing:**

```python
python -c "import attune; print(attune.__file__)"
```

If the path points to a local directory rather than your virtual environment's `site-packages`, the local directory is the source of the problem.

## Fix

1. Remove the shadowing directory:

   ```bash
   rm -rf attune/
   ```

2. Reinstall the package:

   ```bash
   pip install -e .
   ```

3. Re-run the diagnostic in step 3 above and confirm the path now points to `site-packages`.

## Prevention

Never create local directories whose names match an installed package. Even an empty `attune/` directory at the repo root will take precedence over the installed `attune-ai` package, silently breaking submodule imports.

## Related Topics

- [Python import system: the module search path](https://docs.python.org/3/reference/import.html#the-module-search-path)
- **Common mistake:** Shadow directories at the repo root that break imports
