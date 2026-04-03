---
type: reference
name: task-template-design-patterns
tags: [templates, design, help-system, authoring]
source: developer-guidance
---

# Reference: Template design patterns

Complete reference for authoring attune-help templates.
Covers every frontmatter field, all 11 template types
with their required sections, naming conventions, file
organization, cross-linking rules, and a quality
checklist.

## Frontmatter fields

Every template starts with a YAML frontmatter block
delimited by `---`:

| Field | Required | Type | Values | Notes |
|---|---|---|---|---|
| `type` | Yes | string | `concept`, `task`, `reference`, `quickstart`, `error`, `warning`, `tip`, `faq`, `troubleshooting`, `comparison`, `note` | Must match the directory the file lives in |
| `name` | Yes | string | Lowercase slug with hyphens | Becomes template ID when combined with type prefix |
| `tags` | Yes | list | 2-6 lowercase hyphenated strings | Used for search, filtering, and cross-link discovery |
| `source` | Yes | string | File path or `developer-guidance` | Origin of the content; `developer-guidance` for hand-authored templates |

Example:

```yaml
---
type: reference
name: task-template-design-patterns
tags: [templates, design, help-system, authoring]
source: developer-guidance
---
```

## Template types and required sections

### concept

| Section | Required | Purpose |
|---|---|---|
| `# Concept: Name` | Yes | Level-1 heading with type prefix |
| `## What` | Yes | One-paragraph definition |
| `## Why` | Yes | Why this matters to the user |
| Detail sections | Yes (1+) | Tables, principles, examples -- varies by topic |
| `## Want to learn more?` | Yes | Natural language prompts to sibling templates |
| `## Related Topics` | Yes | Explicit cross-links by type |

### task

| Section | Required | Purpose |
|---|---|---|
| `# How to Action Phrase` | Yes | Level-1 heading describing the procedure |
| Intro paragraph | Yes | What this guide covers |
| `## Prerequisites` | Yes | What the user needs before starting |
| `## Steps` | Yes | Numbered sub-sections (`### 1. Title`) |
| `## Verification` | Yes | Checklist of success criteria |
| `## What to do next` | Recommended | Table of follow-up actions |
| `## Want to learn more?` | Yes | Natural language prompts |
| `## Related Topics` | Yes | Cross-links by type |

### reference

| Section | Required | Purpose |
|---|---|---|
| `# Reference: Name` | Yes | Level-1 heading with type prefix |
| Intro paragraph | Yes | Scope of this reference |
| Lookup sections | Yes (1+) | Tables, field lists, code blocks |
| `## Want to learn more?` | Yes | Natural language prompts |
| `## Related Topics` | Yes | Cross-links by type |

### quickstart

| Section | Required | Purpose |
|---|---|---|
| `# Quickstart: Action Phrase` | Yes | Level-1 heading with type prefix |
| Intro line | Yes | One sentence stating the goal |
| `## N steps` | Yes | The step count as a heading |
| Numbered steps | Yes | Bold step titles, 3-7 steps |
| `## What you just did` | Yes | Summary of what was accomplished |
| `## Next steps` | Recommended | Natural language prompts |
| `## Related Topics` | Yes | Cross-links by type |

### error

| Section | Required | Purpose |
|---|---|---|
| `# Error: Short description` | Yes | Level-1 heading |
| `## Symptom` | Yes | What the user sees |
| `## Cause` | Yes | Why this happens |
| `## Fix` | Yes | Step-by-step resolution |
| `## Prevention` | Recommended | How to avoid recurrence |
| `## Related Topics` | Yes | Cross-links |

### warning

| Section | Required | Purpose |
|---|---|---|
| `# Warning: Short description` | Yes | Level-1 heading |
| `## What happens` | Yes | Consequence of the pitfall |
| `## Why` | Yes | Root cause |
| `## Prevention` | Yes | How to avoid it |
| `## Related Topics` | Yes | Cross-links |

### tip

