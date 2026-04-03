---
type: quickstart
name: task-progressive-depth-design
tags: [progressive-depth, help-system, authoring, ux]
source: developer-guidance
---

# Write Progressive Depth Content for a Topic

The fastest path from "I have a topic" to "all three
depth levels are written and cross-linked."

## 5 steps

**1. Pick one topic and name it**

Choose a single topic. Name it with the `task-` prefix:
`task-dependency-management`, `task-debugging-sessions`,
etc. This name goes in the `name` frontmatter field of
all three files.

**2. Write the concept (20-30 lines)**

Answer "what is this and why does it matter?" No code,
no steps, no how-to. End with "Want to learn more?"
prompts.

```markdown
# Topic Name

[Plain-language definition. What it is, why it
matters, when it comes up.]

## Want to learn more?

- Say **"how do I...?"** for the step-by-step guide
- Say **"show me the reference"** for all options
```

Save as `concepts/task-{topic}.md`.

**3. Write the task (40-80 lines)**

Answer "how do I do this?" with numbered steps, code
blocks, and expected output. Don't re-explain the
concept -- jump straight into instructions.

```markdown
# How to [Do the Thing]

### Step 1: [Action]

[Command + expected output]

### Step 2: [Action]

...
```

Save as `tasks/task-{topic}.md`.

**4. Write the reference (100+ lines)**

Answer "what are all the options?" with tables for
every parameter, flag, and edge case. Organize by
category, not by narrative. No concept recap, no
step-by-step instructions.

```markdown
# [Topic] Reference

## [Category]

| Option | Description | Default |
|--------|-------------|---------|
| ...    | ...         | ...     |
```

Save as `references/task-{topic}.md`.

**5. Cross-link all three files**

Add a "Want to learn more?" section at the bottom of
each file with natural language prompts pointing to the
other two levels.

| In this file | Link to concept with | Link to task with | Link to reference with |
|-------------|---------------------|-------------------|----------------------|
| Concept | (you're here) | "how do I {action}?" | "show me the reference" |
| Task | "what is {topic}?" | (you're here) | "show me the reference" |
| Reference | "what is {topic}?" | "how do I {action}?" | (you're here) |

## What you just did

- Wrote three genuinely different documents, not three
  lengths of the same one
- Concept: orients a newcomer (what/why)
- Task: instructs a practitioner (how)
- Reference: documents everything for lookup (all options)
- Cross-linked so "tell me more" navigates naturally

## Sanity check

| Level | Quick test |
|-------|-----------|
| Concept | Does it avoid code and numbered steps? |
| Task | Could someone follow it without the concept? |
| Reference | Can you find a specific option in 10 seconds? |

If any level fails its test, it's probably doing the
job of a different level. Move the content.

## Want to learn more?

- Say **"what is progressive depth?"** for the design
  philosophy behind this approach
- Say **"how do I write progressive depth content?"**
  for the full authoring guide with worked examples
- Say **"show me the content guidelines"** for length
  targets, section patterns, and session state mechanics
