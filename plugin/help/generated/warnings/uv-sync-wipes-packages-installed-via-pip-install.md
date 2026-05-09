---
type: warning
name: uv-sync-wipes-packages-installed-via-pip-install
confidence: Verified
tags: [imports, packaging]
source: .claude/CLAUDE.md
---

# Warning: `uv sync` wipes packages installed via `pip install`

## Condition

Running `.venv/bin/python -m pip install pip-audit` into the venv looks successful, but a subsequent `uv sync --extra dev --extra developer` removes it because `uv sync` enforces the lockfile

## Risk

Ignoring this guidance may cause: `uv sync` wipes packages installed via `pip install`

## Mitigation

1. use `uv run --with pip-audit pip-audit --strict` for ephemeral audit tools, or add the tool to a dev extra in `pyproject.toml` so the lockfile keeps it
2. Running `.venv/bin/python -m pip install pip-audit` into the venv looks successful, but a subsequent `uv sync --extra dev --extra developer` removes it because `uv sync` enforces the lockfile

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `uv sync` wipes packages installed via `pip install`
