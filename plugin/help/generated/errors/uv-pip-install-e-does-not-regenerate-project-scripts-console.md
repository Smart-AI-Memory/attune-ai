---
type: error
name: uv-pip-install-e-does-not-regenerate-project-scripts-console
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: `uv pip install -e .` does not regenerate
  `[project.scripts]` console scripts

## Signature

`uv pip install -e .` does not regenerate
  `[project.scripts]` console scripts

## Root Cause

Editable reinstalls after adding or changing a `[project.scripts]` entry leave the old `.venv/bin/<name>` in place — or absent entirely if it's new. Symptom: `ls .venv/bin/<cli>` returns nothing despite a clean install log.

## Resolution

1. use `uv sync --extra dev --reinstall-package <pkg>` which rebuilds the wheel and refreshes entry_points

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv pip install -e .` does not regenerate
  `[project.scripts]` console scripts
