---
type: troubleshooting
name: import-error-attune
tags: [imports, python, setup]
source: CLAUDE.md Lessons Learned
---

# Troubleshooting: ModuleNotFoundError for attune submodules

## Symptom

`ModuleNotFoundError: No module named 'attune.workflows'` or similar.

## Diagnosis

1. Check for a shadow `attune/` directory at the repo root: `ls -d attune/ 2>/dev/null`
2. Verify installation: `pip show attune-ai`
3. Check Python path: `python -c 'import attune; print(attune.__file__)'`

## Fix

Remove any `attune/` directory at the repo root that shadows the installed package. Reinstall: `pip install -e .`

## Prevention

Never create prototype directories matching the package name at the repo root.

## Related Topics
- **Error**: Shadow directories at repo root break imports