| Section | Required | Purpose |
|---|---|---|
| `# Tip: Short description` | Yes | Level-1 heading |
| Body paragraph | Yes | One actionable paragraph |
| `## Related Topics` | Recommended | Cross-links |

### faq

| Section | Required | Purpose |
|---|---|---|
| `# Question as heading` | Yes | The question itself |
| Answer body | Yes | Direct answer |
| `## Related Topics` | Recommended | Cross-links |

### troubleshooting

| Section | Required | Purpose |
|---|---|---|
| `# Troubleshooting: Symptom` | Yes | Level-1 heading |
| `## Symptoms` | Yes | What the user observes |
| `## Diagnosis` | Yes | Steps to narrow the cause |
| `## Resolution` | Yes | Fix for each diagnosed cause |
| `## Related Topics` | Yes | Cross-links |

### comparison

| Section | Required | Purpose |
|---|---|---|
| `# Comparison: X vs Y` | Yes | Level-1 heading |
| Criteria table | Yes | Side-by-side evaluation |
| `## Recommendation` | Recommended | When to choose each |
| `## Related Topics` | Yes | Cross-links |

### note

| Section | Required | Purpose |
|---|---|---|
| `# Note: Title` | Yes | Level-1 heading |
| `## Context` | Yes | Background information |
| `## Decision` | Yes | What was decided |
| `## Rationale` | Yes | Why this decision was made |
| `## Related Topics` | Recommended | Cross-links |

## Naming conventions

### File naming

Files are named by their `name` frontmatter field with
a `.md` extension:

| Template category | Filename pattern | Example |
|---|---|---|
| Task-category templates | `task-{topic}.md` | `task-error-handling-design.md` |
| Tool-related concepts | `tool-{tool-name}.md` | `tool-security-audit.md` |
| Tool-related tasks | `use-{tool-name}.md` | `use-security-audit.md` |
| Tool-related references | `tool-{tool-name}.md` | `tool-security-audit.md` |
| Tool-related quickstarts | `skill-{skill-name}.md` | `skill-security-audit.md` |
| Help-system concepts | `{topic}.md` | `progressive-depth.md` |
| Error templates | `{slug-from-lesson}.md` | `shadow-dirs.md` |

### Cross-link ID prefixes

The cross-link system generates IDs by combining a type
prefix with the `name` field:

| Type | Prefix | ID example |
|---|---|---|
| concept | `con-` | `con-task-error-handling-design` |
| task | `tas-` | `tas-task-error-handling-design` |
| reference | `ref-` | `ref-task-error-handling-design` |
| quickstart | `qui-` | `qui-task-error-handling-design` |
| error | `err-` | `err-shadow-dirs` |
| warning | `wrn-` | `wrn-pre-commit-stash` |
| tip | `tip-` | `tip-after-code-review` |
| faq | `faq-` | `faq-eval-in-tests` |
| troubleshooting | `tro-` | `tro-mcp-server-not-responding` |
| comparison | `com-` | `com-workflow-vs-wizard` |
| note | `not-` | `not-decision-d1-template-schemas` |

### The four-template set

Task-category topics use the same `name` across all
four directories:

```
concepts/task-my-topic.md       -> con-task-my-topic
tasks/task-my-topic.md          -> tas-task-my-topic
references/task-my-topic.md     -> ref-task-my-topic
quickstarts/task-my-topic.md    -> qui-task-my-topic
```

The cross-link builder connects these automatically
because they share a `name` value.

## File organization

| Directory | Type | What goes here |
|---|---|---|
| `templates/concepts/` | concept | Mental models, explanations, "what is X" |
| `templates/tasks/` | task | Step-by-step procedures |
| `templates/references/` | reference | Lookup tables, complete field lists |
| `templates/quickstarts/` | quickstart | Minimal get-started guides |
| `templates/errors/` | error | Error explanations and fixes |
| `templates/warnings/` | warning | Pitfall prevention |
| `templates/tips/` | tip | Short actionable suggestions |
| `templates/faqs/` | faq | Common question-answer pairs |
| `templates/troubleshooting/` | troubleshooting | Symptom-based diagnosis flows |
| `templates/comparisons/` | comparison | Side-by-side evaluations |
| `templates/notes/` | note | Design decisions and context |

