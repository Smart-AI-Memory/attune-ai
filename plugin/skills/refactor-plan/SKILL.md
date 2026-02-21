---
name: refactor-plan
description: "Refactoring analysis. Triggers: 'refactor', 'code smell', 'clean up code', 'restructure', 'tech debt', 'improve code structure', 'simplify this', 'reduce complexity', 'modularize', 'extract method', 'DRY'."
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

## Analysis Areas

- **Code Smells**: Long methods, god classes, feature envy
- **Duplication**: Copy-paste detection, DRY violations
- **Complexity**: High cyclomatic complexity, deep nesting
- **Coupling**: Tight dependencies, circular imports
- **Naming**: Unclear or inconsistent naming

## Output

- Prioritized issue list
- Refactoring steps (ordered)
- Risk assessment per change
- Estimated effort
- Before/after examples
