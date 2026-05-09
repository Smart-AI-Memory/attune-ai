---
type: warning
name: uv-lock-retains-editable-name-paths-after-tool-uv-sources-edits
confidence: Verified
tags: [ci, git, claude-code, packaging]
source: .claude/CLAUDE.md
---

# Warning: `uv.lock` retains `editable = "../name"` paths after
  `[tool.uv.sources]` edits — always re-run `uv lock`

## Condition

Deleting (or changing) a `[tool.uv.sources]` entry in `pyproject.toml` does NOT automatically refresh the lockfile

## Risk

The lock keeps the old editable-sibling path, and any `uv sync` / `uv run` in CI (pre-commit hooks, fuzzing, etc.) fails with "Failed to generate package metadata for pkg==ver @ editable+../path" because the sibling directory doesn't exist in a CI checkout

## Mitigation

1. Always re-run `uv lock` immediately after editing `[tool.uv.sources]` and commit `uv.lock` in the same change

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `uv.lock` retains `editable = "../name"` paths after
  `[tool.uv.sources]` edits — always re-run `uv lock`
