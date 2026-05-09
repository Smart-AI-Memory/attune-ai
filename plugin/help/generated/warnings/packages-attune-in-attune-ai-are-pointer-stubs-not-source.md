---
type: warning
name: packages-attune-in-attune-ai-are-pointer-stubs-not-source
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Warning: `packages/attune-*/` in attune-ai are pointer stubs, not
  source

## Condition

`packages/attune-author/` and `packages/attune-help/` contain a single README.md that points at the real sibling repo (`/Users/patrickroebuck/attune-{author,help}/`)

## Risk

Ignoring this guidance may cause: `packages/attune-*/` in attune-ai are pointer stubs, not
  source

## Mitigation

1. `packages/attune-author/` and `packages/attune-help/` contain a single README.md that points at the real sibling repo (`/Users/patrickroebuck/attune-{author,help}/`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `packages/attune-*/` in attune-ai are pointer stubs, not
  source
