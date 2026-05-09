---
type: faq
name: uv-sync-wipes-packages-installed-via-pip-install
tags: [imports, packaging]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle uv sync wipes packages installed via pip install?

## Answer

The symptom is a confusing `No module named pip_audit` right after a successful install.

**How to fix:**
- Running `.venv/bin/python -m pip install pip-audit` into the venv looks successful, but a subsequent `uv sync --extra dev --extra developer` removes it because `uv sync` enforces the lockfile
- use `uv run --with pip-audit pip-audit --strict` for ephemeral audit tools, or add the tool to a dev extra in `pyproject.toml` so the lockfile keeps it

```
.venv/bin/python -m pip install pip-audit
```

## Related Topics
- **Error**: Detailed error: `uv sync` wipes packages installed via `pip install`
