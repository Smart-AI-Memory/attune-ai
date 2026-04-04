# attune-help: Project-Local Help System Spec

**Created:** 2026-04-03
**Updated:** 2026-04-03
**Status:** Complete (v1)
**Builds on:** [attune-help.md](attune-help.md) (runtime
package plan)

## Overview

attune-help is a project-local, self-maintaining help
system that lives in a developer's repo. Developers
author and maintain it using attune-ai within Claude Code.
End users access it via `/coach` or natural language.

### System Roles

| Component | Role |
|-----------|------|
| **attune-ai** | Authoring toolkit — bootstraps, generates, and maintains help content |
| **Claude Code** | Runtime environment — where attune-ai operates |
| **attune-help** | The output — a living help/knowledge base tailored to the project |

### Design Principles

- Help lives in the repo, versioned with the code
- Content is per-feature, not per-file
- Self-maintaining via commit hooks (primary) with
  manual refresh as escape hatch
- Hybrid authoring — agent seeds, developer curates
- Progressive depth — concept, task, reference

### `.gitignore` Strategy

Generated templates SHOULD be committed — they are the
help content and must be available to all contributors
without running generation. The `.help/` directory is
part of the repo, not a build artifact.

What to `.gitignore`:

- Nothing by default — commit everything in `.help/`
- If a project wants to regenerate on CI instead:
  `.help/templates/` can be gitignored and regenerated
  in a CI step, but `.help/features.yaml` must always
  be tracked

---

## Content Model

### Directory Structure

```
.help/
  features.yaml          # Feature manifest
  templates/
    authentication/
      concept.md         # What is auth in this project?
      task.md            # How to add/modify auth
      reference.md       # API surface, config options
    payments/
      concept.md
      task.md
      reference.md
    ...
```

### Feature Manifest (`.help/features.yaml`)

Maps features to the source files that define them.
This is the bridge between code changes and help
updates.

```yaml
# .help/features.yaml
version: 1

features:
  authentication:
    description: User auth and session management
    files:
      - src/auth/**
      - src/middleware/session.py
      - config/auth.yaml
    tags: [security, users]

  payments:
    description: Stripe integration and billing
    files:
      - src/billing/**
      - src/webhooks/stripe.py
    tags: [billing, stripe]

  api:
    description: REST API endpoints and versioning
    files:
      - src/api/**
      - src/serializers/**
      - openapi.yaml
    tags: [api, rest]
```

**Key fields:**

- `description` — one-line summary (used by the help
  engine for topic resolution)
- `files` — glob patterns matching source files that
  define this feature
- `tags` — for cross-referencing and discovery

### Template Format

Each feature has up to 3 depth levels, matching the
existing progressive depth model:

| Level | File | Purpose |
|-------|------|---------|
| 0 | `concept.md` | What is this? Why does it exist? |
| 1 | `task.md` | How do I use/modify this? |
| 2 | `reference.md` | Full API, config, edge cases |

Templates are standard markdown. Frontmatter tracks
generation metadata:

```yaml
---
feature: authentication
depth: concept
generated_at: 2026-04-03T10:00:00Z
source_hash: abc123
status: generated  # generated | reviewed | manual
---
```

- `source_hash` — SHA-256 of the concatenated source
  files at generation time. Used by the staleness
  detector.
- `status` — `generated` (agent-created, unreviewed),
  `reviewed` (developer approved), `manual`
  (hand-written, agent should not overwrite)

---

## Bootstrapping (`/coach init`)

First-time setup for a project with no help content.

### Flow

1. User runs `/coach init`
2. Agent scans the project via `scan_project()`:
   - Directory structure and naming conventions
   - README, entry points, config files
   - Public API surface (exported functions, classes)
   - Existing docs (if any)
3. Agent proposes a draft `features.yaml` with:
   - Suggested feature names
   - File glob mappings
   - Descriptions
4. User reviews and edits the manifest (Socratic —
   agent asks clarifying questions)
5. Agent generates initial templates for each feature
   at all 3 depth levels via `generate_feature_templates()`
6. Templates committed to `.help/`

### Discovery Heuristics

The agent identifies features by looking for:

- Top-level source directories (e.g., `src/auth/` →
  "authentication")
