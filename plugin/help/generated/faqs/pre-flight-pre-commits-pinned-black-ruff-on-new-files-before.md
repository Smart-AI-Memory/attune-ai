---
type: faq
name: pre-flight-pre-commits-pinned-black-ruff-on-new-files-before
tags: [git, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about pre-flight pre-commit's pinned black/ruff on new files before staging?

## Answer

This catches format mismatches with the exact version pre-commit will enforce, avoiding the stash/restore dance on commit.

**How to fix:**
- Running `.venv/bin/python -m black` or `uv run black` against a file doesn't guarantee pre-commit will leave it alone — pre-commit pins its own black/ruff versions that can format differently than whatever is in `.venv` (I saw py3.10 black leave a file "clean" while pre-commit's black reformatted triple-quoted-string argument layouts)
- use the pinned tool directly — `uv run --with pre-commit pre-commit run black --files path/to/file.py` — before `git add`

```
.venv/bin/python -m black
```

## Related Topics
- **Error**: Detailed error: Pre-flight pre-commit's pinned black/ruff on new files
  before staging
