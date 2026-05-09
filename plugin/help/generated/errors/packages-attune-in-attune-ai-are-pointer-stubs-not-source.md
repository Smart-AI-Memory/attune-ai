---
type: error
name: packages-attune-in-attune-ai-are-pointer-stubs-not-source
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Error: `packages/attune-*/` in attune-ai are pointer stubs, not
  source

## Signature

`packages/attune-*/` in attune-ai are pointer stubs, not
  source

## Root Cause

`packages/attune-author/` and `packages/attune-help/` contain a single README.md that points at the real sibling repo (`/Users/patrickroebuck/attune-{author,help}/`). The actual package source, `pyproject.toml`, tests, and CI live in those sibling directories. `[tool.uv.sources]` in attune-ai uses `path = "../attune-{name}", editable = true` to resolve them during dev. Any new sibling package (e.g. attune-rag) must follow the same layout: full source in `../attune-<name>/`, pointer stub at `packages/attune-<name>/README.md`, and a `[tool.uv.sources]` entry.

## Resolution

1. `packages/attune-author/` and `packages/attune-help/` contain a single README.md that points at the real sibling repo (`/Users/patrickroebuck/attune-{author,help}/`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `packages/attune-*/` in attune-ai are pointer stubs, not
  source
- Task: Update test mocks and assertions
