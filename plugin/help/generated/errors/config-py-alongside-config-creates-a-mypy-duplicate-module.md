---
type: error
name: config-py-alongside-config-creates-a-mypy-duplicate-module
confidence: Verified
tags: [imports, git, python]
source: .claude/CLAUDE.md
---

# Error: `config.py` alongside `config/` creates a mypy duplicate
  module

## Signature

`config.py` alongside `config/` creates a mypy duplicate
  module

## Root Cause

Having both `src/attune/config.py` and `src/attune/config/__init__.py` causes mypy to report "Duplicate module named attune.config". This blocks mypy in pre-commit. Either rename one or exclude the module from mypy. We removed mypy from pre-commit entirely for now.

## Resolution

1. Having both `src/attune/config.py` and `src/attune/config/__init__.py` causes mypy to report "Duplicate module named attune.config"

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `config.py` alongside `config/` creates a mypy duplicate
  module