## Body conventions

### Headings

- Level 1 (`#`): One per file, follows type convention
- Level 2 (`##`): Major sections
- Level 3 (`###`): Sub-sections (e.g., numbered steps)
- Never skip levels (no `#` to `###`)
- Blank line above and below every heading

### Tables

Use tables for structured comparisons, field lists, and
lookup data. Tables make content scannable and work well
with progressive depth (the engine can show or hide table
rows by depth level).

```markdown
| Column A | Column B | Column C |
|---|---|---|
| Value | Value | Value |
```

Do not manually pad table cells with extra spaces.

### Code blocks

Surround with triple backticks and specify the language:

````markdown
```python
def example():
    pass
```
````

Blank line above and below every code block.

### "Want to learn more?" prompts

Use natural language prompts in bold that tell the user
exactly what to say:

```markdown
- Say **"what is X?"** for the concept overview
- Say **"how do I do X?"** for the step-by-step guide
- Say **"show me all X fields"** for the reference
- Run `/skill-name` to take action
```

### "Related Topics" links

List sibling templates by type with a brief description:

```markdown
- **Concept**: Topic -- one-line description
- **Task**: Topic -- one-line description
- **Reference**: Topic -- one-line description
- **Quickstart**: Topic -- one-line description
```

## Cross-linking conventions

### Automatic links

The cross-link builder (`build_cross_links.py`)
discovers relationships from:

- **Shared name**: Templates with the same `name` across
  different type directories link automatically
- **Tag overlap**: Templates sharing 2+ tags are
  suggested as related
- **Slug matching**: Error templates link to matching
  Warning templates

### Manual links

Add explicit links in the "Related Topics" section when
the automatic builder would miss the connection (e.g.,
linking a concept about progressive depth to a task about
template authoring).

### Link format in cross_links.json

```json
{
  "con-task-my-topic": {
    "tags": ["tag-a", "tag-b"],
    "related": [
      "tas-task-my-topic",
      "ref-task-my-topic",
      "qui-task-my-topic"
    ]
  }
}
```

## Quality checklist

Before considering a template done:

| Check | Rule |
|---|---|
| Frontmatter complete | All four fields present and valid |
| Type matches directory | `type: concept` is in `concepts/` |
| Name matches filename | `name: task-my-topic` is in `task-my-topic.md` |
| Heading convention | Level-1 heading follows type pattern |
| Required sections | All sections for the type are present |
| No trailing whitespace | Clean lines throughout |
| Lines under 80 chars | Except tables and URLs |
| Single trailing newline | File ends with exactly one `\n` |
| No hard tabs | Spaces only |
| Cross-links resolve | Referenced templates exist |
| Natural language prompts | "Want to learn more?" uses bold prompts |
| Tags are relevant | 2-6 tags that aid discovery |
| No stale references | All mentioned tools and templates exist |
| User-facing language | Written for the template author, not the engine |

## Want to learn more?

- Say **"what makes a good template?"** for the concept
  overview -- the 11 types, anatomy, and why structure
  matters for generation
- Say **"walk me through writing a template"** for the
  step-by-step task guide with a complete worked example
- Say **"I need to create a template now"** for the
  5-step quickstart
- Say **"what is progressive depth?"** to understand how
  depth levels control what the user sees
- Say **"how does cross-linking work?"** to see how the
  builder connects templates automatically
- Say **"how does the help engine test templates?"** to
  learn about validation and rendering tests

## Related Topics

- **Concept**: Template design patterns -- the 11 types,
  anatomy of a template, why structured content matters
- **Task**: Template design patterns -- step-by-step
  authoring guide with a worked example
- **Quickstart**: Template design patterns -- 5-step
  guide from blank file to working template
- **Concept**: Progressive depth -- how templates adapt
  verbosity based on access count
- **Concept**: Cross-linking -- how templates discover
  and reference each other
- **Concept**: Template composition -- how templates
  embed related content at render time
