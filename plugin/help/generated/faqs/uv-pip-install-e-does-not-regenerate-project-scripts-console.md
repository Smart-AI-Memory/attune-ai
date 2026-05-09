---
type: faq
name: uv-pip-install-e-does-not-regenerate-project-scripts-console
tags: [packaging]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle uv pip install -e . does not regenerate [project.scripts] console scripts?

## Answer

Editable reinstalls after adding or changing a `[project.scripts]` entry leave the old `.venv/bin/<name>` in place — or absent entirely if it's new. Symptom: `ls .venv/bin/<cli>` returns nothing despite a clean install log.

**How to fix:**
- use `uv sync --extra dev --reinstall-package <pkg>` which rebuilds the wheel and refreshes entry_points

```
[project.scripts]
```

## Related Topics
- **Error**: Detailed error: `uv pip install -e .` does not regenerate
  `[project.scripts]` console scripts
