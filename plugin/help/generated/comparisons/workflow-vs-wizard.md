---
type: comparison
name: workflow-vs-wizard
tags: [workflow, architecture]
source: .claude/CLAUDE.md
---

# Comparison: Workflow vs Wizard

Understanding the difference between non-interactive workflows and guided wizards.

| Feature | Workflow | Wizard |
| ------- | ------- | ------- |
| Interaction | Non-interactive | Guided step-by-step |
| Input | CLI flags or JSON | Interactive questions |
| Output | Structured JSON/report | Conversation with follow-ups |
| Invocation | `attune workflow run <name>` | `/wizard run <name>` |
| Count | 17 built-in | 5 built-in |
| Customization | Python subclass | YAML or Python |
| CI/CD friendly | Yes | No (needs interaction) |
| Best for | Automated analysis | Complex decision-making |

## Recommendation

Use **workflows** for CI/CD pipelines and automated analysis. Use **wizards** when the task needs human judgment at each step (debugging, release prep).

## Related Topics

_No related topics yet._
