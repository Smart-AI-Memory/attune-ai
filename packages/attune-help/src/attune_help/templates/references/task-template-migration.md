---
type: reference
name: task-template-migration
tags: [migration, help-system, documentation, templates]
source: developer-guidance
---

# Reference: Template Migration Patterns

Complete reference for migrating static documentation to
a template-based help system. Includes the decision
matrix, audit checklist, restructuring patterns, frontmatter
mapping, and common mistakes.

## Migration decision matrix

Use this table to determine which template type each
piece of existing content should become.

| Source content type | Primary template | Secondary templates | Notes |
|---|---|---|---|
| README overview section | Concept | Quickstart (if it has install steps) | Split the README -- don't convert it as one unit |
| README install instructions | Quickstart | Task (if multi-step) | Keep the quickstart under 5 minutes |
| API endpoint docs | Reference | Task (for common workflows) | One reference per resource, tasks for multi-step flows |
| Getting started guide | Task | Quickstart (extract the shortest path) | The guide is the task; the quickstart is the happy path only |
| FAQ page | Individual FAQ templates | Concept (if answers are conceptual) | One FAQ per question, not one file for all questions |
| Troubleshooting guide | Troubleshooting + Error templates | Reference (for error code tables) | One template per error or symptom |
| Architecture overview | Concept | Reference (for component details) | Keep the concept high-level; details go in reference |
| Configuration reference | Reference | Quickstart (minimal config) | Reference has every option; quickstart has the three that matter |
| Tutorial | Task | Concept (background) + Quickstart (shortcut) | Tutorials are tasks with extra context; split the context out |
| Changelog | None (keep as-is) | -- | Changelogs are not help content |
| Contributing guide | Task | Reference (for style rules) | "How to contribute" is a task; coding standards are a reference |
| Code comments | Concept or Reference | -- | Extract if the comment explains something users need to know |

## Documentation audit checklist

Run this checklist before starting a migration to
understand the scope and priority.

### Inventory

- [ ] List every documentation file in the project
- [ ] Record location, format, and last-modified date
- [ ] Note which files are linked from the README or
      navigation
- [ ] Identify orphaned docs (exist but nothing links to
      them)

### Accuracy assessment

- [ ] Mark each doc as current, stale, or obsolete
- [ ] For stale docs: note what changed since the last
      update
- [ ] For obsolete docs: decide whether to delete or
      archive
