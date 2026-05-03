---
name: skill-refactor-plan
source: plugin/skills/refactor-plan/SKILL.md
summary: The `/refactor-plan` command analyzes code files or directories to generate
  a structured refactoring analysis with prioritized recommendations and actionable
  next steps.
tags:
- skill
- claude-code
type: quickstart
---

# Quickstart: /refactor-plan

Generate a code-level refactoring analysis and actionable roadmap for any file or directory.

## Usage

```
/refactor-plan <path>
```

## What It Does

Analyzes the target path and returns a structured refactoring plan — including identified issues, prioritized recommendations, and suggested next steps — directly in your Claude Code conversation.

## Example

```
/refactor-plan src/utils/auth.ts
```

## Next Steps

For complete options and advanced usage, run:

```
attune help-docs ref-skill-refactor-plan
```

## Related Topics

*No related topics yet.*
