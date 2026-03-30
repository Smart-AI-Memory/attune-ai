---
type: note
name: code-simplification
tags: [philosophy, code-quality]
source: .claude/CLAUDE.md
---

# Note: Code Simplification

## Context

Engineering philosophy: simpler is better. Three clear lines beat one clever abstraction.

## Content

After writing or modifying code, review it for unnecessary
complexity. Claude tends to over-engineer — too many
abstractions, unnecessary classes, premature optimization,
over-configurable interfaces. Counteract this by:

- Flattening deeply nested conditionals (use early returns)
- Inlining trivial helper functions used only once
- Removing dead code paths and unused parameters
- Preferring stdlib over custom abstractions
- Reducing class hierarchies when a function suffices

Simpler is better. Three clear lines beat one clever
abstraction.

---

## Related Topics

_No related topics yet._
