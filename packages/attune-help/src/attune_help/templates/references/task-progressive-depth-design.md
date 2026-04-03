---
type: reference
subtype: tabular
name: task-progressive-depth-design
tags: [progressive-depth, help-system, authoring, ux]
source: developer-guidance
---

# Progressive Depth Design Reference

Complete content guidelines, section patterns, session
mechanics, and cross-linking conventions for writing
help content at three depth levels.

## Content guidelines per level

### Concept level

| Guideline | Rule |
|-----------|------|
| **Target length** | 20-30 lines of content (excluding frontmatter) |
| **Code blocks** | Avoid. Use only to illustrate a point, never as instructions |
| **Numbered steps** | Never. Concepts orient, they don't instruct |
| **Tables** | For comparisons and tradeoffs, not parameters |
| **Assumed knowledge** | None about this specific topic |
| **Tone** | Explanatory. "This is what X is and why it matters." |
| **Required sections** | Opening definition, comparison/context, "When you'd think about this", "Want to learn more?" |

**Section pattern:**

```markdown
# Topic Name

[1-2 paragraphs defining the concept in plain language]

## [Comparison or breakdown heading]

[Table or list comparing aspects, tradeoffs, or phases]

## When you'd think about this

[Concrete situations where this topic becomes relevant]

## Want to learn more?

[Natural language prompts to task and reference levels]
```

### Task level

| Guideline | Rule |
|-----------|------|
| **Target length** | 40-80 lines of content |
| **Code blocks** | Required. Runnable commands with expected output |
| **Numbered steps** | Required. Use `### Step N:` subheadings |
| **Tables** | For decision-making ("if X, do Y") |
| **Assumed knowledge** | Reader knows what the topic is, not how to do it |
| **Tone** | Instructional. "Here's how to do X." |
| **Required sections** | Brief intro (not a recap), numbered steps, "What to do next", "Want to learn more?" |

**Section pattern:**

```markdown
# How to [Do the Thing]

[1-2 sentence intro -- what you're about to do, not
what the concept is]

## Prerequisites

[Optional. Only if there are real prerequisites]

### Step 1: [Action]

[Instruction]

` ` `
[command]
` ` `

[What to expect]

### Step 2: [Action]

...

## What to do next

[Table of goals mapped to next actions]

## Want to learn more?

[Natural language prompts to concept and reference]
```

### Reference level

| Guideline | Rule |
|-----------|------|
| **Target length** | 100+ lines of content |
| **Code blocks** | For syntax examples and configuration snippets |
| **Numbered steps** | Never. References are organized by category, not sequence |
| **Tables** | Primary format. Parameters, flags, options, edge cases |
| **Assumed knowledge** | Reader knows the concept and basic workflow |
| **Tone** | Documentary. "Here are all the options for X." |
| **Required sections** | Brief description, categories with tables, "Common problems", "Want to learn more?" |

**Section pattern:**

```markdown
# [Topic] Reference

[1-2 line description of scope]

## [Category 1]

[Table of options, parameters, or syntax]

## [Category 2]

[Table of options with examples]

## Common problems

[Table: problem, cause, fix]

## Want to learn more?

[Natural language prompts to concept and task levels]
```

## Frontmatter format

All three files for one topic share the same `name` and
`tags`. Only `type` differs:

```yaml
# concepts/task-{topic}.md
---
type: concept
name: task-{topic}
tags: [relevant, tags, here]
source: developer-guidance
---

# tasks/task-{topic}.md
---
type: task
name: task-{topic}
tags: [relevant, tags, here]
source: developer-guidance
---

# references/task-{topic}.md
---
type: reference
subtype: tabular
name: task-{topic}
tags: [relevant, tags, here]
source: developer-guidance
---
```

The shared `name` field is how the engine knows these
three files belong to the same topic. When a user says
"tell me more", the engine looks for the next type with
the same name.

## Quickstart level (optional fourth file)

Some topics also have a quickstart in
`quickstarts/task-{topic}.md`. This is a compressed
task document for users who want the fastest path
without explanation.

| Guideline | Rule |
|-----------|------|
| **Target length** | 30-50 lines |
| **Steps** | 5 maximum, bold-numbered (not `###`) |
| **Code blocks** | Minimal -- one per step |
| **Tables** | At most one, for "still stuck?" branching |
| **Tone** | Direct. "Do this, then this, done." |
| **Title pattern** | Action-oriented: "Add a Dependency", not "Dependency Management" |

