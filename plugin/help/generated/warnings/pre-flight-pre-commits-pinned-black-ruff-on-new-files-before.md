---
type: warning
name: pre-flight-pre-commits-pinned-black-ruff-on-new-files-before
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Warning: Pre-flight pre-commit's pinned black/ruff on new files
  before staging

## Condition

Running `.venv/bin/python -m black` or `uv run black` against a file doesn't guarantee pre-commit will leave it alone — pre-commit pins its own black/ruff versions that can format differently than whatever is in `.venv` (I saw py3.10 black leave a file "clean" while pre-commit's black reformatted triple-quoted-string argument layouts)

## Risk

Ignoring this guidance may cause: Pre-flight pre-commit's pinned black/ruff on new files
  before staging

## Mitigation

1. use the pinned tool directly — `uv run --with pre-commit pre-commit run black --files path/to/file.py` — before `git add`
2. Running `.venv/bin/python -m black` or `uv run black` against a file doesn't guarantee pre-commit will leave it alone — pre-commit pins its own black/ruff versions that can format differently than whatever is in `.venv` (I saw py3.10 black leave a file "clean" while pre-commit's black reformatted triple-quoted-string argument layouts)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-flight pre-commit's pinned black/ruff on new files
  before staging
