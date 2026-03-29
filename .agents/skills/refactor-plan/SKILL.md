---
name: refactor-plan
description: "Code-level refactoring analysis and roadmap. Detects smells, duplication, complexity. Triggers on: refactor, tech debt, simplify, code smell, clean up, modularize, DRY."
argument-hint: "<path to analyze>"
---

# Refactor Planning

AI-powered refactoring analysis and roadmap generation.

## Scoping

Before running, ask:

1. **Target**: "Which file or directory needs
   refactoring analysis?"
2. **Focus**: "Full analysis or specific concern?"
   - Full: `refactor_plan` (all areas)
   - Simplify: `simplify_code` (reduce complexity only)
3. **Depth**: "Quick scan or detailed roadmap?"

## Execution

Based on scope:

- Full analysis: `refactor_plan(path="<target>")`
- Simplify only: `simplify_code(path="<target>")`

Or via CLI:

```bash
attune workflow run refactor-plan --path <target>
```

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `refactor_plan` | Tech debt analysis and refactoring roadmap |
| `simplify_code` | Reduce complexity in specific files |

### refactor_plan

Full refactoring analysis for a path.

```
refactor_plan(path="<target>")
```

### simplify_code

Targeted complexity reduction for a single file or
module. Flattens nested conditionals, inlines trivial
helpers, removes dead code.

```
simplify_code(path="<target file>")
```

## Analysis Areas

- **Code Smells**: Long methods, god classes, feature
  envy
- **Duplication**: Copy-paste detection, DRY violations
- **Complexity**: High cyclomatic complexity, deep
  nesting
- **Coupling**: Tight dependencies, circular imports
- **Naming**: Unclear or inconsistent naming

## Output

- Prioritized issue list
- Refactoring steps (ordered)
- Risk assessment per change
- Estimated effort
- Before/after examples
