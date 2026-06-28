---
name: refactor-plan
description: "Code-level refactoring analysis and roadmap. Detects duplication and complexity. Triggers on: refactor, tech debt, simplify, clean up, modularize, DRY, restructure."
argument-hint: "<path to analyze>"
---

# Refactor Planning

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="refactor-plan", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Refactor Plan** — Analyzes code structure and produces a prioritized refactoring roadmap.

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

**Prefer the rich panel.** If the tool response includes `panel_html`,
pass it to `mcp__visualize__show_widget` — the universal report panel
(title, score, findings/category sections; from
`attune.workflows.report_panel`). It shows an explicit "did not
complete" state on failure, never a false "clean". Fall back to the
markdown below when the widget surface is unavailable.

- Prioritized issue list
- Refactoring steps (ordered)
- Risk assessment per change
- Estimated effort
- Before/after examples
