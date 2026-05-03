---
name: critical-rules
source: .claude/CLAUDE.md
summary: This developer help template establishes non-negotiable security and code
  quality standards for the attune-ai codebase, including prohibitions on dangerous
  functions like `eval()` and `exec()`, requirements for file path validation and
  exception handling, mandatory type hints and docstrings, minimum test coverage thresholds,
  and guidelines for when to use XML-enhanced prompt formatting for complex multi-file
  changes.
tags:
- security
- rules
type: note
---

# Critical Rules

## Context

Non-negotiable security and quality rules for the attune-ai codebase.

## Rules

### Security

- **Never** use `eval()` or `exec()`
- **Always** validate file paths with `_validate_file_path()`
- **Never** use bare `except:` — catch specific exceptions
- **Always** log exceptions before handling them

### Code Quality

- Type hints and docstrings are required on all public APIs
- Minimum 80% test coverage must be maintained
- Security tests are required for all file operations

### Prompt Format

When creating a plan that involves 3 or more tasks, or touches 3 or more files, use the XML-enhanced prompt format (see `.claude/rules/attune/xml-enhanced-prompts.md`). For simpler work — single-file edits, config changes, or straightforward bug fixes — plain descriptions are fine.

---

## Related Topics

_No related topics yet._
