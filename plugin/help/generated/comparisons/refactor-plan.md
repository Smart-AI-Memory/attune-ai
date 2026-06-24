---
name: refactor-plan
source: content/features/refactor-plan.md
tags:
- refactor
- tech-debt
- complexity
type: comparison
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

## Comparison

Refactor-plan and **code-quality** are both SDK-native, predictive,
read-only analysis workflows reached with `attune workflow run
<slug>` — but they answer different questions.

| | `refactor-plan` | `code-quality` |
|---|---|---|
| **Question** | What tech debt should I tackle, and in what order? | Is this code healthy across security, quality, performance, architecture? |
| **Subagents** | Three: `debt-scanner`, `impact-analyzer`, `plan-generator` | Four: `security-`, `quality-`, `perf-`, `architect-reviewer` |
| **Output** | A prioritized roadmap with effort + risk per item | A health report with findings per domain |
| **Sections** | Summary / Refactoring / Suggestions | Summary / Security / Quality / Performance / Architecture / Suggestions |
| **Slug** | `attune workflow run refactor-plan` | `attune workflow run code-review` |

Reach for **refactor-plan** when you've decided to invest in
cleanup and need a sequenced plan; reach for **code-quality** for a
broad health read across more concerns. To actually *apply* a
cleanup once the plan names it, use **simplify-code**.
