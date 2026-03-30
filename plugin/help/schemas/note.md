---
type: note
description: >
  Note template schema for supplementary information
  that enriches understanding but isn't actionable
  on its own — design decisions, architecture context,
  historical rationale.
required_fields:
  - name
  - context
  - content
optional_fields:
  - related_topics
  - tags
  - source
---

# Note: {name}

## Context

{context}

What this note relates to — the feature, decision,
or system it documents.

## Content

{content}

The information itself — may include paragraphs,
lists, or diagrams.

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Reference: the feature this note describes
- Task: procedure affected by this note
- Warning: caution related to this context
