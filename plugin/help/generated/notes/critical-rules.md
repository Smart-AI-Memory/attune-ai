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
- Minimum 85% test coverage
- Security tests required for file operations
- Choose the artifact tier through the shared contract's Artifact selection
  section. XML-task eligibility and format requirements are canonical in
  `.claude/rules/attune/xml-enhanced-prompts.md`; do not restate them here.

---

## Related Topics

_No related topics yet._
