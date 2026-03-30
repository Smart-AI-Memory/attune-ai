---
type: reference
description: >
  Reference template schema for factual, structured
  information about skills, tools, commands, and APIs.
  Supports three subtypes: procedural, tabular, freeform.
required_fields:
  - name
  - description
  - category
  - subtype
optional_fields:
  - sections
  - parameters
  - usage
  - related_topics
  - tags
  - source
---

# Reference: {name}

Reference templates have three subtypes, each with
a different structure suited to its content.

## Subtypes

### procedural

For skills and step-by-step guides. Structure:

1. Description — what this item does
2. Usage — invocation syntax
3. Sections — ordered body sections parsed from
   the source (e.g. Scoping, Execution, Output
   Format, Follow-Up)
4. Related Topics — cross-links

### tabular

For tools, APIs, and config options. Structure:

1. Description — what this item does
2. Parameters — table with name, type, description,
   and default
3. Usage — example invocation (optional)
4. Related Topics — cross-links

### freeform

For concepts, architecture docs, and mixed content.
Structure:

1. Description — overview
2. Sections — heading + body pairs (paragraphs,
   examples, diagrams)
3. Related Topics — cross-links

## Subtype Auto-Selection

| Source | Subtype |
| ------ | ------- |
| plugin/skills/*/SKILL.md | procedural |
| src/attune/mcp/tool_schemas.py | tabular |
| docs/**/*.md (future) | freeform |

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Task: how-to guide using this item
- Tip: best practices for effective use
- Warning: edge cases or limitations
- Error: known failure modes
