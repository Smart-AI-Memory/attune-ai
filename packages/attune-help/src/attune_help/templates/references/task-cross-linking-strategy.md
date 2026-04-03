---
type: reference
name: task-cross-linking-strategy
tags: [cross-linking, navigation, help-system, authoring]
source: developer-guidance
---

# Reference: Cross-linking specification

Complete specification of the 7 link rules, the
cross_links.json structure, the tag index, the workflow
map, the rebuild script, the "Want to learn more?"
pattern, and tag naming conventions.

## The 7 link rules

### Rule 1: Error to Warning (bidirectional)

| Property | Value |
|---|---|
| Direction | `err-{slug}` <-> `war-{slug}` |
| Match method | Exact slug name |
| Edge type (error side) | `related_warning` |
| Edge type (warning side) | `related_error` |
| False positive rate | Zero -- exact match only |

**How it works:** Every error template has a slug
derived from the Lessons Learned entry it was generated
from. If a warning template has the same slug, the two
are linked bidirectionally.

**Example:** `err-pre-commit-stash-conflict` links to
`war-pre-commit-stash-conflict`. The error explains what
went wrong; the warning explains what to watch for.

### Rule 2: Skill to Tool (directional)

| Property | Value |
|---|---|
| Direction | `ref-skill-{name}` -> `ref-tool-{name}` |
| Match method | Tool name appears in skill file body |
| Edge type (skill side) | `references_tools` |
| Edge type (tool side) | `referenced_by_skills` |
| False positive rate | Low -- substring match on tool names |

**How it works:** The build script reads each
`plugin/skills/{name}/SKILL.md` file and checks whether
any registered tool name appears in the body text. Each
match creates a directional link from the skill
reference to the tool reference.

**Example:** `ref-skill-security-audit` links to
`ref-tool-security-audit` and `ref-tool-code-review`
because both tool names appear in the security audit
skill file.

### Rule 3: Error to Tip (directional)

| Property | Value |
|---|---|
| Direction | `err-{slug}` -> `tip-{slug}` |
| Match method | 2+ non-stopword title tokens overlap |
| Edge type | `prevented_by` |
| False positive rate | Low-to-moderate -- token overlap can match loosely |

**How it works:** The build script tokenizes the title
of every error and every tip, strips stopwords, and
links any pair that shares 2 or more tokens. This
surfaces tips that help prevent the error condition.

**Example:** An error titled "pre-commit stash conflict
with auto-fix hooks" links to a tip titled "avoid
pre-commit stash conflicts" because "pre-commit",
"stash", and "conflict" overlap.

### Rule 4: Task to Reference (bidirectional)

| Property | Value |
|---|---|
| Direction | `tas-use-{name}` <-> `ref-skill-{name}` |
| Match method | Task prefix `use-` maps to reference prefix `skill-` |
| Edge type (task side) | `related_reference` |
| Edge type (reference side) | `related_task` |
| False positive rate | Zero -- prefix transformation is deterministic |

**How it works:** Skill task templates use the naming
convention `use-{skill-name}`. The build script strips
the `use-` prefix, prepends `skill-`, and looks for a
matching reference template.

**Example:** `tas-use-security-audit` links to
`ref-skill-security-audit`. The task explains how to run
the skill; the reference documents its full API.

### Rule 5: FAQ to Error (bidirectional)

| Property | Value |
|---|---|
| Direction | `faq-{slug}` <-> `err-{slug}` |
| Match method | Exact slug name |
| Edge type (FAQ side) | `related_error` |
| Edge type (error side) | `related_faq` |
| False positive rate | Zero -- exact match only |

**How it works:** Both FAQ and error templates are
generated from the same Lessons Learned entries with
the same slug. If both exist, they are linked
bidirectionally.

**Example:** `faq-windows-ci-encoding` links to
`err-windows-ci-encoding`. The FAQ answers "why does
this happen?"; the error documents the failure mode.

