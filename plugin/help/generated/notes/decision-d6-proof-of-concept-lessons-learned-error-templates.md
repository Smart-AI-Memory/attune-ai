---
type: note
name: decision-d6-proof-of-concept-lessons-learned-error-templates
tags: [architecture, design-decision]
source: .claude/plans/documentation-stack-spec.md
---

# Note: Design decision: Proof of concept: Lessons Learned -> Error templates

## Context

Documentation stack architecture decision.

## Content

**Status: DONE** (2026-03-29)

Built and validated. The pipeline:

```text
CLAUDE.md Lessons Learned (140 entries)
  -> parse_lessons_learned() extracts title + body
  -> lesson_to_template() populates ErrorTemplate
  -> Jinja2 renders via error.md.jinja2
  -> Output to plugin/help/generated/errors/
  -> --check mode verifies sync state
```

**Results:** 140 entries -> 140 Error templates, 0
failures. All templates have frontmatter (type, name,
confidence, tags, source), structured sections
(Signature, Root Cause, Resolution, Related Topics),
and auto-classified tags.

**Files created:**

- `plugin/help/schemas/error.md` — schema definition
- `plugin/help/templates/error.md.jinja2` — Jinja2
  render template
- `scripts/generate_error_templates.py` — generator
  (follows sync paradigm: discover, parse, transform,
  validate, output, verify)
- `plugin/help/generated/errors/*.md` — 140 generated
  Error templates

**Libraries used:**

- `jinja2` — template rendering (already in codebase,
  now declared in pyproject.toml)
- `python-frontmatter` — YAML frontmatter parsing
  (new dependency, for future schema reading)

**Key design choices:**

- Sentence splitting respects backtick-quoted code
  (e.g. `Path.read_text()` not split at the dot)
- Tag classification uses keyword matching across 10
  categories (ci, testing, security, imports, git,
  windows, macos, claude-code, packaging, python)
- Signature extraction prefers backtick-quoted error
  names (e.g. `ModuleNotFoundError`) over title text
- Resolution extraction finds Fix: markers and
  imperative sentences (Always, Never, Use, etc.)
- Related Topics auto-generated from content analysis
  (Warning for "avoid/never", Tip for "always/prefer")

## Related Topics

_No related topics yet._
