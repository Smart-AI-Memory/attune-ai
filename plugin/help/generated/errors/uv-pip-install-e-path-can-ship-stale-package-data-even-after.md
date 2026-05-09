---
type: error
name: uv-pip-install-e-path-can-ship-stale-package-data-even-after
confidence: Verified
tags: [packaging, python]
source: .claude/CLAUDE.md
---

# Error: `uv pip install -e <path>` can ship stale
  package-data even after `--force-reinstall
  --no-cache`

## Signature

`uv pip install -e <path>` can ship stale
  package-data even after `--force-reinstall
  --no-cache`

## Root Cause

added `src/attune_help/templates/summaries_by_path.json` and expected editable-installed attune-help to see it. It didn't — the file appeared in a freshly built wheel but not via the editable install. Wasted ~20 min debugging. Workarounds that work: (1) `uv sync` refreshes the whole venv from the lockfile, (2) build a wheel with `python -m build --wheel` and install it directly, (3) delete the `site-packages/<pkg>` dir manually before reinstalling. Use these when iterating on a package's shipped data files — editable install's caching is unreliable for non-Python content.

## Resolution

1. Use these when iterating on a package's shipped data files — editable install's caching is unreliable for non-Python content

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv pip install -e <path>` can ship stale
  package-data even after `--force-reinstall
  --no-cache`
