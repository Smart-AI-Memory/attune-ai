---
type: quickstart
name: task-template-design-patterns
tags: [templates, design, help-system, authoring]
source: developer-guidance
---

# Quickstart: Create Your First Template

The fastest path from "I need to write a help template"
to a working template that renders and cross-links
correctly.

## 5 steps

**1. Pick the type and directory**

Decide what the user needs:

| They need... | Type | Directory |
|---|---|---|
| An explanation | concept | `templates/concepts/` |
| Step-by-step instructions | task | `templates/tasks/` |
| A lookup table | reference | `templates/references/` |
| The fastest start | quickstart | `templates/quickstarts/` |

For a developer task category, create all four. They
share the same `name` and cross-link automatically.

**2. Create the file with frontmatter**

Create `templates/concepts/task-my-topic.md` (or the
directory matching your type):

```yaml
---
type: concept
name: task-my-topic
tags: [relevant, tags, here]
source: developer-guidance
---
```

Rules: `type` matches the directory, `name` matches the
filename (without `.md`), tags are lowercase with
hyphens, 2-6 per template.

**3. Write the body**

Follow the heading convention for your type:

```markdown
# Concept: My topic

## What

One paragraph defining the concept.

## Why

One paragraph explaining why it matters.

## Key details

| Option | When to use | Trade-off |
|---|---|---|
| Option A | Situation A | Pro / con |
| Option B | Situation B | Pro / con |
```

Each type has required sections. Concepts need "What"
and "Why." Tasks need "Prerequisites," numbered "Steps,"
and "Verification." References need lookup tables.
Quickstarts need numbered steps and "What you just did."

**4. Add cross-linking sections**

End every template with these two sections:

```markdown
## Want to learn more?

- Say **"how do I do X?"** for the step-by-step guide
- Say **"show me all X options"** for the reference
- Run `/relevant-skill` to take action

## Related Topics

- **Task**: My topic -- brief description
- **Reference**: My topic -- brief description
- **Quickstart**: My topic -- brief description
```

The "Want to learn more?" prompts use natural language
in bold. The "Related Topics" section lists siblings
for the cross-link builder.

**5. Verify it works**

Check your template renders without errors:

```
python -c "
from attune_help import HelpEngine
engine = HelpEngine()
result = engine.populate('con-task-my-topic')
print(result[:200])
"
```

If you created the four-template set, verify all four
IDs resolve: `con-task-my-topic`, `tas-task-my-topic`,
`ref-task-my-topic`, `qui-task-my-topic`.

## What you just did

- Chose a template type based on user need
- Created a file with valid YAML frontmatter
- Structured the body with the required sections
- Added cross-linking prompts for discoverability
- Verified the template renders in the help engine

## Next steps

- Say **"tell me more about templates"** for the full
  authoring guide -- choosing types, structuring bodies,
  building a complete worked example
- Say **"show me all template fields"** for the complete
  reference -- every frontmatter field, every required
  section, naming conventions, and quality checklist
- Say **"what makes a good template?"** to understand
  the 11 types and why structured content matters
- Say **"what is progressive depth?"** to learn how
  templates adapt verbosity on repeated access
- Say **"how does cross-linking work?"** to see how
  the builder connects templates automatically

## Related Topics

- **Concept**: Template design patterns -- the 11 types,
  anatomy of a template, why structure matters
- **Task**: Template design patterns -- full step-by-step
  authoring guide with worked example
- **Reference**: Template design patterns -- all fields,
  types, sections, naming conventions, quality checklist
- **Concept**: Progressive depth -- how depth levels
  control verbosity
- **Concept**: Cross-linking -- how templates discover
  and reference each other