- Entry points (CLI commands, API routers, main files)
- Config files (suggesting configurable subsystems)
- Test directories (mirror of feature structure)
- README sections (often map to features)
- Package exports (`__init__.py`, `index.ts`)

The agent should **propose, not assume**. Every
suggested feature goes through the user for
confirmation.

---

## Self-Maintenance (Option 1: On Commit)

### Hook Design

A commit hook detects which features are affected by
the changed files and regenerates their templates.

**Trigger:** Post-commit or pre-push hook (not
pre-commit — help generation is too slow for the
commit loop)

**Logic (implemented in `maintenance.run_hook()`):**

```
1. Get list of changed files from the commit
2. For each feature in features.yaml:
     Match changed files against feature's file globs
3. For each affected feature:
     Compute new source_hash from current source files
     If source_hash != template's source_hash:
       Regenerate templates (concept, task, reference)
       Update source_hash in frontmatter
4. If any templates changed:
     Create a follow-up commit (see Decisions below)
```

### Smart Filtering

Not every file change warrants a help update. The hook
should prioritize changes to:

- Public API surface (function signatures, class
  interfaces, exports)
- Configuration (new options, changed defaults)
- New files (new capability added)
- Deleted files (capability removed)
- Structural changes (moved, renamed, reorganized)

Lower priority (may skip):

