---
type: task
name: task-progressive-depth-design
tags: [progressive-depth, help-system, authoring, ux]
source: developer-guidance
---

# How to Write Progressive Depth Content

When you add a new topic to the help system, you write
three files -- a concept, a task, and a reference. Each
one serves a different reader need, not a different
length target.

## Before you start

Pick one topic. You'll write all three levels for that
topic before moving to the next one. Having one polished
topic across three levels is more valuable than three
topics with only a concept each.

## Step 1: Write the concept (what is it?)

The concept answers "what is this and why should I
care?" in 20-30 lines. No how-to instructions, no
code unless it illustrates a point.

**Structure:**

- Opening paragraph: define the thing in plain language
- A table or list comparing aspects (when/why/tradeoffs)
- "When you'd think about this" section -- concrete
  situations where this topic becomes relevant
- "Want to learn more?" with natural language prompts

**Example -- dependency management concept opening:**

```markdown
Every package you add to your project is a decision
with long-term consequences. A dependency brings code
you didn't write into your supply chain -- its bugs
become your bugs, its vulnerabilities become your
vulnerabilities.
```

Notice: no commands, no `pip install`, no code blocks.
Just orientation.

### Common mistake: concept that's really a task

If your concept has numbered steps or tells the reader
to run a command, it's a task wearing a concept's
clothes. Move the instructions to the task file and
replace them with the "why" behind those instructions.

## Step 2: Write the task (how do I do it?)

The task answers "how do I actually do this?" with
step-by-step instructions, runnable commands, and
expected output. Target 40-80 lines.

**Structure:**

- Brief intro (1-2 sentences, not a concept recap)
- Numbered steps with `###` subheadings
- Each step: what to do, a code block, what to expect
- Decision tables for branching paths
- "What to do next" section with natural language prompts

**Example -- dependency management task excerpt:**

```markdown
### Step 1: Check the package

Look at the package on PyPI and its source repository:

| Question | Where to look | Red flag |
|----------|--------------|----------|
| Last release? | PyPI release history | Over 2 years ago |
| Known CVEs? | `pip-audit` or osv.dev | Unpatched advisories |
```

Notice: the reader already knows what dependency
management is. The task doesn't re-explain it -- it
jumps straight into what to do.

### Common mistake: task that's really a reference

If your task has 15 steps, or spends more time listing
every possible flag than guiding the reader through the
common path, it's a reference. Move the exhaustive
detail to the reference file. Keep the task focused on
the 80% path -- the thing most people need to do most
of the time.

## Step 3: Write the reference (show me everything)

The reference answers "what are all the options?" for
a reader who already knows the concept and the basic
workflow. Target 100+ lines.

**Structure:**

- Brief description (1-2 lines, not an intro)
- Organized by category (syntax, tools, config, etc.)
- Tables for every parameter, flag, and option
- Edge cases, gotchas, and common problems
- Cross-links back to concept and task

**Example -- dependency management reference excerpt:**

```markdown
## Version constraint syntax

| Specifier | Example | What it allows | When to use |
|-----------|---------|---------------|-------------|
| `>=` | `>=2.0.0` | 2.0.0 and above | Libraries with good semver |
| `>=,<` | `>=2.0.0,<3.0` | 2.x only | Most dependencies |
| `~=` | `~=2.5.0` | >=2.5.0, <2.6.0 | Tight compatibility |
| `==` | `==2.5.3` | Exactly this | Reproducible builds |
```

Notice: no explanation of what version constraints are
or why you'd use them. The reader knows. They just need
the syntax table.

## Step 4: Add cross-links

Each file ends with a "Want to learn more?" section that
links to the other two levels using natural language
prompts. These prompts match what a user would actually
say:

```markdown
## Want to learn more?

- Say **"what is dependency management?"** to go back
  to the overview
- Say **"how do I manage dependencies?"** for the
  step-by-step guide
- Say **"show me the reference"** for version constraint
  syntax and all tooling options
```

## Step 5: Verify each level serves its purpose

Test each document against these questions:

| Level | Test question | Pass if... |
|-------|--------------|------------|
| **Concept** | Could someone who's never heard of this topic understand it? | Yes -- no jargon without explanation, no assumed knowledge |
| **Task** | Could someone follow this without the concept? | Yes -- self-contained steps, clear expected output |
| **Reference** | Could someone find a specific detail in under 10 seconds? | Yes -- organized by category, scannable tables |

If the concept fails its test, it's probably too
technical. If the task fails, it probably assumes too
much. If the reference fails, it probably needs better
organization or more tables.

## Worked example: all three levels for one topic

Here's how the same information about "extras in
pyproject.toml" appears at each level:

**Concept level:**

> Optional features let users install only the parts
> of your package they need. A data scientist doesn't
> need your Redis cache; a backend engineer doesn't
> need your notebook integration.

**Task level:**

> Add an extras section to your `pyproject.toml`:
>
> ```toml
> [project.optional-dependencies]
> redis = ["redis>=5.0.0"]
> ```
>
> Install it with `pip install 'your-package[redis]'`.

**Reference level:**

> | Extra | Packages | Purpose |
> |-------|----------|---------|
> | `redis` | redis>=5.0.0 | Redis memory backend |
> | `developer` | pytest, ruff, black | Dev toolchain |
> | `memory` | sentence-transformers | Embedding cache |

Same topic. Three genuinely different documents.

## What to do next

| Goal | What to say |
|------|-------------|
| See the content guidelines per level | "show me the progressive depth reference" |
| Understand the design philosophy | "what is progressive depth?" |
| Start writing immediately | "quickstart for progressive depth content" |
