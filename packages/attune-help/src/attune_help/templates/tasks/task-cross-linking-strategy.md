---
type: task
name: task-cross-linking-strategy
tags: [cross-linking, navigation, help-system, authoring]
source: developer-guidance
---

# Task: Add cross-links to templates

Connect new or existing templates to related content so
users can navigate naturally between topics. This guide
covers identifying related templates, writing the
navigation sections, adding tags for discovery, and
verifying that the links resolve.

## Prerequisites

- At least one template you want to connect (new or
  existing)
- Familiarity with the template types (concept, task,
  reference, quickstart, error, warning, tip, FAQ, note)
- Access to `scripts/build_cross_links.py` for rebuild

## Steps

### 1. Identify related templates

Start by listing templates that answer follow-up
questions a reader might ask after reading yours.

| If your template is... | Look for related... | Why |
|---|---|---|
| An error | Warning with the same slug, FAQ with the same slug, tips with overlapping title words | Users who hit an error want prevention, explanation, and fixes |
| A task | Reference for the same tool or topic, concept for the "why", quickstart for the short version | Users who follow steps want deeper context or a quick alternative |
| A concept | Task for the "how", reference for the full spec, quickstart for the fast path | Users who understand "why" want to act on it |
| A skill reference | Tool references mentioned in the skill body, task for "how to use it" | Users who read about a skill want to know its tools and usage |

Use the tag index to find templates in the same topic
area. Run this to see what shares your tags:

```bash
python -c "
import json
links = json.load(open(
    'packages/attune-help/src/attune_help/'
    'templates/cross_links.json'
))
tag = 'your-tag-here'
print(links.get('tag_index', {}).get(tag, []))
"
```

### 2. Write the "Want to learn more?" section

Add a section at the bottom of your template (before
"Related Topics") that uses natural language prompts.
Each prompt is a question the reader might actually ask,
followed by a pointer to the answer.

**Pattern:**

```markdown
## Want to learn more?

- "Question a reader would ask" -- see the **type**
  template for a description of what they will find
- "Another natural question" -- see the **type**
  template for what it covers
```

**Concrete example -- linking a new error template:**

Suppose you created `err-missing-api-key`. The reader
who hits this error might ask:

```markdown
## Want to learn more?

- "How do I prevent this from happening again?" -- see
  the **warning** template for the API key configuration
  checklist
- "Why does Attune need an API key at all?" -- see the
  **FAQ** for authentication strategy details
- "What is the recommended way to store API keys?" --
  see the **tip** template for secrets management
  patterns
```

**Rules for writing prompts:**

| Do | Don't |
|---|---|
| Use a question the reader would actually type | Use technical template IDs in the prompt |
| Name the template type in bold (**concept**, **task**) | Use raw file paths or markdown links |
| Describe what the reader will find there | Just say "see related template" |
| Limit to 3-5 prompts per template | List every vaguely related template |

### 3. Write the "Related Topics" section

After the prompts, add a structured list of related
templates. This section is more formal and is used by
the build script and the help engine for navigation.

```markdown
## Related Topics

- **Concept**: Topic name -- one-line summary of what
  the concept template covers
- **Task**: Topic name -- one-line summary of what the
  task template covers
- **Reference**: Topic name -- one-line summary of the
  reference scope
- **Quickstart**: Topic name -- one-line summary of the
  quick guide
```

For task-category templates (con-task-*, tas-task-*,
ref-task-*, qui-task-*), always link all four types to
each other. For error/warning/FAQ templates, link the
matching slug pairs.

### 4. Add tags for tag-based discovery

Tags are the catch-all discovery mechanism. Every
template should have 2-4 tags in its frontmatter that
describe the topic, not the template type.

```yaml
tags: [security, path-validation, file-io]
```

**Tag naming conventions:**

| Convention | Example | Purpose |
|---|---|---|
| Lowercase, hyphenated | `code-review` | Consistency across all templates |
| Topic-focused, not type-focused | `security` not `error-security` | Tags group by topic, not by template type |
| Reuse existing tags when possible | Check `cross_links.json` tag_index first | Avoid near-duplicates like `auth` vs `authentication` |
| 2-4 tags per template | `[auth, setup, security]` | Enough for discovery, not so many that every search matches |

### 5. Rebuild cross-links and verify

After editing templates, rebuild the cross-links JSON
and verify your links resolve.

```bash
# Rebuild cross_links.json
python scripts/build_cross_links.py

# Check that your template appears in the output
python -c "
import json
data = json.load(open(
    'packages/attune-help/src/attune_help/'
    'templates/cross_links.json'
))
template_id = 'your-template-id'
print(json.dumps(
    data['links'].get(template_id, {}),
    indent=2,
))
"
```

### 6. Test navigation manually

Verify the user experience by following the cross-links
from your template.

- Read your template as a user would
- For each "Want to learn more?" prompt, confirm the
  referenced template exists and answers the question
- For each "Related Topics" entry, confirm the template
  type and name are correct
- Search by each of your tags and confirm your template
  appears in the results

## Verification

After adding cross-links:

- [ ] "Want to learn more?" section has 3-5 natural
      language prompts
- [ ] Each prompt names the target template type in bold
- [ ] "Related Topics" lists all directly related
      templates with type and summary
- [ ] Tags are lowercase, hyphenated, and reuse existing
      tags where possible
- [ ] `build_cross_links.py` runs without errors
- [ ] Your template appears in `cross_links.json` with
      the expected links
- [ ] Manual navigation from your template reaches all
      referenced content

## Want to learn more?

- "Why does cross-linking matter?" -- see the **concept**
  template for the knowledge graph design and the 7 link
  rules
- "Show me all the link rules and JSON structure" -- see
  the **reference** template for the complete
  specification
- "I just need the quick version" -- see the
  **quickstart** for a 5-step guide

## Related Topics

- **Concept**: Cross-linking strategy -- why cross-links
  matter, the 7 deterministic rules, and the navigation
  pattern
- **Reference**: Cross-linking strategy -- all link
  rules, cross_links.json structure, tag conventions, and
  rebuild script details
- **Quickstart**: Cross-linking strategy -- 5-step guide
  to connecting templates
