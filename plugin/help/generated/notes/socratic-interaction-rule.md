---
name: socratic-interaction-rule
source: .claude/CLAUDE.md
summary: This template establishes a Socratic interaction rule requiring developers
  to use guided questioning via `AskUserQuestion` to understand user intent and scope
  before executing any actions, rather than jumping directly to command execution.
tags:
- philosophy
- ux
type: note
---

# Socratic Interaction Rule

## Context

Core UX principle: always guide users with questions before executing actions.

## Content

**ALWAYS use `AskUserQuestion` to guide users through workflow discovery and scoping. NEVER skip straight to execution.**

This is the core design principle of Attune AI's developer experience. When a user invokes `/attune` or any workflow, follow this sequence:

1. **Initial discovery** — Use `AskUserQuestion` to understand their goal. *What are you trying to accomplish?*
2. **Scoping** — Use `AskUserQuestion` to narrow scope. *Which files? What test subset? What level of detail?*
3. **Confirmation** — Use `AskUserQuestion` before any meaningful decision point. *Which approach, format, or targets?*
4. **Execution** — Only run CLI commands or invoke tools after the user has been guided through the relevant decisions.

### When to Ask

| User says… | Ask… |
|---|---|
| "run tests" | Which tests — full suite, CLI only, or a quick smoke test? |
| "security audit" | Which path — `src/`, `tests/`, or the full project? |
| "review code" | Which files or area, and what's the focus — security, quality, or performance? |
| "commit" | Which files to stage, and what kind of change is this? |

### What NOT to Do

- Jump straight to running commands without scoping
- Assume the user wants the broadest possible execution
- Skip questions because the next step seems obvious

> **This rule applies to all workflow interactions, not just `/attune`.**

---

## Related Topics

*No related topics yet.*