- [ ] Identify knowledge gaps (things that should be
      documented but aren't)

### Priority ranking

| Priority | Criteria |
|---|---|
| **P0 -- migrate first** | Read by most users, currently stale, high business value |
| **P1 -- migrate soon** | Read regularly, mostly accurate, would benefit from structure |
| **P2 -- migrate later** | Rarely read, accurate enough, low urgency |
| **P3 -- skip or delete** | Obsolete, duplicated, or not worth maintaining |

### Coverage check

- [ ] Every user-facing feature has at least a quickstart
- [ ] Every complex feature has all four template types
- [ ] Every error the user can encounter has a
      troubleshooting template
- [ ] Cross-links connect related topics

## Content restructuring patterns

### Long document to multi-level templates

A single long document (50+ lines) typically contains
content at multiple depth levels. Split it:

| Section of the long doc | Becomes |
|---|---|
| Opening paragraph explaining "what" and "why" | Concept template, first two sections |
| Step-by-step instructions | Task template |
| Configuration tables, parameter lists | Reference template |
| "Quick setup" or "TL;DR" section | Quickstart template |
| Warnings or gotchas scattered throughout | Warning templates (one per warning) |
| FAQ section at the bottom | Individual FAQ templates |

**Example**: A 200-line `AUTHENTICATION.md` becomes:

- `concepts/task-authentication.md` (40 lines)
- `tasks/task-authentication.md` (80 lines)
- `references/task-authentication.md` (100 lines)
- `quickstarts/task-authentication.md` (35 lines)
- `warnings/auth-token-expiry.md` (15 lines)
- `faqs/auth-refresh-token.md` (20 lines)

Total lines increase, but each file is self-contained
and serves one reader need.

### FAQ page to individual templates

Static FAQ pages bundle unrelated questions into one
file. Split them:

| Before | After |
|---|---|
| `docs/faq.md` with 20 questions | 20 individual files in `faqs/` |
| Questions sorted by "when we added them" | Questions tagged by topic, surfaced by relevance |
| Reader scrolls through everything | Reader gets the one FAQ that matches their question |

Each FAQ template has frontmatter tags that connect it
to related concepts, tasks, and references.

### Troubleshooting guide to error templates

A troubleshooting guide organized by symptom becomes
individual error and troubleshooting templates:

| Before | After |
|---|---|
| One file: "Common errors and fixes" | `errors/connection-timeout.md` + `troubleshooting/connection-timeout.md` |
| Errors mixed with explanations | Error template has the fix; troubleshooting template has the diagnosis steps |
| Reader searches within one long file | System routes reader to the right template by error message or symptom |

## Frontmatter mapping from common doc formats

### From MkDocs (mkdocs.yml + markdown)

| MkDocs element | Template frontmatter |
|---|---|
| `title:` in YAML header | First `#` heading in template body |
| `tags:` in YAML header | `tags:` in template frontmatter |
| Navigation path in mkdocs.yml | Not needed -- tags and cross-links handle routing |
| `hide: [toc]` | Not applicable -- template type controls depth |
| Admonitions (`!!! note`) | Separate warning/tip templates, or inline text |

### From Sphinx (RST files)

| Sphinx element | Template frontmatter |
|---|---|
| `:title:` directive | First `#` heading in template body |
| `:tags:` metadata | `tags:` in template frontmatter |
| `.. toctree::` | Cross-links in "Want to learn more?" section |
| `.. warning::` directives | Separate warning templates |
| `:ref:` cross-references | Natural language prompts ("say X for...") |
| `.. automodule::` | Not needed -- `/doc-gen` generates from source |

### From Docusaurus (MDX files)

| Docusaurus element | Template frontmatter |
|---|---|
| `sidebar_label:` | First `#` heading |
| `tags:` | `tags:` in frontmatter |
| `sidebar_position:` | Not needed -- no fixed navigation order |
| MDX components (`<Tabs>`, `<CodeBlock>`) | Standard markdown (fenced code blocks) |
| `import` statements | Not applicable |

## Handling redirects from old doc URLs

When migrating from a docs site with established URLs,
prevent broken links:

| Scenario | Redirect strategy |
|---|---|
| MkDocs site with known URLs | Add `redirects` plugin entries in mkdocs.yml |
| GitHub wiki pages | Add a note at the top of the old page pointing to the new location |
| README sections with anchor links | Keep anchors in README that link to template entry points |
| Sphinx docs on ReadTheDocs | Use `redirects.yaml` in the RTD config |
| No existing URLs (internal docs) | No redirect needed -- just delete the old files |

## Measuring migration success

Track these metrics to know whether the migration is
working:

| Metric | How to measure | Target |
|---|---|---|
| **Coverage** | Templates exist / topics that need them | 100% of user-facing features |
| **Staleness rate** | Templates flagged stale / total templates | Under 10% at any time |
| **Depth completeness** | Topics with all 4 template types / total topics | Above 80% |
| **Cross-link density** | Average cross-links per template | 3-5 per template |
| **Orphan rate** | Templates with zero inbound links | Under 5% |
| **Usage distribution** | Quickstart views / total views | 40-60% (healthy entry point) |
| **Escalation rate** | Users who go from quickstart to task or reference | 20-30% (shows depth is useful) |

## Common migration mistakes

| Mistake | What happens | How to avoid it |
|---|---|---|
| **Migrating everything at once** | Burnout, inconsistent quality, half-finished templates | Start with one pilot doc; iterate |
| **Copying content instead of restructuring** | Four templates that say the same thing at different lengths | Each type serves a different reader need -- rewrite, don't trim |
| **Skipping the audit** | Migrating obsolete docs into shiny new templates | Audit first; delete what's obsolete before migrating |
| **Tags that are too broad** | Everything tagged `docs` links to everything else | Use 3-6 specific tags per template |
| **Tags that are too narrow** | No cross-links generated; templates are isolated | Share at least 2 tags with related templates |
| **Forgetting the quickstart** | Users have no fast entry point; they bounce | Every topic needs a quickstart, even if it's short |
| **Reference that says "see the code"** | Reference template is incomplete; defeats the purpose | If it's worth a reference, it's worth writing the details |
| **No cross-links between siblings** | User reads the concept but doesn't know the task exists | Always include "Want to learn more?" with sibling links |
| **Keeping the old doc alongside the new templates** | Two sources of truth; one inevitably drifts | Delete or redirect the old doc after migration |
| **Over-engineering frontmatter** | Spending time on metadata instead of content | Start with type, name, tags, source. Add more only when needed. |

## Template naming conventions

| Template type | Directory | File name pattern | Example |
|---|---|---|---|
| Concept | `concepts/` | `task-{topic}.md` | `concepts/task-template-migration.md` |
| Task | `tasks/` | `task-{topic}.md` | `tasks/task-template-migration.md` |
| Reference | `references/` | `task-{topic}.md` | `references/task-template-migration.md` |
| Quickstart | `quickstarts/` | `task-{topic}.md` | `quickstarts/task-template-migration.md` |
| FAQ | `faqs/` | `{short-question}.md` | `faqs/auth-token-expired.md` |
| Error | `errors/` | `{error-name}.md` | `errors/connection-timeout.md` |
| Warning | `warnings/` | `{warning-topic}.md` | `warnings/breaking-change.md` |
| Tip | `tips/` | `{tip-topic}.md` | `tips/cache-invalidation.md` |

The `task-` prefix groups the four core template types
for a given topic. All four files share the same name
so the system can find siblings automatically.

## Cross-link identifiers

Templates are referenced in `cross_links.json` using
prefixed identifiers:

| Prefix | Template type | Example ID |
|---|---|---|
| `con-` | Concept | `con-task-template-migration` |
| `tas-` | Task | `tas-task-template-migration` |
| `ref-` | Reference | `ref-task-template-migration` |
| `qui-` | Quickstart | `qui-task-template-migration` |

## Want to learn more?

- Say **"what is template migration?"** for the concept
  overview -- why static docs fail and what you gain from
  templates
- Say **"walk me through migrating my docs"** for the
  step-by-step task guide
- Say **"I need to move my docs to templates"** for the
  5-minute quickstart
- Run `/doc-gen` to auto-generate template stubs from
  source code
- Run `/help` to browse the full template system
- Ask **"how does cross-linking work?"** for the
  cross-linking concept

## Related Topics

- **Concept**: Template migration -- why static docs fail,
  what templates fix, cost/benefit analysis
- **Task**: Template migration -- step-by-step migration
  guide with audit, split, and verification
- **Quickstart**: Template migration -- move your first
  doc in 5 minutes
