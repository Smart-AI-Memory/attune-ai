---
name: refactor-plan
description: "Code-level refactoring analysis and roadmap generation. Detects code smells, duplication, complexity, coupling, and naming issues. For high-level feature or architecture planning, use the planning skill instead. Triggers on: refactor, restructure, code smell, clean up, tech debt, simplify, reduce complexity, modularize, extract method, DRY."
argument-hint: "<path to analyze>"
---

# Refactor Planning

AI-powered refactoring analysis and roadmap generation.

## Quick Start

```bash
attune workflow run refactor-plan --path ./src
```

## Usage

### Via Script

```bash
python scripts/run.py --path ./src/legacy_module.py
```

### Via Python

```python
from attune.workflows import RefactorPlanWorkflow

workflow = RefactorPlanWorkflow()
result = await workflow.execute(target_path="./src")
print(result.plan)
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