- Internal implementation details (private methods,
  refactors that don't change behavior)
- Test-only changes
- Comment/docstring-only changes (unless the help
  was generated from docstrings)

### Respecting Manual Content

Templates with `status: manual` are **never
overwritten** by the hook. The agent may flag them as
potentially stale (source_hash mismatch) but leaves
the content untouched. The developer decides via
option 2.

---

## Manual Maintenance (Option 2: On Demand)

### Commands (via `/coach`)

| Command | What It Does |
|---------|-------------|
| `/coach init` | Bootstrap — scan project, propose manifest, generate templates |
| `/coach maintain` | Full refresh — check all features for staleness, regenerate as needed |
| `/coach update <feature>` | Targeted — regenerate templates for one feature |
| `/coach add <feature>` | Add a new feature to the manifest and generate its templates |
| `/coach status` | Show staleness report — which features are current vs stale |

**Note:** `/help` is a Claude Code built-in. `/init` is
also reserved. `/coach` avoids both collisions.

### `/coach maintain` Flow

1. For each feature in the manifest:
   - Compute current source_hash via `compute_source_hash()`
   - Compare against template's stored source_hash
   - Flag stale features
2. Present staleness report to user via `format_status_report()`
3. Ask: regenerate all stale? Or select specific ones?
4. Regenerate selected features via `generate_feature_templates()`
5. Show diff of what changed (for review)

---

## Access Model

Users access help through Claude Code via:

### Slash Commands

| Command | Behavior |
|---------|----------|
| `/coach <topic>` | Look up topic, show at current depth level |
| `/coach <topic> concept` | Force specific depth |
| `/coach topics` | List all features in the manifest |

### Natural Language

- "How does authentication work?" → matches
  `authentication` feature → shows concept
- "Tell me more" → increments depth on last topic
- "How do I add a new payment method?" → matches
  `payments` feature → shows task level

### Topic Resolution

1. Exact match against feature names in manifest
   via `resolve_topic()`
2. Fuzzy match against feature descriptions and tags
3. If ambiguous, ask the user to clarify (Socratic)

### Progressive Depth (Session State)

Same model as existing `help/session.py`:

- First access to a topic → concept (depth 0)
- Same topic again → task (depth 1)
- Same topic again → reference (depth 2)
- Different topic → resets to concept
- Session TTL: 4 hours

---

## Generation

### What the Agent Reads

When generating templates for a feature, the agent
reads:

1. All source files matching the feature's globs
2. Related test files (for usage examples)
3. Existing docs that reference the feature
4. The feature's description from the manifest
5. Adjacent feature templates (for cross-linking)

### Template Quality

Generated templates should:

- Use the project's terminology (extracted from source)
- Include real code examples (from the actual codebase)
- Cross-link to related features
- Be accurate to the current code (not aspirational)
- Follow progressive depth conventions:
  - Concept: why it exists, mental model, when to use
  - Task: step-by-step, common modifications, gotchas
  - Reference: full API, config options, edge cases

---

## Integration with attune-ai

### Existing Infrastructure Used

| Component | How It's Used |
|-----------|--------------|
| Progressive depth (`help/session.py`) | Session state for depth tracking |
| Templates (`help/templates/`) | Template format and rendering |
| Plugin skills | `/coach` skill routes all help commands |
| Hooks | `help_freshness_check.py` (session start), `help_on_error.py` (Bash failures) |

### New Components (Implemented)

| Component | Purpose | Status |
|-----------|---------|--------|

| `help/manifest.py` | Parse and query `features.yaml` | Done |
| `help/staleness.py` | SHA-256 hash comparison, staleness detection | Done |
| `help/generator.py` | Template generation from source files | Done |
| `help/bootstrap.py` | Project scanning and manifest proposal | Done |
| `help/maintenance.py` | Hook logic — diff, filter, regenerate | Done |

---

## Decisions (Resolved Open Questions)

1. **Commit strategy for hook updates** — **Follow-up
   commit.** Amending rewrites history and conflicts
   with GPG signing, pre-commit hooks, and shared
   branches. A follow-up commit is clean and safe.
   The maintenance module creates a separate commit
   with help template updates.

2. **Generation cost** — **AST-based for v1, no LLM
   calls.** The current generator extracts public
   API info via Python's `ast` module and renders
   structured templates without any LLM calls. This
   is free, fast, and deterministic. LLM-enriched
   generation (better prose, examples from tests) is
   a v2 enhancement that can use the Batch API for
   50% savings.

3. **Multi-language support** — **Python only for v1.**
   The manifest's file globs are language-agnostic
   (works for any file type), but `generator.py`'s
   `_extract_source_info()` only parses Python AST.
   Non-Python files are counted and listed but not
   parsed for API surface. Adding TypeScript/Go/Rust
   parsers is a v2 task — the generator has a clean
   `_SourceInfo` dataclass that other parsers can
   populate.

4. **Monorepo features** — **One manifest, multiple
   glob roots.** A feature's `files:` list already
   supports globs across packages:

   ```yaml
   payments:
     files:
       - packages/billing/**
       - packages/webhooks/stripe/**
       - shared/models/payment.py
   ```

   No need for per-package manifests in v1. If
   monorepo scale demands it, v2 can support
   `include:` directives to compose manifests.

5. **Template versioning** — **Frontmatter-based.**
   Each template already has `generated_at` and
   `source_hash` in its YAML frontmatter. If the
   template format changes, a migration script reads
   frontmatter, detects the old format, and
   regenerates. The `version: 1` field in
   `features.yaml` gates manifest schema migrations
   separately.

---

## Non-Goals (for v1)

- External help hosting (web, API)
- Multi-user session state (shared teams)
- Real-time collaboration on help content
- Help analytics (which topics are accessed most)
- Internationalization / translation
- LLM-enriched generation (v2)
- Non-Python AST parsing (v2)

---

## Success Criteria

1. A developer can run `/coach init` on an existing
   project and get a working help system in < 5
   minutes
2. Help content stays current with code changes
   without manual intervention (via commit hook)
3. Developers can hand-write templates that the
   system respects and doesn't overwrite
4. End users can access help via natural language
   or slash commands with progressive depth
5. The entire system lives in the project repo —
   no external services required

---

## Next Steps

- [x] Design `features.yaml` schema (v1)
- [x] Implement `help/manifest.py` (parser + query)
- [x] Implement `help/staleness.py` (hash comparison)
- [x] Implement `help/bootstrap.py` (project scanning)
- [x] Implement `help/generator.py` (template gen)
- [x] Implement `help/maintenance.py` (hook logic)
- [x] Wire exports through `help/engine.py` facade
- [x] Build prototype on attune-ai's own codebase
  (dogfood — 14 features, 42 templates)
- [x] Write tests for manifest, staleness, bootstrap,
  generator, maintenance (62 tests, 0.25s)
- [x] Add MCP tools: `help_init`, `help_status`,
  `help_update` (schemas + handlers)
- [x] Wire `/coach init` via `help_init` MCP tool
  (scan → Socratic review → accept)
- [x] Wire `/coach status` via `help_status` MCP tool
- [x] Wire `/coach maintain` via `help_update` MCP tool
- [x] Add post-commit hook
  (`help_post_commit.py` → `maintenance.run_hook()`)
- [x] Update tool count test (38 → 41)
