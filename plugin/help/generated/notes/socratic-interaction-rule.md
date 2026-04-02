---
type: note
name: socratic-interaction-rule
tags: [philosophy, ux]
source: .claude/CLAUDE.md
---

# Note: Socratic Interaction Rule

## Context

Core UX principle: always guide users with questions before executing actions.

## Content

**ALWAYS use `AskUserQuestion` to guide users through workflow discovery and scoping. NEVER skip straight to execution.**

This is the core design principle of Attune AI's developer experience. When a user invokes `/attune` or any workflow:

1. **Initial discovery**: Use `AskUserQuestion` to understand their goal (what are you trying to accomplish?)
2. **Scoping**: Use `AskUserQuestion` to narrow scope (which files? what test subset? what level of detail?)
3. **Confirmation**: Use `AskUserQuestion` if there are meaningful choices before execution (approach, format, targets)
4. **Then execute**: Only run CLI commands or tools after the user has been guided through the relevant decisions

**Examples of when to ask:**

- User says "run tests" → Ask: which tests? full suite, CLI only, or quick smoke test?
- User says "security audit" → Ask: which path? src/, tests/, or full project?
- User says "review code" → Ask: which files or area? what focus (security, quality, performance)?
- User says "commit" → Ask: which files to stage? what kind of change is this?

**Do NOT:**

- Jump straight to running commands without scoping
- Assume the user wants the broadest possible execution
- Skip questions just because the next step seems obvious

This rule applies to ALL workflow interactions, not just `/attune`.

---

## Related Topics

_No related topics yet._
