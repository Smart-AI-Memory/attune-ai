---
type: warning
name: uv-pip-install-e-path-can-ship-stale-package-data-even-after
confidence: Verified
tags: [packaging, python]
source: .claude/CLAUDE.md
---

# Warning: `uv pip install -e <path>` can ship stale
  package-data even after `--force-reinstall
  --no-cache`

## Condition

added `src/attune_help/templates/summaries_by_path.json` and expected editable-installed attune-help to see it

## Risk

Wasted ~20 min debugging

## Mitigation

1. Use these when iterating on a package's shipped data files — editable install's caching is unreliable for non-Python content

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `uv pip install -e <path>` can ship stale
  package-data even after `--force-reinstall
  --no-cache`
