---
type: note
name: critical-rules
tags: [security, rules]
source: .claude/CLAUDE.md
---

# Note: Critical Rules

## Context

Non-negotiable security and quality rules for the attune-ai codebase.

## Content

- NEVER use eval() or exec()
- ALWAYS validate file paths with _validate_file_path()
- NEVER use bare except: - catch specific exceptions
- ALWAYS log exceptions before handling
- Type hints and docstrings required on all public APIs
- Minimum 80% test coverage
- Security tests required for file operations
- When creating a detailed plan with 3+ tasks or touching
  3+ files, use XML-enhanced prompt format (see
  `.claude/rules/attune/xml-enhanced-prompts.md`). For
  simpler work (single-file edits, config changes, bug
  fixes), plain descriptions are fine.

---

## Related Topics

_No related topics yet._
