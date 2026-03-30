---
type: note
name: decision-d1-template-schemas-live-in-the-repo
tags: [architecture, design-decision]
source: .claude/plans/documentation-stack-spec.md
---

# Note: Design decision: Template schemas live in the repo

## Context

Documentation stack architecture decision.

## Content

Template schemas (the *structure*, not populated
content) are defined as files in `plugin/help/schemas/`:

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

Each schema file uses YAML frontmatter for metadata
(type, required fields, optional fields) and markdown
body for the structural template. The AI engine reads
these schemas and fills them with content from code
analysis.

This mirrors how `plugin/skills/*/SKILL.md` defines
skill structure — schemas are the documentation
equivalent.

## Related Topics

_No related topics yet._