### Rule 6: Note to Reference (directional)

| Property | Value |
|---|---|
| Direction | `not-{slug}` -> `ref-{slug}` |
| Match method | 2+ non-stopword title tokens overlap |
| Edge type | `related_reference` |
| False positive rate | Low-to-moderate -- same as Rule 3 |

**How it works:** Design decision notes are tokenized
and compared against reference titles. Matches surface
the reference that documents the pattern the design
decision produced.

**Example:** A note about "cursor-based pagination
design" links to a reference on "pagination strategies"
because "pagination" and "cursor" (or "cursor-based")
overlap.

### Rule 7: Tag-based (implicit)

| Property | Value |
|---|---|
| Direction | Implicit -- no explicit edges |
| Match method | Shared tag strings |
| Structure | `tag_index` in cross_links.json |
| False positive rate | Depends on tag specificity |

**How it works:** Every template's tags are indexed in
the `tag_index` section of cross_links.json. A search
for tag `security` returns all templates tagged with
`security` regardless of type. This is the catch-all
rule that ensures every template is discoverable.

**Example:** Searching tag `auth` returns
`err-missing-api-key`, `war-api-key-rotation`,
`tip-secrets-management`, `faq-auth-strategies`, and
`ref-skill-security-audit`.

## cross_links.json structure

```json
{
  "version": 1,
  "stats": {
    "total_templates": 605,
    "linked_templates": 557,
    "total_tags": 87
  },
  "links": {
    "err-pre-commit-stash-conflict": {
      "tags": ["pre-commit", "git"],
      "related_warning": ["war-pre-commit-stash-conflict"],
      "related_faq": ["faq-pre-commit-stash-conflict"],
      "prevented_by": ["tip-pre-commit-stash-conflict"]
    },
    "ref-skill-security-audit": {
      "tags": ["security", "audit"],
      "references_tools": [
        "ref-tool-security-audit",
        "ref-tool-code-review"
      ],
      "related_task": ["tas-use-security-audit"]
    }
  },
  "tag_index": {
    "security": [
      "err-path-traversal",
      "ref-skill-security-audit",
      "tas-use-security-audit",
      "tip-validate-file-paths"
    ],
    "pre-commit": [
      "err-pre-commit-stash-conflict",
      "war-pre-commit-stash-conflict",
      "faq-pre-commit-stash-conflict"
    ]
  },
  "workflow_map": {
    "security-audit": [
      "ref-skill-security-audit",
      "ref-tool-security-audit"
    ]
  }
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `version` | `int` | Schema version, currently `1` |
| `stats.total_templates` | `int` | Total templates discovered |
| `stats.linked_templates` | `int` | Templates with at least one link |
| `stats.total_tags` | `int` | Distinct tags across all templates |
| `links` | `dict[str, dict]` | Template ID -> link data |
| `links.*.tags` | `list[str]` | Tags from frontmatter |
| `links.*.related_warning` | `list[str]` | Rule 1 links |
| `links.*.related_error` | `list[str]` | Rule 1 or 5 inverse |
| `links.*.references_tools` | `list[str]` | Rule 2 links |
| `links.*.referenced_by_skills` | `list[str]` | Rule 2 inverse |
| `links.*.prevented_by` | `list[str]` | Rule 3 links |
| `links.*.related_reference` | `list[str]` | Rule 4 or 6 links |
| `links.*.related_task` | `list[str]` | Rule 4 inverse |
| `links.*.related_faq` | `list[str]` | Rule 5 links |
| `tag_index` | `dict[str, list[str]]` | Tag -> template IDs |
| `workflow_map` | `dict[str, list[str]]` | Workflow name -> template IDs |

### Template ID prefixes

| Prefix | Template type |
|---|---|
| `err-` | Error |
| `war-` | Warning |
| `tip-` | Tip |
| `ref-` | Reference |
| `tas-` | Task |
| `faq-` | FAQ |
| `not-` | Note |
| `con-` | Concept |
| `qui-` | Quickstart |
| `com-` | Comparison |
| `tro-` | Troubleshooting |

## The "Want to learn more?" pattern

### Why natural language prompts win

The help system uses intent detection to route user
queries to templates. Natural language prompts in the
"Want to learn more?" section serve double duty: they
guide human readers AND provide matchable phrases for
the intent engine.

| Approach | Human experience | Machine experience |
|---|---|---|
| Markdown link: `[reference](ref-task-api.md)` | Must guess what the link contains from its text | Link text is usually too short for intent matching |
| Natural language: "Show me all status codes" -- see the **reference** | Reads a question they might ask, sees where the answer lives | The full prompt phrase is matchable against user queries |

### Format specification

```markdown
## Want to learn more?

