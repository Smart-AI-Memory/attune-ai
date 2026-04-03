---
type: concept
name: task-cross-linking-strategy
tags: [cross-linking, navigation, help-system, authoring]
source: developer-guidance
---

# Concept: Cross-linking strategy

## What

Cross-linking is the practice of connecting templates so
users flow naturally between related content. A template
without cross-links is a dead end -- the user reads it,
gets partial understanding, and has no path forward. A
cross-linked template is a node in a knowledge graph that
responds to natural language navigation like "tell me
more", "what is X?", and "show me an example".

## Why

Templates in isolation answer one question. Cross-linked
templates answer follow-up questions before the user has
to ask. When a user reads an error template about path
traversal, they should be one sentence away from the
warning that prevents it, the FAQ that explains why it
happens, and the tip that shows the fix. Without
cross-links, the user must know the exact template name
to find related content. With cross-links, the help
system surfaces related content automatically.

The difference matters most for discovery. Users who
arrive at one template via search or error message rarely
know the full landscape of related content. Cross-links
turn a single answer into a learning path.

## The 7 deterministic link rules

Attune uses 7 rules to derive cross-links automatically
from template metadata. Every rule is deterministic --
no fuzzy matching, no AI inference, no manual curation.

| # | Rule | Direction | How it matches | Purpose |
|---|---|---|---|---|
| 1 | Error to Warning | Bidirectional | Same slug name | Pairs the "what went wrong" with "how to prevent it" |
| 2 | Skill to Tool | Skill -> Tool | Tool name appears in skill body | Connects the workflow instruction to the underlying MCP tool |
| 3 | Error to Tip | Error -> Tip | 2+ non-stopword title tokens overlap | Surfaces prevention advice alongside failure documentation |
| 4 | Task to Reference | Bidirectional | Skill task `use-X` matches reference `skill-X` | Links the "how to do it" to the "full specification" |
| 5 | FAQ to Error | Bidirectional | Same slug name | Connects the question format to the technical diagnosis |
| 6 | Note to Reference | Note -> Reference | 2+ non-stopword title tokens overlap | Links design decisions to the patterns they produced |
| 7 | Tag-based | Implicit | Shared tags across all template types | Groups templates by topic for search and discovery |

Rules 1, 4, and 5 use exact slug matching -- they are
precise and produce zero false positives. Rules 3 and 6
use token overlap -- they cast a wider net and
occasionally produce weak links that the tag index helps
filter. Rule 2 reads the actual skill file body to find
tool references. Rule 7 is the catch-all that ensures
every template is discoverable by topic even when no
structural link exists.

## The navigation pattern

Cross-links surface through the "Want to learn more?"
section at the bottom of every template. This section
uses natural language prompts instead of raw markdown
links.

**Why natural language wins over markdown links:**

| Approach | Example | User experience |
|---|---|---|
| Markdown link | `[API endpoint reference](ref-task-api-endpoint-design.md)` | User must parse the link text and guess what they will find |
| Natural language | "Show me all the status codes and patterns" -- see the **reference** template | User reads a question they might actually ask, then sees where the answer lives |

Natural language prompts work with the help system's
intent detection. When a user says "show me all the
status codes", the system can match that phrase to the
cross-link and route directly to the reference. Markdown
links are opaque to intent detection.

## The knowledge graph in practice

When all 7 rules run across the full template set, the
result is a connected graph stored in `cross_links.json`.
Each node has typed edges (related_warning,
references_tools, prevented_by, related_reference,
related_error, related_faq) and tag memberships for
implicit connections.

A user navigating this graph might follow this path:

1. Search "path traversal" -- tag index returns 6
   templates across errors, warnings, tips, and FAQs
2. Read the error template -- cross-link to the matching
   warning shows how to prevent it
3. Follow the warning -- cross-link to the tip shows the
   `_validate_file_path()` pattern
4. Ask "tell me more" -- tag-based discovery surfaces
   the reference template with the full validation API

Each hop answers a natural follow-up question. The user
never needs to know template IDs or file paths.

## Want to learn more?

- "How do I add cross-links to my own templates?" -- see
  the **task** template for a step-by-step guide
- "Show me all the link rules and the JSON structure" --
  see the **reference** template for the complete
  specification
- "I just need to connect my templates quickly" -- see
  the **quickstart** for a 5-step guide

## Related Topics

- **Task**: Cross-linking strategy -- step-by-step guide
  to adding cross-links to new and existing templates
- **Reference**: Cross-linking strategy -- all 7 link
  rules, cross_links.json structure, tag naming
  conventions, and the rebuild script
- **Quickstart**: Cross-linking strategy -- 5-step guide
  to connecting templates
