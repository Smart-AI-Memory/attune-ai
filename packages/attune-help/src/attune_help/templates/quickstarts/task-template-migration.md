---
type: quickstart
name: task-template-migration
tags: [migration, help-system, documentation, templates]
source: developer-guidance
---

# Quickstart: Move Your First Doc to Templates

The fastest path from "I have static docs" to "I have a
working template-based help topic." Start with one
document. The whole thing takes about 15 minutes.

## Step 1: Pick one document

Choose the doc you'd most like to improve. Good first
candidates:

- Your README (everybody reads it, it's probably stale)
- A getting-started guide (high traffic, easy to split)
- An FAQ page (natural split into individual entries)

Don't pick your longest or most complex doc. Pick one
that's useful but imperfect.

## Step 2: Identify the four layers

Read through your document and highlight which parts
answer which question:

| Question | Template type | Highlight color |
|---|---|---|
| "What is this and why does it matter?" | Concept | Blue |
| "How do I do this step by step?" | Task | Green |
| "What are all the options and details?" | Reference | Yellow |
| "Just get me started fast" | Quickstart | Red |

Most documents mix all four. A typical README has a
one-paragraph concept (blue), install steps that are
a quickstart (red), a usage section that's a task
(green), and a configuration table that's a reference
(yellow).

## Step 3: Create the four template files

Create one file in each directory, all sharing the same
name:

```
templates/concepts/task-your-topic.md
templates/tasks/task-your-topic.md
templates/references/task-your-topic.md
templates/quickstarts/task-your-topic.md
```

Add frontmatter to each:

```yaml
---
type: concept
name: task-your-topic
tags: [your-tag-1, your-tag-2, your-tag-3]
source: developer-guidance
---
```

Change `type:` to match the directory (concept, task,
reference, quickstart).

## Step 4: Move the content

Distribute your highlighted sections into the matching
templates:

- **Concept**: The "what" and "why" paragraphs. Add a
  comparison table if the topic has alternatives.
- **Task**: The step-by-step instructions. Number the
  steps. Add a verification checklist at the end.
- **Reference**: The tables, parameter lists, and edge
  cases. Be exhaustive here.
- **Quickstart**: The shortest possible happy path. Five
  steps max. Skip edge cases entirely.

Don't copy the same text into multiple templates.
Rewrite each one for its specific reader.

## Step 5: Add cross-links

End each template with a "Want to learn more?" section
that points to its siblings:

```markdown
## Want to learn more?

- Say **"what is [topic]?"** for the concept overview
- Say **"how do I [topic]?"** for the step-by-step guide
- Say **"show me [topic] reference"** for the full
  details
- Say **"quickstart for [topic]"** for the 5-minute
  version
```

Then delete or redirect the original document. Two
sources of truth will drift.

## What you just did

- Took one static document and split it into four
  focused templates
- Each template serves a different reader need
- Cross-links connect them so readers can navigate by
  depth
- The original monolithic doc is replaced by a
  structured, maintainable set

## What to do next

Repeat for your next most-read document. Each one gets
faster as you internalize the pattern.

| Your next goal | What to say |
|---|---|
| Migrate another doc | Repeat these 5 steps with the next document |
| Understand the system deeply | "what is template migration?" |
| See all the restructuring patterns | "show me the migration reference" |
| Get the full step-by-step guide | "how do I migrate my docs?" |

## Want to learn more?

- Say **"what is template migration?"** for the concept
  overview -- why static docs rot and what templates fix
- Say **"how do I migrate my docs to templates?"** for
  the complete step-by-step guide with audit and
  verification
- Say **"show me the migration reference"** for the
  decision matrix, naming conventions, and common
  mistakes
- Ask **"/doc-gen"** to generate template stubs from
  source code automatically
- Ask **"/help"** to see the template system in action

## Related Topics

- **Concept**: Template migration -- why migrate, what
  you gain, what it costs
- **Task**: Template migration -- full step-by-step
  guide with audit and iteration
- **Reference**: Template migration -- decision matrix,
  restructuring patterns, naming conventions
