---
type: faq
name: pytest-lives-in-the-dev-extra-not-developer
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about pytest lives in the dev extra, not developer?

## Answer

The `developer` extra in `pyproject.toml` does NOT include pytest — that's in the separate `dev` extra. Symptom: `.venv/bin/python -m pytest` exits with `No module named pytest` after `uv sync --extra developer`.

**How to fix:**
- sync both with `uv sync --extra dev --extra developer`

```
 extra in
```

## Related Topics
- **Error**: Detailed error: `pytest` lives in the `dev` extra, not `developer`
