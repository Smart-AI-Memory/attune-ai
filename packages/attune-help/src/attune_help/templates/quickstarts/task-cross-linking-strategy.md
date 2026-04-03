---
type: quickstart
name: task-cross-linking-strategy
tags: [cross-linking, navigation, help-system, authoring]
source: developer-guidance
---

# Quickstart: Connect your templates

Five steps to cross-link a new or existing template to
related content.

## 1. Find related templates by tag

Check what already exists in your topic area.

```bash
python -c "
import json
data = json.load(open(
    'packages/attune-help/src/attune_help/'
    'templates/cross_links.json'
))
for tid in data.get('tag_index', {}).get('your-tag', []):
    print(tid)
"
```

Replace `your-tag` with the primary topic of your
template (e.g., `security`, `auth`, `pre-commit`). The
output lists every template that shares that tag.

## 2. Identify the link targets

Pick 3-5 templates that answer follow-up questions a
reader of your template would ask.

| Your template type | Best targets |
|---|---|
| Error | Matching warning (same slug), FAQ (same slug), tips (related topic) |
| Task | Reference for the same tool, concept for the "why", quickstart for the short version |
| Concept | Task for the "how", reference for the full spec |
| Quickstart | Task for the full guide, concept for the background |

For task-category templates (`task-*` naming), always
link all four types: concept, task, reference, and
quickstart.

## 3. Add the "Want to learn more?" section

Write natural language prompts -- questions the reader
would actually ask -- pointing to each target.

```markdown
## Want to learn more?

- "How do I prevent this error?" -- see the **warning**
  template for the prevention checklist
- "Why does this happen?" -- see the **concept**
  template for the underlying design decision
- "Show me the full specification" -- see the
  **reference** template for all configuration options
```

Use double quotes around the question, bold the template
type, and describe what the reader will find.

## 4. Add tags to your frontmatter

Ensure your template has 2-4 topic tags that match
existing tags in the index.

```yaml
---
type: error
name: your-template-name
tags: [security, path-validation, file-io]
source: developer-guidance
---
```

Check existing tags first to avoid near-duplicates (use
`auth` not `authentication` if `auth` already exists).

## 5. Rebuild and verify

Run the build script and confirm your template appears
in the output with the expected links.

```bash
# Rebuild
python scripts/build_cross_links.py

# Verify your template's links
python -c "
import json
data = json.load(open(
    'packages/attune-help/src/attune_help/'
    'templates/cross_links.json'
))
import pprint
pprint.pprint(data['links'].get('your-template-id', {}))
"
```

Replace `your-template-id` with the full prefixed ID
(e.g., `err-missing-api-key`, `tas-task-git-workflow`,
`con-task-cross-linking-strategy`).

## Verify

After connecting your templates:

- [ ] "Want to learn more?" has 3-5 natural language
      prompts
- [ ] Each prompt names the target type in bold
- [ ] Tags are lowercase, hyphenated, and reuse existing
      tags
- [ ] `build_cross_links.py` runs clean
- [ ] Your template appears in `cross_links.json`

## Want to learn more?

- "Why does cross-linking matter for navigation?" -- see
  the **concept** template for the knowledge graph
  design and the 7 link rules
- "Walk me through the full process in detail" -- see
  the **task** template for a complete step-by-step
  guide with verification
- "Show me all the link rules and JSON structure" -- see
  the **reference** template for the full specification

## Related Topics

- **Concept**: Cross-linking strategy -- why cross-links
  create a navigable knowledge graph instead of isolated
  dead-end pages
- **Task**: Cross-linking strategy -- detailed guide
  covering identification, prompts, tags, rebuilding,
  and manual testing
- **Reference**: Cross-linking strategy -- all 7 link
  rules, cross_links.json schema, tag naming conventions,
  and rebuild script phases
