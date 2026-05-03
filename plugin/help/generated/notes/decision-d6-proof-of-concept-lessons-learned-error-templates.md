---
name: decision-d6-proof-of-concept-lessons-learned-error-templates
source: .claude/plans/documentation-stack-spec.md
summary: This developer help template documents a proof-of-concept system that automatically
  generates standardized error documentation templates from structured lessons learned
  entries using a pipeline that parses, transforms, and validates them through Jinja2
  rendering.
tags:
- architecture
- design-decision
type: note
---

# Design Decision: Lessons Learned → Error Templates

## Context

Documentation stack architecture decision.

**Status: Done** (2026-03-29)

---

## Summary

A proof-of-concept pipeline that automatically converts structured lessons learned entries into standardized error template files was built and validated.

## Pipeline

```text
CLAUDE.md Lessons Learned (140 entries)
  -> parse_lessons_learned()  — extracts title + body
  -> lesson_to_template()     — populates ErrorTemplate
  -> Jinja2                   — renders via error.md.jinja2
  -> Output                   — plugin/help/generated/errors/
  -> --check mode             — verifies sync state
```

**Result:** 140 entries → 140 error templates, 0 failures.

All generated templates include:

- **Frontmatter:** `type`, `name`, `confidence`, `tags`, `source`
- **Structured sections:** Signature, Root Cause, Resolution, Related Topics
- **Auto-classified tags**

---

## Files Created

| File | Description |
|---|---|
| `plugin/help/schemas/error.md` | Schema definition |
| `plugin/help/templates/error.md.jinja2` | Jinja2 render template |
| `scripts/generate_error_templates.py` | Generator script (discover → parse → transform → validate → output → verify) |
| `plugin/help/generated/errors/*.md` | 140 generated error templates |

---

## Dependencies

| Library | Purpose | Notes |
|---|---|---|
| `jinja2` | Template rendering | Already in codebase; now declared in `pyproject.toml` |
| `python-frontmatter` | YAML frontmatter parsing | New dependency; added for future schema reading |

---

## Key Design Choices

**Sentence splitting**
Respects backtick-quoted code spans — for example, `` `Path.read_text()` `` is not split at the dot.

**Tag classification**
Keyword matching across 10 categories: `ci`, `testing`, `security`, `imports`, `git`, `windows`, `macos`, `claude-code`, `packaging`, `python`.

**Signature extraction**
Prefers backtick-quoted error names (e.g., `` `ModuleNotFoundError` ``) over raw title text.

**Resolution extraction**
Finds `Fix:` markers and imperative sentences beginning with `Always`, `Never`, `Use`, etc.

**Related Topics generation**
Derived from content analysis: `Warning` nodes for "avoid/never" language; `Tip` nodes for "always/prefer" language.

---

## Related Topics

_None yet._
