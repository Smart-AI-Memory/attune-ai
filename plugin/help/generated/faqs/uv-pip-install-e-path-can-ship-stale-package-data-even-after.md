---
type: faq
name: uv-pip-install-e-path-can-ship-stale-package-data-even-after
tags: [packaging, python]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle uv pip install -e <path> can ship stale package-data even after --force-reinstall --no-cache?

## Answer

added `src/attune_help/templates/summaries_by_path.json` and expected editable-installed attune-help to see it. It didn't — the file appeared in a freshly built wheel but not via the editable install.

**How to fix:**
- Use these when iterating on a package's shipped data files — editable install's caching is unreliable for non-Python content

```
src/attune_help/templates/summaries_by_path.json
```

## Related Topics
- **Error**: Detailed error: `uv pip install -e <path>` can ship stale
  package-data even after `--force-reinstall
  --no-cache`
