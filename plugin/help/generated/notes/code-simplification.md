---
name: code-simplification
source: .claude/CLAUDE.md
summary: This template guides developers to simplify code by eliminating unnecessary
  abstractions, deep nesting, and over-engineering in favor of clarity and straightforward
  solutions.
tags:
- philosophy
- code-quality
type: note
---

# Note: Code Simplification

## Context

Engineering philosophy: simpler is better. Three clear lines beat one clever abstraction.

## Content

After writing or modifying code, review it for unnecessary complexity. Claude tends to over-engineer — introducing too many abstractions, unnecessary classes, premature optimizations, and overly configurable interfaces. Counteract this tendency by:

- Flattening deeply nested conditionals using early returns
- Inlining trivial helper functions that are only called once
- Removing dead code paths and unused parameters
- Preferring standard library solutions over custom abstractions
- Collapsing class hierarchies where a plain function suffices

When in doubt, choose the simpler approach. Three clear lines beat one clever abstraction.

---

## Related Topics

*No related topics yet.*
