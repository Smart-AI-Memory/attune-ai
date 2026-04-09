# Attune Two-Marketplace Split

**Created:** 2026-04-08
**Updated:** 2026-04-09 (Phase 1 steps 2, 5 executed — see execution log)
**Source:** /brainstorm session
**Status:** Phase 1 in flight. Steps 2 (tags) and 5 (new repo) done. Steps 1, 3, 4, 6, 7, 8, 9 pending or skipped — see execution log below.

## Phase 1 execution log (2026-04-09)

- **PR #140 merged** (squash `96a04c96`): brought
  `packages/attune-author/plugin/` and
  `packages/attune-help/plugin/` to main along with the
  v5.9.0/v5.10.0 release backport.
- **Step 2 — per-plugin tags:** `attune-help-v0.3.0` and
  `attune-author-v0.1.0` created and pushed at `96a04c96`.
- **Step 5 — attune-docs repo:** created at
  [Smart-AI-Memory/attune-docs](https://github.com/Smart-AI-Memory/attune-docs),
  initialized **private**, contents: README, LICENSE
  (Apache 2.0), .gitignore,
  `.claude-plugin/marketplace.json` with `git-subdir` refs
  pinned to the step 2 tags. Flip to public when announcing.
- **Step 6 — slim attune-ai marketplace.json:** **mostly
  already done.** Main never contained the bundled
  attune-help/attune-author entries (the uncommitted additions
  were discarded before PR #140). Still pending: add the
  cross-promotion hook to the attune-ai plugin description
  (see draft at /tmp/attune-docs-scratch/step6-attune-ai-marketplace-patch.md
  or regenerate it from the "Draft repo copy" section below).
- **Step 7 — migration banner:** **skipped** — the bundle
  was never public, no users to migrate.
- **Steps 1 and 8 — sandbox + funnel tests:** **pending.**
  Both require a clean Claude Code session running in a second
  instance; cannot be run from within the current session.
  Manual test script drafted at
  /tmp/attune-docs-scratch/manual-test-plan.md — run from a
  clean environment when ready.
- **Step 9 — publish and announce:** **blocked** on step 8.

### Remaining prerequisites before making attune-docs public

1. Run the Step 1 sandbox test and document the duplicate-
   plugin behavior in Open Question 8 below.
2. Run the Step 8 three-funnel test and record results.
3. Apply the Step 6 cross-promotion hook to attune-ai's
   `.claude-plugin/marketplace.json` description.
4. Flip `Smart-AI-Memory/attune-docs` from private to public.
5. Announce the two-marketplace structure.

## Problem

The current bundled marketplace structure at
[.claude-plugin/marketplace.json](../../.claude-plugin/marketplace.json)
forces three distinct user funnels — dev workflows, help
reader, and help builder — through a single
`claude plugin marketplace add Smart-AI-Memory/attune-ai`
entry point. This dilutes the marketing story for both the
developer tool (attune-ai) and the help platform
(attune-help + attune-author), and anticipates friction for
new users who want to adopt attune-help and attune-author
together to provide context-sensitive help inside their own
AI products.

The marketplace structure is downstream of a bigger issue:
Smart AI Memory has two distinct product lines, not one
suite with three sub-plugins.

## Goals

### Must-haves

- Independent release cadence for all three plugins
  (attune-ai, attune-help, attune-author) — each can ship a
  fix or feature without rev'ing the others
- Frictionless install for funnel 3 (help builder) — one
  marketplace add, both plugins surfaced from the same place
- Clean marketing story: attune-ai positioned as a
  developer workflow tool for building AI-powered products;
  the help platform positioned as the tool for authoring
  and delivering context-sensitive help inside those
  products
- All three funnels work cleanly without cross-contamination

### Nice-to-haves

- Cross-promotion between the two marketplaces for
  discovery (e.g. "if you're using attune-ai to build an AI
  app, check out attune-docs for its help system")
- Shared CI/tooling between repos where it does not
  compromise release independence

## End State

**Two repos, two marketplaces, three independently-shippable plugins.**

| Repo | Marketplace | Plugins | Story |
|------|-------------|---------|-------|
| `Smart-AI-Memory/attune-ai` (current, slimmed) | attune-ai | attune-ai | Developer workflows for building AI-powered products |
| `Smart-AI-Memory/attune-docs` (new) | attune-docs | attune-help + attune-author | Author & deliver context-sensitive help inside AI products |

### Funnel experience

| Funnel | User type | Install flow |
|--------|-----------|--------------|
| 1 | Developer building an AI product | `marketplace add Smart-AI-Memory/attune-ai` -> install attune-ai |
| 2 | Downstream consumer reading `.help/` templates shipped by someone else | `marketplace add Smart-AI-Memory/attune-docs` -> install attune-help alone (no AI keys needed) |
| 3 | Builder shipping help content with their AI app | `marketplace add Smart-AI-Memory/attune-docs` -> install both attune-help and attune-author from the same place |

### Success criteria

- Each of the three plugins has its own version and ships
  on its own cadence (Phase 2 fully, Phase 1 via git-tag
  discipline)
- The current repo's README and marketplace description
  refocus on the dev-tool story with no help-platform
  language
- The new repo's README and landing page tell the
  help-platform story without dev-workflow
  cross-contamination
- A new user in funnel 3 can get both attune-help and
  attune-author installed in under 60 seconds from a clean
  Claude Code environment

## Research findings (2026-04-08)

Key constraints and capabilities surfaced via the
Claude Code plugin marketplace research:

### 1. marketplace.json supports five source types

Authoritative source:
[plugin-marketplaces.md](https://code.claude.com/docs/en/plugin-marketplaces.md).
Plugins can be referenced from:

- **Relative path** — `"./plugins/my-plugin"` (same repo)
- **GitHub** — `{"source": "github", "repo": "owner/repo"}`
- **Git URL** — `{"source": "url", "url": "https://...git"}`
- **Git subdirectory** — `{"source": "git-subdir", "url": "...", "path": "..."}`
- **npm package** — `{"source": "npm", "package": "@org/plugin"}`

**Critical implication:** a marketplace in Repo A can
list plugins physically located in Repo B via `git-subdir`
or `github` source types. Raw external URLs are NOT
supported.

### 2. git-subdir and github sources support ref pinning

Both accept optional `ref` (branch or tag name) and
`sha` (40-character commit SHA) fields:

```json
{
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/Smart-AI-Memory/attune-ai.git",
    "path": "packages/attune-help/plugin",
    "ref": "attune-help-v0.3.0"
  }
}
```

Users receive the exact tagged release, never drift to
`main`. Phase 1 is production-safe.

### 3. Update flow is fully manual, two-step

After a plugin is updated (new tag, new commit, new
marketplace.json edit):

1. User runs `/plugin marketplace update <name>` to pull
   the new marketplace manifest
2. User runs `/plugin install <plugin>@<marketplace>` to
   upgrade the installed plugin

**No auto-polling, no notifications.** Release
announcements must include both commands explicitly.

**Version detection uses the plugin's own `plugin.json`
`version` field** — NOT marketplace.json, NOT the git tag.
If two tags ship with the same `plugin.json` version,
Claude Code treats them as identical and skips the update.
**Every release must bump `plugin.json` version.**

### 4. Plugin identity is namespaced by marketplace

Install syntax requires explicit marketplace:
`/plugin install attune-help@attune-docs`. Each
marketplace caches separately. Cross-marketplace duplicate
handling at the runtime skill-trigger level is **a
documentation blind spot** and must be verified via
sandbox test before Phase 1 launch.

### 5. Local dev workflow

- `/plugin marketplace add ./local-dir` — add from local
  filesystem path (iterate without pushing)
- `claude --plugin-dir ./plugin` — load plugin directly
  without a marketplace
- BUT: `git-subdir` sources always resolve to remote git
  repos; they cannot be locally overridden
- **Dev workflow:** during Phase 1 setup, prototype the
  wrapper marketplace using relative paths against a local
  clone of attune-ai, then rewrite to `git-subdir` before
  pushing to the new repo

## Approach — two-phase execution

### Phase 1 — Thin wrapper marketplace (committed)

**Cost:** days, not weeks. **Reversibility:** high. **Risk:** low.

Create `Smart-AI-Memory/attune-docs` as a minimal wrapper
repo containing only a README and a marketplace.json. The
marketplace uses `git-subdir` references to pin plugins
that still physically live in the current `attune-ai`
repo.

**What ships in Phase 1:**

- New repo: `Smart-AI-Memory/attune-docs`
  - `README.md` — audience-forward copy from the
    "Draft repo copy" section below
  - `LICENSE` — Apache 2.0 (matches attune-ai)
  - `.claude-plugin/marketplace.json` — lists attune-help
    and attune-author via `git-subdir` sources with `ref`
    pinning to tagged versions in attune-ai
- Slimmed marketplace.json in current `attune-ai` repo —
  lists only the `attune-ai` plugin with a cross-promotion
  hook in the description pointing users at
  `Smart-AI-Memory/attune-docs`
- Migration banner in current `attune-ai` README —
  short paragraph directing existing bundled-install users
  to the new marketplace location
- New per-plugin git tags on the current `attune-ai` repo
  — e.g., `attune-help-v0.3.0`, `attune-author-v0.1.0`
  — so the wrapper marketplace can pin refs

**What Phase 1 does NOT change:**

- Plugin code stays in
  [packages/attune-help/](../../packages/attune-help/) and
  [packages/attune-author/](../../packages/attune-author/)
- PyPI packages (`attune-help`, `attune-author`) continue
  to release from the current repo's CI
- `src/attune/` and the `attune-ai` plugin code remain
  untouched
- No git history surgery, no new CI setup, no new PyPI
  trusted publishing

**If Phase 1 fails or the two-marketplace UX proves
wrong:** delete the new repo, revert the slimmed
marketplace.json, delete the migration banner. Roughly
one commit to undo everything.

### Phase 2 — Full extraction (conditional, later)

**Cost:** weeks. **Reversibility:** low. **Risk:** higher.

Executed **only if** Phase 1 validates the two-marketplace
UX as an adoption win. Phase 2 does the full work to get
true independent release cadence, true multi-platform
separation, and clean per-repo CI:

- Extract `packages/attune-help/` and
  `packages/attune-author/` into the attune-docs repo with
  git history preserved (git subtree split or git
  filter-repo)
- Stand up new CI, pre-commit, release workflow, PyPI
  trusted publishing in the attune-docs repo
- Swap the attune-docs marketplace.json from `git-subdir`
  sources to relative paths (plugins are now local to the
  repo)
- Delete `packages/` from the current attune-ai repo (or
  leave a tombstone README pointing to the new repo)
- Decide and implement what is shared between the two
  repos (CI reusable workflows, docs theme, etc.)
- Update the attune-docs landing page / website content
  to tell the help-platform story with full depth

**Decision gate:** Phase 2 launches only after Phase 1 has
been live for a meaningful period and shows that (a)
funnel 3 adoption actually happens and (b) the release
cadence friction is real enough to justify the extraction
cost.

## Phase 1 execution plan

1. **Sandbox test the duplicate-plugin scenario.** On a
   clean Claude Code environment, add the current
   `Smart-AI-Memory/attune-ai` marketplace and install
   `attune-help@attune-ai`. Then create a throwaway test
   marketplace that also lists `attune-help` and try to
   install `attune-help@<test-marketplace>`. Observe:
   does it error, warn, install twice, or trigger
   duplicate skills? Document the behavior. This result
   determines whether the slim-and-publish order matters.

2. **Tag per-plugin versions on the current repo.** Create
   git tags `attune-help-v0.3.0` and
   `attune-author-v0.1.0` on the current `attune-ai` repo
   pointing at the latest commits where those plugins'
   `plugin.json` files declare those versions. These tags
   are what the wrapper marketplace pins to via
   `git-subdir` `ref`.

3. **Prototype the wrapper marketplace locally.** Create a
   local scratch directory with a
   `.claude-plugin/marketplace.json` using RELATIVE paths
   pointing at `packages/attune-help/plugin` and
   `packages/attune-author/plugin` in a local clone of
   attune-ai. Run `/plugin marketplace add ./scratch-dir`
   in a clean Claude Code environment and verify both
   plugins install cleanly and their skills trigger as
   expected.

4. **Rewrite the scratch marketplace.json to use
   `git-subdir` sources.** Swap the relative paths for
   `git-subdir` references pinned to the tags from step 2.
   Test again locally — the marketplace should still add
   and install correctly, but now fetching from the remote
   repo via the sparse checkout.

5. **Create the `Smart-AI-Memory/attune-docs` GitHub
   repository.** Apache 2.0 license. Push:
   - `README.md` from the "Draft repo copy" section
   - `LICENSE` (Apache 2.0)
   - `.claude-plugin/marketplace.json` (tested version
     from step 4)
   - `.gitignore` (minimal — `.DS_Store`, etc.)

6. **Slim the current `attune-ai` marketplace.json.**
   Remove the `attune-help` and `attune-author` entries
   from
   [.claude-plugin/marketplace.json](../../.claude-plugin/marketplace.json);
   update the `attune-ai` plugin description to include
   the cross-promotion hook from the "Draft repo copy"
   section.

7. **Add a migration banner to the current `attune-ai`
   README.** Short paragraph near the top: "attune-help
   and attune-author have moved to
   `Smart-AI-Memory/attune-docs`. If you previously
   installed them via this marketplace, see the migration
   guide below."

8. **End-to-end test all three funnels** from a clean
   Claude Code environment:
   - Funnel 1: add attune-ai marketplace, install
     attune-ai, verify skills trigger
   - Funnel 2: add attune-docs marketplace, install
     attune-help alone, verify lookup commands work
     without AI keys
   - Funnel 3: add attune-docs marketplace, install both
     attune-help and attune-author, verify both work
     together

9. **Publish and announce.** Push the slimmed
   marketplace.json and migration banner to attune-ai main.
   Announce the split with explicit two-command upgrade
   instructions for existing users.

## Phase 1 release playbook

When shipping a new version of attune-help or attune-author
during Phase 1:

1. Bump the `version` field in the plugin's
   `.claude-plugin/plugin.json` (not optional — Claude
   Code uses this for update detection)
2. Commit the change to the attune-ai repo's main branch
3. Create a new per-plugin tag on attune-ai:
   `git tag attune-help-v0.3.1 -m "..."` then
   `git push origin attune-help-v0.3.1`
4. Update
   `Smart-AI-Memory/attune-docs/.claude-plugin/marketplace.json`
   — bump the `ref` field of the updated plugin to the new
   tag, bump the plugin's `version` field to match
   `plugin.json`
5. Commit and push the attune-docs update
6. Announce with explicit upgrade commands:

   ```
   /plugin marketplace update attune-docs
   /plugin install attune-help@attune-docs
   ```

## Phase 1 migration guide (for existing bundled-install users)

Users who previously installed `attune-help` or
`attune-author` via the bundled `attune-ai` marketplace
need to move their installation:

1. Add the new marketplace:

   ```
   /plugin marketplace add Smart-AI-Memory/attune-docs
   ```

2. Uninstall from the old marketplace:

   ```
   /plugin uninstall attune-help@attune-ai
   /plugin uninstall attune-author@attune-ai
   ```

3. Install from the new marketplace:

   ```
   /plugin install attune-help@attune-docs
   /plugin install attune-author@attune-docs
   ```

This migration note should appear in the current repo's
README banner AND in the release announcement.

## Next Steps (Phase 1 immediate)

- [ ] Sandbox test the duplicate-plugin scenario (step 1)
- [ ] Create per-plugin git tags on attune-ai (step 2)
- [ ] Prototype wrapper marketplace locally (steps 3-4)
- [ ] Create `Smart-AI-Memory/attune-docs` GitHub repo
      (step 5)
- [ ] Slim current `attune-ai` marketplace.json (step 6)
- [ ] Add migration banner to attune-ai README (step 7)
- [ ] End-to-end test all three funnels (step 8)
- [ ] Publish and announce (step 9)

## Open Questions

1. **Name for new repo and marketplace** — RESOLVED
   2026-04-08: **`attune-docs`**. Functional naming wins
   on searchability, OSS convention, verbal ergonomics,
   platform-neutrality (survives the multi-platform
   future in open question 7), and brand cohesion with
   the existing `attune-*` family. The "docs undersells
   runtime help" concern is addressed by investing in
   audience-forward README and landing page copy.

2. **What stays shared between the two repos (Phase 2
   scope)** — `.help/` format spec, CI reusable workflows,
   pre-commit config, docs theme. Deferred until Phase 2
   extraction decision.

3. **Migration path for existing bundled-install users** —
   RESOLVED 2026-04-08: Phase 1 uses the "Phase 1
   migration guide" section above. Three manual commands,
   documented in release notes and README banner.

4. **What happens to the current `packages/` directory** —
   DEFERRED. Phase 1 keeps it in place (plugins still live
   there). Phase 2 decides: delete or tombstone.

5. **Cross-repo references** — RESOLVED 2026-04-08: the
   slimmed `attune-ai` marketplace description carries a
   one-sentence cross-promotion hook pointing at
   `attune-docs`. Reverse direction (attune-docs
   referencing attune-ai) is optional for Phase 1 —
   include only if it fits the audience-forward copy
   naturally.

6. **PyPI naming and release pipeline** — DEFERRED to
   Phase 2. Phase 1 does not touch PyPI; `attune-help` and
   `attune-author` continue to release from the attune-ai
   repo's CI exactly as today.

7. **Multi-platform future** — the eventual goal is to
   support additional AI CLI platforms beyond Claude Code
   (Gemini CLI, potentially others). The Python packages
   (`attune-help`, `attune-author`) and their MCP servers
   are already platform-neutral; only the plugin wrappers
   under `.claude-plugin/` are Claude Code-specific. All
   decisions in this plan — repo names, marketplace
   structure, documentation framing — must avoid
   platform-specific branding that would block future
   adapters. Candidate repo structure for Phase 2: one
   repo per "product line," containing platform-neutral
   Python packages plus per-platform plugin wrappers side
   by side (e.g. `.claude-plugin/`, `.gemini-plugin/`,
   etc.).

8. **Runtime skill-trigger collision in cross-marketplace
   duplicate installs** — UNKNOWN, must be verified via
   sandbox test in Phase 1 step 1. The docs do not
   address what happens when the same plugin name is
   installed from two different marketplaces. The historic
   "duplicate plugins cause conflicting skill triggers"
   lesson may or may not apply here. Test result
   determines safe order of operations for slimming the
   old marketplace.

## Draft repo copy

Lift-and-ship copy for the new `attune-docs` repo. Final
polish happens during Phase 1 setup, but this is the
starting point so the positioning intent is captured
while it is fresh.

### README header (top of `README.md`)

```markdown
# attune-docs

**Context-sensitive help for your AI product's users.**

Ship help content the same way you ship code — authored
in templates, version-controlled, and delivered at the
exact moment your users need it.

attune-docs is a two-plugin help platform for Claude
Code (with Gemini and other platform adapters planned):

- **attune-help** — lightweight runtime reader. Reads
  `.help/` templates with progressive depth
  (concept → task → reference). No AI keys required.
  Install this alone when you just want to consume help
  content someone else wrote.
- **attune-author** — AI-powered authoring companion.
  Generates, maintains, and validates `.help/` templates
  via a staleness-aware workflow. Install this alongside
  attune-help when you are the one building the help
  content.

## Quick start

### I want to read help templates

    claude plugin marketplace add Smart-AI-Memory/attune-docs
    claude plugin install attune-help@attune-docs

### I want to author and ship help content

    claude plugin marketplace add Smart-AI-Memory/attune-docs
    claude plugin install attune-help@attune-docs
    claude plugin install attune-author@attune-docs

## Why "docs"?

"Docs" is the category people actually search for. But
this is not a static site generator or a wiki — it is a
runtime, context-sensitive help system your AI product
uses to answer user questions at the exact moment they
need the answer. Authored like docs, delivered like chat.
```

### Marketplace metadata for new `attune-docs` repo (Phase 1)

Uses `git-subdir` sources pinned to tags on the current
`attune-ai` repo. Swap to relative paths in Phase 2 after
extraction.

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "attune-docs",
  "owner": {
    "name": "Smart AI Memory",
    "email": "patrick.roebuck@smartaimemory.com"
  },
  "metadata": {
    "description": "Context-sensitive help for your AI product's users. Author and deliver runtime help content the same way you ship code.",
    "version": "0.1.0"
  },
  "plugins": [
    {
      "name": "attune-help",
      "description": "Lightweight runtime reader for .help/ templates. Progressive depth (concept -> task -> reference). No AI keys required. Install alone to consume help content, or pair with attune-author to build it.",
      "source": {
        "source": "git-subdir",
        "url": "https://github.com/Smart-AI-Memory/attune-ai.git",
        "path": "packages/attune-help/plugin",
        "ref": "attune-help-v0.3.0"
      },
      "version": "0.3.0"
    },
    {
      "name": "attune-author",
      "description": "AI-powered authoring companion for attune-help. Generates, maintains, and validates .help/ templates through a 3-stage pipeline with staleness detection. Pairs with attune-help to build and ship context-sensitive help content.",
      "source": {
        "source": "git-subdir",
        "url": "https://github.com/Smart-AI-Memory/attune-ai.git",
        "path": "packages/attune-author/plugin",
        "ref": "attune-author-v0.1.0"
      },
      "version": "0.1.0"
    }
  ]
}
```

### Slimmed marketplace metadata for current `attune-ai` repo

Remove `attune-help` and `attune-author` entries; narrow
the `attune-ai` plugin description to focus on dev-tool
positioning with a cross-promotion hook back to
`attune-docs`:

```json
{
  "metadata": {
    "description": "Developer workflow tool for building AI-powered products. Security audits, code review, test generation, release prep — skills-first, auto-triggering from natural language.",
    "version": "5.10.0"
  },
  "plugins": [
    {
      "name": "attune-ai",
      "description": "14 auto-triggering skills for the developer workflows behind building AI products: security audits, code reviews, test generation, bug prediction, and release preparation. Looking for help content tools? See Smart-AI-Memory/attune-docs."
    }
  ]
}
```

The final sentence is the cross-promotion hook back to
attune-docs for funnel-3 discovery, without bundling.

### Migration banner for current `attune-ai` README

Add near the top of
[README.md](../../README.md), before the main
feature list:

```markdown
> **Heads up:** `attune-help` and `attune-author` have
> moved to their own marketplace at
> [Smart-AI-Memory/attune-docs](https://github.com/Smart-AI-Memory/attune-docs).
> If you installed them via this marketplace previously,
> see the [migration guide](#migration) below. New users
> should add the `attune-docs` marketplace directly.
```

A `## Migration` section later in the README walks through
the three-command uninstall/reinstall flow from the
"Phase 1 migration guide" section above.