- "Question phrased as the user would ask it" -- see
  the **type** template for a summary of what they
  will find
```

**Rules:**

- Enclose the question in double quotes
- Use a double dash ` -- ` to separate the question
  from the pointer
- Bold the template type (`**concept**`, `**task**`,
  `**reference**`, `**quickstart**`)
- Describe what the reader will find, not just the
  template name
- Include 3-5 prompts per template
- Order from most likely follow-up to least likely

### "Related Topics" section format

```markdown
## Related Topics

- **Type**: Topic name -- one-line description of scope
```

This section is more structured and is parsed by the
build script. Always include it after "Want to learn
more?" for templates that have cross-type siblings.

## Tag naming conventions

| Convention | Good | Bad | Why |
|---|---|---|---|
| Lowercase | `code-review` | `Code-Review` | Tags are compared case-sensitively |
| Hyphenated compounds | `path-validation` | `path_validation` | Consistency with slug naming |
| Topic-focused | `security` | `error-security` | Template type is already encoded in the prefix |
| Singular nouns | `workflow` | `workflows` | Simplifies matching and avoids duplicates |
| 2-4 per template | `[auth, setup]` | `[auth, setup, config, security, api, keys]` | Too many tags dilute discovery precision |
| Reuse before inventing | Check `tag_index` first | Create `authentication` when `auth` exists | Prevents near-duplicate fragmentation |

## How the rebuild script discovers links

The `scripts/build_cross_links.py` script runs these
phases in order:

1. **Scan** -- Walk the templates directory, parse YAML
   frontmatter from every `.md` file, collect name,
   type, tags, and title
2. **Rule 1** -- Match error/warning pairs by slug
3. **Rule 2** -- Read skill SKILL.md files, search for
   tool names in body text
4. **Rule 3** -- Tokenize error and tip titles, link on
   2+ token overlap
5. **Rule 4** -- Map `use-X` tasks to `skill-X`
   references
6. **Rule 5** -- Match FAQ/error pairs by slug
7. **Rule 6** -- Tokenize note and reference titles,
   link on 2+ token overlap
8. **Tag index** -- Build tag -> template_id mappings
9. **Workflow map** -- Map workflow slugs to related
   template IDs
10. **Merge** -- Combine all link dicts, deduplicate
    edges
11. **Write** -- Output `cross_links.json` with stats

The script is idempotent. Running it multiple times
produces the same output given the same input templates.

## Want to learn more?

- "Why does cross-linking matter for user navigation?"
  -- see the **concept** template for the knowledge
  graph design and navigation philosophy
- "Walk me through adding cross-links step by step" --
  see the **task** template for a guided implementation
- "I just need to connect my templates quickly" -- see
  the **quickstart** for a 5-step guide

## Related Topics

- **Concept**: Cross-linking strategy -- why cross-links
  matter, the 7 deterministic rules, and the "Want to
  learn more?" navigation pattern
- **Task**: Cross-linking strategy -- step-by-step guide
  to identifying related templates, writing prompts,
  adding tags, and verifying links
- **Quickstart**: Cross-linking strategy -- 5-step guide
  to connecting templates