## Session state mechanics

The help engine maintains a `SessionState` dict per
user session:

| Field | Type | Description |
|-------|------|-------------|
| `last_template_id` | `str` | Name of the last-served template |
| `depth` | `int` | Current depth level (0=concept, 1=task, 2=reference) |
| `last_access` | `datetime` | Timestamp of last access |

### Depth progression

| Action | Effect on depth |
|--------|----------------|
| First request for topic X | Depth set to 0, serve concept |
| "Tell me more" (same topic) | Depth increments to 1, serve task |
| "Tell me more" again | Depth increments to 2, serve reference |
| "Tell me more" at depth 2 | Stays at 2, re-serves reference |
| Request for topic Y | Depth resets to 0 for topic Y |
| 4+ hours of inactivity | Session expires, next request starts at 0 |

### TTL and expiration

Session state has a 4-hour TTL. After 4 hours without
any help request, the session is cleared. This prevents
stale depth from surprising users who return the next
day -- they'll see the concept level fresh, which is
correct because context has been lost.

Topic switching is immediate. Asking about "auth
patterns" after reading the dependency management
reference starts "auth patterns" at depth 0 regardless
of where you were in the previous topic.

## Cross-linking conventions

### "Want to learn more?" section

Every file at every level ends with this section. The
prompts use natural language that matches what a user
would actually type or say:

| Linking to | Prompt pattern | Example |
|------------|---------------|---------|
| Concept | "what is {topic}?" | "what is dependency management?" |
| Task | "how do I {action}?" | "how do I add a dependency?" |
| Reference | "show me the {topic} reference" | "show me the dependency reference" |
| Quickstart | "quickstart for {topic}" | "quickstart for adding a dependency" |
| Related workflow | "run a {workflow}" | "run a security audit" |
| Related command | "{slash-command}" | "/fix-test" |

### Cross-level references within content

When a task or reference needs to reference another
level, use inline natural language rather than file
paths:

```markdown
For background on why this matters, see the concept:
say **"what is dependency management?"**
```

Do not use relative file paths or template IDs in
user-facing content. The engine resolves natural
language prompts to the correct template.

## Testing that each level serves its purpose

### Concept-level tests

- [ ] Can someone with no prior knowledge of this topic
      understand the document after one read?
- [ ] Does it avoid code blocks (or use them only for
      illustration)?
- [ ] Does it answer "what" and "why" without answering
      "how"?
- [ ] Is it under 35 lines of content?
- [ ] Does it end with natural language prompts to the
      task and reference?

### Task-level tests

- [ ] Are the steps numbered and actionable?
- [ ] Does each step include a command or clear action?
- [ ] Could someone follow this without reading the
      concept first?
- [ ] Does it show expected output after commands?
- [ ] Is it between 40 and 80 lines?
- [ ] Does it stay on the 80% path (common case, not
      every edge case)?

### Reference-level tests

- [ ] Can a reader find a specific detail (flag, option,
      syntax) in under 10 seconds of scanning?
- [ ] Is content organized by category, not by narrative
      sequence?
- [ ] Are tables the primary content format?
- [ ] Does it cover edge cases and common problems?
- [ ] Is it 100+ lines?
- [ ] Does it avoid re-explaining the concept or
      repeating task steps?

## Common authoring mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Concept contains steps | "Step 1: install..." appears in the concept file | Move steps to task, replace with "why you'd do this" |
| Task recaps the concept | First 3 paragraphs explain what the thing is | Cut to 1-2 sentences max, link back to concept |
| Reference has narrative flow | Reads like a tutorial, not a lookup table | Reorganize by category, convert prose to tables |
| All three levels say the same thing | "Tell me more" feels like re-reading | Audit: concept=what/why, task=how, reference=everything |
| Quickstart has 10 steps | Longer than the task | Cut to 5 steps max, move detail to task |
| Cross-links use file paths | "See `templates/tasks/task-foo.md`" | Replace with natural language: "say **how do I...**" |
| Missing "Want to learn more?" | Reader has no path to other levels | Add section with prompts to all related levels |

## Want to learn more?

- Say **"what is progressive depth?"** to go back to the
  design philosophy
- Say **"how do I write progressive depth content?"** for
  the step-by-step authoring guide
- Say **"quickstart for progressive depth content"** to
  jump straight to the 5-step workflow
