---
name: decision-d1-template-schemas-live-in-the-repo
source: .claude/plans/documentation-stack-spec.md
summary: This template covers the decision to store template schemas—which define
  the structure of different help document types (task, reference, FAQ, warning, error,
  tip, note)—as versioned files in the repository under `plugin/help/schemas/`, where
  each schema combines YAML metadata with a Markdown template that an AI engine uses
  to generate populated documentation.
tags:
- architecture
- design-decision
type: note
---

# Design Decision: Template Schemas Live in the Repository

## Context

Documentation stack architecture decision.

## Summary

Template schemas — defining *structure*, not populated content — are stored as files under `plugin/help/schemas/`:

```text
plugin/help/schemas/
  task.md
  reference.md
  faq.md
  warning.md
  error.md
  tip.md
  note.md
```

Each schema file consists of two parts:

- **YAML frontmatter** — declares metadata such as document type, required fields, and optional fields.
- **Markdown body** — provides the structural template that content will populate.

The AI engine reads these schemas and uses them as scaffolding, filling each template with content derived from code analysis.

## Rationale

This approach mirrors the convention used by `plugin/skills/*/SKILL.md`, where each file defines the structure of a skill. Template schemas serve as the direct documentation equivalent: a single source of truth for how each help document type should be shaped.

Keeping schemas in the repository means they are versioned, reviewable, and editable alongside the code they document.

## Related Topics

_No related topics yet._
