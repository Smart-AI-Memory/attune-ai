---
type: task
name: task-template-migration
tags: [migration, help-system, documentation, templates]
source: developer-guidance
---

# How to Migrate Your Docs to Templates

A step-by-step guide to moving from static documentation
(README, wiki, markdown files) to a structured template-
based help system. This works for any project size, from
a single README to a full docs site.

## Prerequisites

- Existing documentation in any format (markdown, wiki,
  README sections, or even just code comments)
- Access to the template directory structure
- 1-2 hours for a pilot migration; more for a full audit

## Steps

### 1. Audit your current documentation

Before migrating anything, understand what you have. Walk
through every doc and classify it:

```
find docs/ -name "*.md" -type f | sort
ls README.md CONTRIBUTING.md CHANGELOG.md 2>/dev/null
```

Build an inventory with this structure:

| Document | Location | Last updated | Still accurate? | Who reads it? | Content type |
|---|---|---|---|---|---|
| README.md | repo root | 3 months ago | Partially | New users | Mixed (install + concepts + reference) |
| API Guide | docs/api.md | 8 months ago | Probably not | Integrators | Reference |
| Getting Started | wiki/quickstart | 1 year ago | No | Beginners | Task/quickstart |
| FAQ | docs/faq.md | 6 months ago | Mostly | Everyone | Mixed |
| Troubleshooting | docs/troubleshoot.md | 2 months ago | Yes | Users hitting errors | Troubleshooting |

Mark each document as one of:

- **Current** -- accurate and actively useful
- **Stale** -- was accurate but has drifted
- **Obsolete** -- describes features that no longer exist
- **Missing** -- knowledge that exists in people's heads
  but not in any document

### 2. Map content to template types

Each piece of content maps to one or more template types.
Use this decision process:

| If the content... | It becomes a... |
|---|---|
| Explains what something is and why it matters | **Concept** template |
| Walks through doing something step by step | **Task** template |
| Lists options, parameters, configurations, or patterns | **Reference** template |
| Gets someone started in under 5 minutes | **Quickstart** template |
| Answers a specific question | **FAQ** template |
| Describes what to do when something goes wrong | **Troubleshooting** template |
| Warns about a common mistake | **Warning** template |

Most existing documents map to multiple templates. A
README typically contains a quickstart, a concept
overview, and a reference section -- those become three
separate templates.

### 3. Pick your highest-value doc for a pilot

Choose one document to migrate first. Pick the one that:

- Is read most often (README is a good default)
- Is partially stale (so the migration shows immediate
  value)
- Covers a self-contained topic (easier to split)

Do not start with the largest or most complex document.
Start with one that proves the pattern works.

### 4. Split the pilot into templates

Take your chosen document and decompose it into the four
core template types.

**Example: migrating a README section about authentication**

The README says:

> "Our API uses JWT tokens. Set `API_KEY` in your
> environment. Tokens expire after 1 hour. Use the
> `/auth/token` endpoint to get a new one. See the
> full auth guide for OAuth2 support."

This becomes:

| Template | File | Content |
|---|---|---|
| **Concept** | `concepts/task-authentication.md` | What JWT auth is, why we use it, how tokens work, expiration model |
| **Task** | `tasks/task-authentication.md` | Step 1: Get your API key. Step 2: Set the env var. Step 3: Request a token. Step 4: Attach to requests. |
| **Reference** | `references/task-authentication.md` | All auth endpoints, token fields, error codes, OAuth2 config, rate limits |
| **Quickstart** | `quickstarts/task-authentication.md` | "Get authenticated in 3 steps: set API_KEY, hit /auth/token, use the bearer token" |

### 5. Add frontmatter and structure

Every template starts with YAML frontmatter:

```yaml
---
type: concept
name: task-authentication
tags: [auth, security, api, jwt]
source: developer-guidance
---
```

Rules for frontmatter:

| Field | What to put |
|---|---|
| `type` | One of: concept, task, reference, quickstart, faq, troubleshooting, warning, tip |
| `name` | The shared name across all four template types for this topic. Use `task-` prefix for task-category templates. |
| `tags` | 3-6 lowercase tags that describe the content. These drive cross-linking. |
| `source` | Where the content came from: `developer-guidance`, `api-docs`, `user-feedback`, etc. |

### 6. Set up cross-links

Each template should end with a "Want to learn more?"
section that links to its siblings:

```markdown
## Want to learn more?

- Say **"what is authentication?"** for the concept
  overview
- Say **"show me auth patterns"** for the full reference
- Say **"I need to set up auth"** for the quickstart
```

Cross-links are also generated automatically from shared
tags. Two templates with the tag `auth` will be linked
regardless of what you write in the body.

### 7. Test progressive depth

Verify that a user can navigate naturally through the
depth levels:

1. Start at the **quickstart** -- can someone follow it
   cold and get a working result?
2. Move to the **concept** -- does it answer "why?" and
   "how does this work?" without repeating the quickstart?
3. Check the **task** -- does it cover edge cases and
   choices the quickstart skipped?
4. Verify the **reference** -- is it complete enough that
   someone never needs to read source code for this topic?

If any level feels redundant with another, the content
needs redistribution.

### 8. Iterate on the remaining docs

With the pilot complete, repeat for the rest of your
inventory. Prioritize:

1. **Stale docs** -- the migration forces an accuracy
   review
2. **High-traffic docs** -- users benefit immediately
3. **Missing docs** -- knowledge that was never written
   down but should be

Each subsequent migration goes faster because you've
established the pattern.

## Verification

After migrating a document:

- [ ] All four template types exist for the topic
- [ ] Frontmatter has correct type, name, and tags
- [ ] Tags are consistent with related templates
- [ ] Cross-links point to real sibling templates
- [ ] Quickstart works end-to-end for a new reader
- [ ] Concept doesn't duplicate the task steps
- [ ] Reference is comprehensive (no "see the code"
      shortcuts)
- [ ] Old document is either deleted or redirected

## What to do next

| Goal | What to say |
|---|---|
| Check that templates are well-structured | "review my template quality" |
| Generate stubs from code | "generate docs for this module" |
| See all templates in the system | "browse help docs" |
| Set up cross-links automatically | "how does cross-linking work?" |

## Want to learn more?

- Say **"what is template migration?"** for the concept
  overview -- why static docs fail and what templates fix
- Say **"show me the migration reference"** for the
  decision matrix, audit checklist, and restructuring
  patterns
- Say **"I need to move my docs to templates"** for the
  5-minute quickstart starting with one document
- Ask **"/doc-gen"** to generate template stubs from
  existing source code
- Ask **"/help"** to browse the template system and see
  how it all connects
