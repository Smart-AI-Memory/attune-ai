---
type: concept
name: task-template-design-patterns
tags: [templates, design, help-system, authoring]
source: developer-guidance
---

# Concept: Template design patterns

## What

A template is the atomic unit of help content in
attune-help. Every template is a markdown file with YAML
frontmatter (type, name, tags, source) and a structured
body. The frontmatter tells the engine what the template
is; the body tells the user what they need to know.

There are 11 template types, each serving a distinct
purpose. Choosing the right type determines what sections
the body contains, where the file lives on disk, and how
the engine renders it at different depth levels.

## Why

Structured templates solve three problems that freeform
documentation creates:

1. **Generation.** The engine can compose, filter, and
   cross-link templates because it knows their shape.
   Freeform docs require human curation to connect.
2. **Progressive depth.** Each type defines compact,
   normal, and detailed views. The engine serves the right
   level without the author writing three versions.
3. **Consistency.** Users learn the shape once. A concept
   always starts with "What" and "Why." A quickstart
   always has numbered steps. Predictable structure
   reduces cognitive load.

## The 11 template types

| Type | Prefix | Directory | Purpose | When to use | Example |
|---|---|---|---|---|---|
| **concept** | `con-` | `concepts/` | Explain an idea -- what, why, how | User asks "what is X?" or needs mental model before doing | `con-task-error-handling-design` |
| **task** | `tas-` | `tasks/` | Step-by-step procedure | User asks "how do I do X?" and needs a walkthrough | `tas-task-code-migration` |
| **reference** | `ref-` | `references/` | Complete lookup table | User knows what they want and needs exact syntax or values | `ref-task-authentication-patterns` |
| **quickstart** | `qui-` | `quickstarts/` | Minimal path to working result | User wants to start immediately with least reading | `qui-task-git-workflow` |
| **error** | `err-` | `errors/` | Explain a specific error and fix | User hit an error message and needs resolution | `err-shadow-dirs` |
| **warning** | `wrn-` | `warnings/` | Preventive guidance | User is about to hit a known pitfall | `wrn-pre-commit-stash` |
| **tip** | `tip-` | `tips/` | Short actionable suggestion | User could benefit from a workflow nudge | `tip-after-code-review` |
| **faq** | `faq-` | `faqs/` | Question-answer pair | User asks a common question | `faq-eval-in-tests` |
| **troubleshooting** | `tro-` | `troubleshooting/` | Diagnosis flow for symptoms | User describes a symptom, not an error message | `tro-mcp-server-not-responding` |
| **comparison** | `com-` | `comparisons/` | Side-by-side evaluation | User needs to choose between alternatives | `com-workflow-vs-wizard` |
| **note** | `not-` | `notes/` | Project decision or context | User needs background on a design choice | `not-decision-d1-template-schemas` |

## Anatomy of a template

Every template has two parts:

**1. YAML frontmatter** -- metadata the engine reads:

```yaml
---
type: concept
name: task-template-design-patterns
tags: [templates, design, help-system, authoring]
source: developer-guidance
---
```

- `type` -- one of the 11 types above
- `name` -- the slug used in cross-links and lookups
- `tags` -- list of searchable tags (lowercase, hyphenated)
- `source` -- where the content originated (a source file
  path or `developer-guidance` for hand-written content)

**2. Markdown body** -- what the user sees. Each type has
its own section conventions:

| Type | Required sections |
|---|---|
| concept | What, Why, (one or more detail sections) |
| task | Prerequisites, Steps (numbered), Verification |
| reference | Lookup tables, code blocks, field lists |
| quickstart | Numbered steps (3-7), What you just did |
| error | Symptom, Cause, Fix |
| warning | What happens, Why, Prevention |
| tip | One actionable paragraph |
| faq | Question as heading, answer as body |
| troubleshooting | Symptoms, Diagnosis steps, Resolution |
| comparison | Criteria table, recommendation |
| note | Context, Decision, Rationale |

## The four-template pattern

For developer-facing task categories (like "error handling
design" or "code migration"), create all four core types
as a set:

1. **Concept** -- the mental model (task-error-handling-design)
2. **Task** -- the step-by-step procedure
3. **Reference** -- the complete lookup
4. **Quickstart** -- the fastest path

These four share the same `name` value in frontmatter.
The cross-link builder connects them automatically
because their slugs differ only by prefix (`con-`, `tas-`,
`ref-`, `qui-`).

## Want to learn more?

- Say **"how do I write a template?"** for the step-by-step
  authoring guide -- from blank file to rendered output
- Say **"show me all frontmatter fields"** for the
  complete reference -- every field, every type, every
  naming convention
- Say **"I need to create a template now"** for the
  5-step quickstart
- Say **"what is progressive depth?"** to understand how
  templates adapt verbosity on repeated access
- Say **"how does cross-linking work?"** to see how
  templates discover and reference each other

## Related Topics

- **Task**: Template design patterns -- step-by-step
  guide for writing a template from scratch
- **Reference**: Template design patterns -- all fields,
  types, sections, naming conventions, and quality
  checklist
- **Quickstart**: Template design patterns -- 5-step
  guide from blank file to working template
- **Concept**: Progressive depth -- how templates adapt
  verbosity based on repeated access
- **Concept**: Cross-linking -- how templates discover
  and reference each other
