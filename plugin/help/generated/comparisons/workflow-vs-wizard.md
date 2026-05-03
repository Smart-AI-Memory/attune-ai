---
name: workflow-vs-wizard
source: .claude/CLAUDE.md
summary: This template explains the key differences between workflows and wizards,
  helping developers decide which tool to use based on whether their task requires
  automation or interactive guidance.
tags:
- workflow
- architecture
type: comparison
---

# Comparison: Workflow vs. Wizard

Understanding the difference between non-interactive workflows and guided wizards helps you choose the right tool for each task.

| Feature | Workflow | Wizard |
|---|---|---|
| Interaction | Non-interactive | Guided, step-by-step |
| Input | CLI flags or JSON | Interactive prompts |
| Output | Structured JSON or report | Conversational, with follow-ups |
| Invocation | `attune workflow run <name>` | `/wizard run <name>` |
| Built-in count | 17 | 5 |
| Customization | Python subclass | YAML or Python |
| CI/CD compatible | Yes | No — requires user interaction |
| Best for | Automated analysis | Complex, judgment-driven decisions |

## When to Use Each

**Choose workflows** when you need repeatable, automated execution — for example, in CI/CD pipelines, scheduled analysis jobs, or any context where no human interaction is available.

**Choose wizards** when the task requires human judgment at each step, such as debugging a complex issue or preparing a release.

## Related Topics

_No related topics yet._
