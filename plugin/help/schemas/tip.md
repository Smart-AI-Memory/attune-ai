---
type: tip
description: >
  Tip template schema for best practices, shortcuts,
  and efficiency patterns surfaced progressively based
  on usage and workflow context.
required_fields:
  - name
  - context
  - recommendation
  - why
optional_fields:
  - related_topics
  - tags
  - source
---

# Tip: {name}

## Context

{context}

When this tip is relevant. Describes the trigger
condition, usage threshold, or workflow state.

## Recommendation

{recommendation}

What to do. Should be concise and actionable.

## Why

{why}

The benefit or rationale for following this tip.

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Task: detailed procedure referenced by the tip
- Reference: API or config details for the action
- Warning: caution if the tip has edge cases
- Error: failure mode the tip helps avoid
