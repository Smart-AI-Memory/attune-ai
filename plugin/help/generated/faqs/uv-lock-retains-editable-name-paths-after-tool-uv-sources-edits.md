---
type: faq
name: uv-lock-retains-editable-name-paths-after-tool-uv-sources-edits
tags: [ci, git, claude-code, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about uv.lock retains editable = "../name" paths after [tool.uv.sources] edits — always re-run uv lock?

## Answer

Deleting (or changing) a `[tool.uv.sources]` entry in `pyproject.toml` does NOT automatically refresh the lockfile. The lock keeps the old editable-sibling path, and any `uv sync` / `uv run` in CI (pre-commit hooks, fuzzing, etc.) fails with "Failed to generate package metadata for pkg==ver @ editable+../path" because the sibling directory doesn't exist in a CI checkout.

**How to fix:**
- Always re-run `uv lock` immediately after editing `[tool.uv.sources]` and commit `uv.lock` in the same change

```
[tool.uv.sources]
```

## Related Topics
- **Error**: Detailed error: `uv.lock` retains `editable = "../name"` paths after
  `[tool.uv.sources]` edits — always re-run `uv lock`
