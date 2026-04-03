---
type: task
name: task-template-design-patterns
tags: [templates, design, help-system, authoring]
source: developer-guidance
---

# How to Write a Help Template

A step-by-step guide for creating a new template in
attune-help. By the end, you will have a working template
that renders correctly, links to related content, and
follows the conventions other templates use.

## Prerequisites

- Familiarity with YAML frontmatter and markdown
- Access to the `packages/attune-help/` directory
- A topic that fits one of the 11 template types

## Steps

### 1. Choose the template type

Decide what the user needs when they encounter your
content:

| User's situation | Choose this type | Body shape |
|---|---|---|
| "What is X?" -- needs a mental model | concept | What, Why, detail sections |
| "How do I do X?" -- needs instructions | task | Prerequisites, numbered Steps, Verification |
| "What are all the options for X?" -- needs a lookup | reference | Tables, field lists, code blocks |
| "Just get me started with X" -- needs speed | quickstart | 3-7 numbered steps, What you just did |
| "I hit error X" -- needs a fix | error | Symptom, Cause, Fix |
| "I keep hitting X" -- needs prevention | warning | What happens, Why, Prevention |
| "Quick tip about X" | tip | One actionable paragraph |
| "Is it true that X?" | faq | Question heading, answer body |
| "Something is wrong but I don't know what" | troubleshooting | Symptoms, Diagnosis, Resolution |
| "Should I use X or Y?" | comparison | Criteria table, recommendation |
| "Why was X decided?" | note | Context, Decision, Rationale |

If your topic is a developer task category (like
"database migrations" or "error handling"), plan all four
core types: concept, task, reference, quickstart. They
share the same `name` and cross-link automatically.

### 2. Write the frontmatter

Create a new `.md` file in the correct directory. The
filename matches the `name` field:

```yaml
---
type: task
name: task-my-topic
tags: [relevant, lowercase, tags]
source: developer-guidance
---
```

Frontmatter rules:

| Field | Required | Format | Notes |
|---|---|---|---|
| `type` | Yes | One of 11 type names | Must match the directory the file lives in |
| `name` | Yes | Lowercase slug with hyphens | Becomes the template ID with prefix (`tas-task-my-topic`) |
| `tags` | Yes | YAML list of strings | Lowercase, hyphenated, 2-6 tags |
| `source` | Yes | File path or `developer-guidance` | Indicates where the content came from |

### 3. Structure the body

Start with a level-1 heading that follows the type's
convention:

| Type | Heading pattern | Example |
|---|---|---|
| concept | `# Concept: Topic name` | `# Concept: Error handling design` |
| task | `# How to Do the Thing` | `# How to Write a Help Template` |
| reference | `# Reference: Topic name` | `# Reference: Authentication patterns` |
| quickstart | `# Quickstart: Action Phrase` | `# Quickstart: Create Your First Template` |

Add the sections required for your type. Use `##` for
major sections and `###` for sub-sections within them.

For task templates, the body structure is:

```markdown
# How to Do the Thing

Brief description of what this guide covers.

## Prerequisites

- What the user needs before starting

## Steps

### 1. First step title

Explanation and code examples.

### 2. Second step title

Explanation and code examples.

## Verification

- [ ] Checklist of things to confirm

## What to do next

| Goal | What to say |
|---|---|
| Related action | "natural language prompt" |

## Want to learn more?

- Say **"prompt"** for related concept/reference/quickstart
```

### 4. Add cross-linking sections

Every template should end with two sections that connect
it to related content:

**"Want to learn more?"** -- natural language prompts
that tell the user what to say to reach related templates:

```markdown
## Want to learn more?

- Say **"what is X?"** for the concept overview
- Say **"show me the full reference"** for lookup tables
- Say **"I need to do X quickly"** for the quickstart
- Run `/skill-name` to take action on this topic
```

**"Related Topics"** -- explicit links for the
cross-link builder:

```markdown
## Related Topics

- **Concept**: Topic name -- brief description
- **Task**: Topic name -- brief description
- **Reference**: Topic name -- brief description
- **Quickstart**: Topic name -- brief description
```

### 5. Write a complete example

Here is a minimal concept template being built from
scratch:

```markdown
---
type: concept
name: task-retry-strategies
tags: [error-handling, resilience, python]
source: developer-guidance
---

# Concept: Retry strategies

## What

A retry strategy defines how your code responds to
transient failures -- network timeouts, rate limits,
temporary unavailability. The three common strategies
are fixed delay, exponential backoff, and circuit
breaker.

## Why

Without retries, a single transient failure becomes a
permanent failure. With naive retries (immediate,
unlimited), you create a thundering herd that makes
the outage worse. A good strategy balances recovery
speed against system load.

## Strategy comparison

| Strategy | Delay pattern | Best for | Risk |
|---|---|---|---|
| Fixed delay | Same wait every time | Simple scripts | Can overload a recovering service |
| Exponential backoff | Doubles each attempt | API clients | Slow recovery if first attempts fail |
| Circuit breaker | Stops trying after threshold | Microservices | Needs health check to re-close |

## Want to learn more?

- Say **"how do I add retries?"** for the step-by-step
  task guide
- Say **"show me retry code examples"** for the
  complete reference

## Related Topics

- **Task**: Retry strategies -- step-by-step guide
- **Reference**: Retry strategies -- full pattern catalog
```

### 6. Test the rendering

Verify your template works with the help engine:

```
python -c "
from attune_help import HelpEngine
engine = HelpEngine()
result = engine.populate('con-task-my-topic')
print(result[:200])
"
```

Check that:

- The template loads without errors
- Frontmatter is parsed correctly
- Cross-links resolve to existing templates

## Verification

- [ ] File is in the correct directory for its type
- [ ] Filename matches the `name` field in frontmatter
- [ ] All four frontmatter fields are present and valid
- [ ] Body starts with a level-1 heading
- [ ] Required sections for the type are present
- [ ] "Want to learn more?" uses natural language prompts
- [ ] "Related Topics" lists sibling templates by type
- [ ] No trailing whitespace or hard tabs
- [ ] Lines stay under 80 characters (except tables)
- [ ] File ends with a single trailing newline

## What to do next

| Goal | What to say |
|---|---|
| Check all frontmatter fields | "show me the template reference" |
| Understand progressive depth | "what is progressive depth?" |
| Build the cross-links index | "how does cross-linking work?" |
| Review template quality | "run code quality check" |

## Want to learn more?

- Say **"what makes a good template?"** for the concept
  overview -- the 11 types, anatomy, and why structured
  content matters
- Say **"show me all template fields and conventions"**
  for the complete reference -- every frontmatter field,
  body section, and naming rule
- Say **"I need to create a template now"** for the
  5-step quickstart
- Say **"what is progressive depth?"** to understand how
  templates adapt their verbosity
- Say **"how does cross-linking work?"** to see how
  templates discover each other automatically

## Related Topics

- **Concept**: Template design patterns -- the 11 types,
  anatomy of a template, why structure matters
- **Reference**: Template design patterns -- all fields,
  types, sections, naming conventions, quality checklist
- **Quickstart**: Template design patterns -- 5-step
  guide from blank file to working template
- **Concept**: Progressive depth -- how depth levels
  control verbosity
- **Concept**: Cross-linking -- how templates reference
  each other
