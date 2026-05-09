---
type: error
name: uv-lock-retains-editable-name-paths-after-tool-uv-sources-edits
confidence: Verified
tags: [ci, git, claude-code, packaging]
source: .claude/CLAUDE.md
---

# Error: `uv.lock` retains `editable = "../name"` paths after
  `[tool.uv.sources]` edits — always re-run `uv lock`

## Signature

`uv.lock` retains `editable = "../name"` paths after
  `[tool.uv.sources]` edits — always re-run `uv lock`

## Root Cause

Deleting (or changing) a `[tool.uv.sources]` entry in `pyproject.toml` does NOT automatically refresh the lockfile. The lock keeps the old editable-sibling path, and any `uv sync` / `uv run` in CI (pre-commit hooks, fuzzing, etc.) fails with "Failed to generate package metadata for pkg==ver @ editable+../path" because the sibling directory doesn't exist in a CI checkout. Always re-run `uv lock` immediately after editing `[tool.uv.sources]` and commit `uv.lock` in the same change. Verify with `grep -A 2 "name = \"pkg\"" uv.lock` — the `source` line should read `{ registry = "https://pypi.org/simple" }` once the dep is published.

## Resolution

1. Always re-run `uv lock` immediately after editing `[tool.uv.sources]` and commit `uv.lock` in the same change

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv.lock` retains `editable = "../name"` paths after
  `[tool.uv.sources]` edits — always re-run `uv lock`
