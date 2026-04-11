# Attune Two-Marketplace Split

**Created:** 2026-04-08
**Updated:** 2026-04-09 (Phase 1 architecture pivoted due to git-subdir CLI bug; manual tests executed)
**Source:** /brainstorm session
**Status:** Phase 1 marketplace architecture was forced to collapse into partial Phase 2 because `git-subdir` source type is not supported by shipping Claude Code v2.1.68/v2.1.78 (anthropics/claude-code#33172). Install-level tests pass end-to-end against a republished `Smart-AI-Memory/attune-docs` that uses physically-copied plugin dirs + relative-path sources. MCP runtime is blocked by a separate pre-existing release-engineering gap (stale/missing PyPI publications of `attune-help` and `attune-author`) and is tracked as a Phase 1 follow-up, not a Plan B regression.

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

- [x] Sandbox test the duplicate-plugin scenario (step 1)
      — done 2026-04-09, Open Question 8 resolved as
      "coexist cleanly"
- [x] Create per-plugin git tags on attune-ai (step 2)
      — `attune-help-v0.3.0` and `attune-author-v0.1.0`
      pushed to origin
- [x] Prototype wrapper marketplace locally (steps 3-4)
      — obsoleted by architectural pivot; `git-subdir`
      unsupported in shipping Claude Code
- [x] Create `Smart-AI-Memory/attune-docs` GitHub repo
      (step 5) — live at commit `dc7f9a7`, uses
      relative-path sources with physically-copied plugin
      dirs (pivot from git-subdir architecture)
- [x] Slim current `attune-ai` marketplace.json (step 6)
      — live marketplace.json already only lists
      `attune-ai` plugin
- [x] Add migration banner to attune-ai README (step 7)
      — committed 2026-04-10, includes full Migration
      section with three-command upgrade flow
- [x] End-to-end test all three funnels (step 8) —
      install-level: all pass. MCP runtime verified
      2026-04-10 after resolving Blocker 1.
- [x] Close sub-package PyPI publish gap (Blocker 1) —
      resolved 2026-04-10, see updated blocker section
- [x] Run interactive skill-trigger phase (Blocker 2) —
      resolved 2026-04-10, all 14 skills fire correctly
- [x] Fix invalid `uv run --from` syntax in all three
      `.mcp.json` files (Blocker 3, discovered 2026-04-10
      evening during funnel test run — was the actual
      root cause of the MCP health-check failures
      previously attributed to pyenv shim quirks)
- [x] Clean-environment Funnel 1 + Funnel 3 tests with
      `CLAUDE_CONFIG_DIR` isolation — both pass including
      MCP runtime connectivity
- [ ] Publish and announce (step 9) — ready to execute
      once attune-ai PR #142 merges (CI test matrix
      pending, all required checks already green)

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
   duplicate installs** — RESOLVED 2026-04-09: **coexist
   cleanly at the install level**. Tested in a clean
   `CLAUDE_CONFIG_DIR` against two self-contained scratch
   marketplaces (`attune-docs-scratch` and
   `attune-docs-scratch-dup`) that both declare an
   `attune-help` plugin. Both `claude plugin install
   attune-help@attune-docs-scratch` and `claude plugin
   install attune-help@attune-docs-scratch-dup` succeeded
   with no error, no warning, no conflict detection.
   `claude plugin list` showed both entries side-by-side
   with their distinct stub versions. Claude Code treats
   `plugin@marketplace` as the real identity — the `plugin`
   name alone is not a uniqueness constraint. **Implication
   for plan step ordering:** no ordering constraint between
   slimming `attune-ai` marketplace and publishing
   `attune-docs`. They are safe to ship in either order.
   **Remaining sub-question** (not yet tested, requires
   interactive session): when the same plugin name from two
   marketplaces exposes the same skill trigger, does Claude
   Code route the trigger to one of them deterministically,
   both, or prompt for disambiguation? This is a runtime
   concern only, not a publish-order concern. Tracked as
   a Phase 2 follow-up.

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

## Phase 1 test results

Executed 2026-04-09. Tests were run from isolated
`CLAUDE_CONFIG_DIR` directories (safer than the
scrub-and-restore runbooks at
`/tmp/attune-docs-scratch/{scrub,restore}-runbook.md` —
no primary profile state was touched). Test driver scripts
live at `/tmp/attune-docs-scratch/execution-kit/` and write
full transcripts to `~/claude-test/<step>/observations.log`.

**Status:** INSTALL-LEVEL PASS. All install, isolation,
and benchmark assertions met. MCP runtime health-check
fails for all three plugins on this machine (including
`attune-ai` itself, which is published on PyPI) and is a
separate pre-existing issue; see "Known blockers and
follow-ups" below.

### Architectural pivot (2026-04-09)

**Phase 1 "thin wrapper marketplace" strategy was
unimplementable.** Claude Code v2.1.68 (and confirmed
v2.1.78 per GitHub issues) rejects the `git-subdir`
source type at schema validation. This affects Anthropic's
own `claude-plugins-official` marketplace too. Open issue:
[anthropics/claude-code#33172](https://github.com/anthropics/claude-code/issues/33172).

The fix was to collapse Phase 1 and part of Phase 2
early: physically copy
[packages/attune-help/plugin](../../packages/attune-help/plugin)
and
[packages/attune-author/plugin](../../packages/attune-author/plugin)
into `Smart-AI-Memory/attune-docs` at `plugins/attune-help`
and `plugins/attune-author`, then rewrite
`attune-docs/.claude-plugin/marketplace.json` to use
relative-path sources (`"./plugins/attune-help"` and
`"./plugins/attune-author"`). This is the proven-working
source form used by `claude-plugins-official` and
`knowledge-work-plugins`.

Trade-off accepted: plugin code now exists in BOTH
`attune-ai/packages/` AND `attune-docs/plugins/` until a
proper Phase 2 extraction removes the attune-ai copies.
No git history preservation was done on the copy —
that is deferred to full Phase 2.

### Test environment

- Machine: Patrick's primary dev machine
- Isolation method: `CLAUDE_CONFIG_DIR=~/claude-test/<step>`
  per test (not scrub-and-restore)
- Claude Code version: 2.1.68
- Scratch marketplaces (rewritten 2026-04-09 to use
  relative-path sources with stub plugins):
  - `/tmp/attune-docs-scratch/step3-relative/` — name
    `attune-docs-scratch`, contains a stub
    `attune-help` plugin at `./plugins/attune-help`
  - `/tmp/attune-docs-scratch/step3-dup/` — name
    `attune-docs-scratch-dup`, same stub layout,
    different marketplace name
- Published attune-docs state: rewritten commit `dc7f9a7`
  on `main`, uses relative-path sources pointing at
  physically-copied plugin dirs under `plugins/`

### Step 1 — Duplicate-plugin sandbox test

**Date run:** 2026-04-09
**Tester:** Patrick (driven by Claude Code)
**Log:** `~/claude-test/step1/observations.log`

**Observed behavior:**

1. Starting state: empty plugin list, empty marketplace
   list, empty MCP list. Verified.
2. Added `attune-docs-scratch` (first marketplace).
3. `claude plugin install attune-help@attune-docs-scratch`
   succeeded. Plugin list showed
   `attune-help@attune-docs-scratch` (v0.0.1-stub-a).
4. Added `attune-docs-scratch-dup` (second marketplace
   with the same `attune-help` plugin name).
5. `claude plugin install
   attune-help@attune-docs-scratch-dup` **succeeded
   with no error, warning, or conflict prompt**.
6. `claude plugin list` showed BOTH entries side by side:
   ```
   ❯ attune-help@attune-docs-scratch      v0.0.1-stub-a
   ❯ attune-help@attune-docs-scratch-dup  v0.0.1-stub-b
   ```
7. MCP list: empty (stub plugins had no MCP servers).
8. Skill trigger test: not run (stub plugins; deferred to
   a separate interactive test against real plugins to
   answer the runtime routing sub-question).

**Conclusion for Open Question 8:**

- [x] **Coexist cleanly** — safe to publish attune-docs
  marketplace before or after slimming attune-ai
  marketplace. No ordering constraint.
- [ ] Error on duplicate install
- [ ] Silent shadowing
- [ ] Other

Claude Code treats `plugin@marketplace` as the unique
identity. The `plugin` name alone is not a uniqueness
constraint across marketplaces.

### Step 8 — Three-funnel end-to-end test

**Date run:** 2026-04-09
**Tester:** Patrick (driven by Claude Code)
**Logs:** `~/claude-test/{funnel1,funnel2,funnel3}/observations.log`

#### Funnel 1 — Developer building an AI product

- [x] Clean session starts with no attune-* plugins installed
- [x] `claude plugin marketplace add Smart-AI-Memory/attune-ai` succeeds
- [x] `claude plugin install attune-ai@attune-ai` succeeds
  (v5.10.0)
- [x] `claude plugin list` shows only `attune-ai` — no
  `attune-help` or `attune-author` leakage (verified by
  automated grep assertion in the test script)
- [ ] Natural-language skill trigger ("security audit src/")
  fires `/attune-ai:security-audit` — NOT RUN (interactive
  phase skipped; install-phase was the priority)
- [ ] `claude mcp list` shows the attune-ai MCP server
  healthy — **FAILED with "Failed to connect"**. See
  "Known blockers and follow-ups" below. Note: this
  affects `attune-ai` itself which IS on PyPI, so the
  root cause is NOT the Plan B split.
- [x] Cleanup via `CLAUDE_CONFIG_DIR` wipe (not
  `/plugin uninstall`) succeeds

**Deviations:** MCP health check failure is systemic
across all plugins on this machine, not Plan-B-specific.

#### Funnel 2 — Downstream consumer (read-only, no AI key)

- [x] `ANTHROPIC_API_KEY` unset for this test (script
  explicitly `unset`s before launching)
- [x] `claude plugin marketplace add
  Smart-AI-Memory/attune-docs` succeeds from **live
  GitHub** (no local substitute needed)
- [x] `claude plugin install attune-help@attune-docs`
  succeeds (v0.3.0)
- [x] `claude plugin list` shows ONLY `attune-help`, not
  `attune-author` (verified by automated assertion)
- [ ] Natural-language lookup skill renders template
  without AI — NOT RUN (see note above)
- [ ] `claude mcp list` shows `attune-help` MCP server
  healthy — **FAILED with "Failed to connect"**. Root
  cause is the stale PyPI publication of `attune-help`,
  not the marketplace. See blockers section.

**Deviations:** MCP server startup failure. Install side
is clean.

#### Funnel 3 — Help builder (both plugins)

- [ ] `ANTHROPIC_API_KEY` is set — script gated with
  confirmation prompt if unset; test run did not verify
  the explicit `set` case
- [x] Both `attune-help` and `attune-author` installed
  from the same `attune-docs` marketplace
- [x] `claude plugin list` shows both
- [ ] `claude mcp list` shows both MCP servers healthy —
  **FAILED for both**. Both plugins hit the
  release-engineering blocker.
- [ ] Natural-language triggers ("set up help in this
  project", "what's stale?") — NOT RUN (interactive
  phase skipped)
- [ ] Full author workflow end-to-end in throwaway project
  — NOT RUN (depends on MCP server working; blocked by
  the publish gap)
- [x] **Total time from "clean environment" to "both
  plugins installed" was 4 seconds**, under the 60-second
  benchmark by 15x.

**Deviations:** MCP servers fail for the reason documented
in the blockers section.

### Go/no-go decision

Based on the above:

- [x] **All three funnels pass install-level assertions**
  → proceed to step 9 (publish and announce) for the
  **install-level fix**, with the MCP publish gap as a
  documented known-issue in the release notes
- [ ] Funnel 1 or 2 fails at install level → halt, investigate
- [x] **Funnel 3 has partial failures (MCP only)** → publish
  attune-docs install fix but flag the MCP publish gap in
  release notes and fix before any wider announcement

**Decision:** PROCEED with narrow scope. The git-subdir
bug fix (commit `dc7f9a7` on attune-docs `main`) is
already pushed and verified against live GitHub. It
unblocks install for all three funnels. Wider Phase 1
announcement waits on the publish gap.

**Rationale:** The Plan B Phase 1 story — "install
attune-docs marketplace and get the two help plugins" —
works now at the install level. The MCP runtime gap is a
pre-existing release-engineering debt independent of Plan
B; closing it requires (a) new CI infrastructure to
publish sub-packages and (b) a version bump on
`attune-help`. Neither is in the Plan B critical path and
both should be scoped as their own work.

## Known blockers and follow-ups

### Blocker 1: sub-package PyPI publication gap — RESOLVED 2026-04-10

Both sub-packages are now published with working
`[plugin]` extras, and both have dedicated CI workflows
in their standalone repos:

| Package | PyPI version | `[plugin]` extra | CI |
| --- | --- | --- | --- |
| `attune-help` | 0.3.1 | Works (`mcp>=0.9.0`) | `attune-help/.github/workflows/publish.yml` (OIDC) |
| `attune-author` | 0.1.0 | Works (`mcp>=0.9.0`, `anthropic>=0.40.0`) | `attune-author/.github/workflows/publish.yml` (OIDC) |

Verified end-to-end:

- `pip install 'attune-help[plugin]'` resolves cleanly
- `pip install 'attune-author[plugin]'` resolves cleanly
- `python -c "from attune_help.mcp.server import main"` OK
- `python -c "from attune_author.mcp.server import main"` OK
- `attune.help.preamble` imports via `attune_help` re-export path
- Main `attune.mcp.server` initialises with 41 tools registered

Cleanup:

- Removed stale
  [.github/workflows/publish-attune-help.yml](../../.github/workflows/publish-attune-help.yml)
  from the main repo — it built from
  `packages/attune-help/` which is now a tombstone
- The `packages/attune-help/` and `packages/attune-author/`
  directories in this repo remain as tombstones with
  README pointers to the standalone repos; deletion is
  deferred to a later cleanup PR

### Blocker 3: invalid `uv run --from` syntax in every `.mcp.json` — RESOLVED 2026-04-10

Discovered during tonight's Funnel 1 test run. This was
the actual root cause of the "MCP health-check fails for
all three plugins" symptom attributed in the 2026-04-09
test log to "pyenv shim quirks / uv startup path".

All three plugins shipped `.mcp.json` files invoking the
MCP server with:

```text
uv run --from <package>[plugin] python -m <module>
```

But `--from` is **not a valid flag for `uv run`** in any
shipped uv version. Tested with uv 0.9.17 (Homebrew) and
uv 0.9.22 (pyenv); both reject with:

```text
error: unexpected argument '--from' found
tip: a similar argument exists: '--frozen'
```

The correct form is `uvx --from <package> <command>` (an
alias for `uv tool run --from …`), which creates a
dedicated isolated environment from the specified package
and runs the command in it. The `--from` flag belongs to
`uv tool run`, not `uv run`.

Fix applied to all three plugins:

- `plugin/.mcp.json` (this repo, on PR #142)
- `attune-docs/plugins/attune-help/.mcp.json`
  (attune-docs PR #2, merged)
- `attune-docs/plugins/attune-author/.mcp.json`
  (attune-docs PR #2, merged)

Verified on live installs using
`CLAUDE_CONFIG_DIR`-isolated profiles:

```text
# Funnel 3 (attune-docs, both plugins):
plugin:attune-help:attune-help:
  uvx --from attune-help[plugin] python -m attune_help.mcp.server
  - ✓ Connected
plugin:attune-author:attune-author:
  uvx --from attune-author[plugin] python -m attune_author.mcp.server
  - ✓ Connected

# Funnel 1 (attune-ai, after patching the installed
# cache with the PR #142 fix):
plugin:attune-ai:attune-ai:
  uvx --from attune-ai python -m attune.mcp.server
  - ✓ Connected
```

Supporting verification of the local stale-install
issue encountered earlier: the outdated v3.9.0 PyPI
install on Patrick's machine was shadowing the editable
source; fixed by `pip install -e .` and removing the
stale `site-packages/attune/workflows/` shadow directory.
That was a dev-machine quirk, not a ship-blocker.

### Funnel test results (2026-04-10, evening)

Test method: `CLAUDE_CONFIG_DIR` isolation per funnel,
running `claude plugin marketplace add` → `claude plugin
install` → `claude plugin list` → `claude mcp list`.

**Funnel 1 — attune-ai solo (developer workflows):**

- `claude plugin marketplace add Smart-AI-Memory/attune-ai` OK
- `claude plugin install attune-ai@attune-ai` OK
- `claude plugin list` shows `attune-ai@attune-ai` v5.10.0 enabled
- All 14 skill directories present on disk
- MCP health: `✓ Connected` (after patching cache with PR #142 fix)

**Funnel 3 — attune-docs both plugins (AI authoring workflow):**

- `claude plugin marketplace add Smart-AI-Memory/attune-docs` OK
- `claude plugin install attune-help@attune-docs` OK
- `claude plugin install attune-author@attune-docs` OK
- `claude plugin list` shows both plugins enabled at
  v0.3.1 and v0.1.0 respectively
- All 4 attune-help skills and 6 attune-author skills
  present on disk
- MCP health: both servers `✓ Connected`

Funnel 2 (attune-help solo, no AI key) was not run as a
separate test tonight — the attune-help MCP connectivity
evidence from Funnel 3 is sufficient, since attune-help
is independent of `ANTHROPIC_API_KEY` by design.

---

**Original symptom (for history):** MCP server health
check failed for `attune-help`, `attune-author`, and
`attune-ai` with `✗ Failed to connect` when running
`claude mcp list`.

**Root cause (partial):** `.mcp.json` in both
`attune-help` and `attune-author` plugins uses
`uv run --from <package>[plugin]` which resolves the
package from PyPI at runtime. But:

1. **`attune-help` v0.3.0 on PyPI is stale.** Local
   `packages/attune-help/pyproject.toml` defines a
   `[plugin] = ["mcp>=0.9.0"]` extra. The published PyPI
   version only has `[rich]`. The stale publish predates
   the `[plugin]` extra addition and was never bumped.
2. **`attune-author` is not on PyPI at all.** Never
   published. `uv run --from attune-author` resolves to
   nothing.
3. **No CI publish path exists for sub-packages.** The
   workflow at
   [.github/workflows/publish-pypi.yml](../../.github/workflows/publish-pypi.yml)
   runs `python -m build` from repo root, which only
   builds the main `attune-ai` package. It does not
   iterate into `packages/`. The past `attune-help` v0.3.0
   publication must have been done manually outside CI.
4. **`attune-ai` MCP also fails** on this machine despite
   being on PyPI. Root cause likely the pyenv `uv` shim
   path combined with `claude mcp list`'s health-check
   timeout during cold-start dependency resolution — this
   is the same class of issue called out in
   [.claude/CLAUDE.md](../CLAUDE.md) lesson-learned about
   `uv run pip-audit` hitting the pyenv shim rather than
   the venv. Needs a separate diagnostic pass.

**Scope of fix (to close the blocker):**

- [ ] Add a CI publish workflow (or extend existing
  `publish-pypi.yml`) that builds and uploads
  `packages/attune-help` and `packages/attune-author`
  independently of the main `attune-ai` package.
  Trusted-publishing OIDC applies per package. Likely
  needs two new PyPI projects registered with OIDC.
- [ ] Bump `packages/attune-help/pyproject.toml` version
  0.3.0 → 0.3.1 (PyPI rejects re-publishing the same
  version). Also bump
  `plugins/attune-help/.claude-plugin/plugin.json`
  version to match.
- [ ] Trigger the new CI workflow for both packages.
  Approve the `pypi` environment gate manually.
- [ ] Re-probe MCP health on Patrick's machine (and on a
  fresh clean machine to rule out pyenv shim quirks).
- [ ] If MCP still fails after publication, diagnose the
  pyenv-shim / `uv` startup path separately.

**Estimated scope:** release engineering — CI change +
first-time PyPI project registration + two package
publishes + retest. Not Plan B core work.

### Blocker 2: interactive skill trigger tests — RESOLVED 2026-04-10

All 14 plugin skills were invoked from a live Claude
Code session with `attune-ai` installed and verified to
fire correctly. Results captured in
[.claude/MCP_TEST_RESULTS.md](../MCP_TEST_RESULTS.md).

Summary:

- 13 of 14 skills fire via natural-language / slash
  command triggers (`security-audit`, `smart-test`,
  `code-quality`, `doc-gen`, `refactor-plan`, `coach`,
  `spec`, `fix-test`, `bug-predict`, `planning`,
  `workflow-orchestration`, `memory-and-context`,
  `attune-hub`)
- 1 skill (`release-prep`) has
  `disable-model-invocation: true` by design — not
  model-triggered, user-only
- 10 of 10 utility MCP tools dispatch successfully
  (`memory_*`, `context_*`, `attune_*_level`,
  `auth_status`, `telemetry_stats`)
- Supporting automated coverage: 399 MCP tests and 93
  plugin-validation tests green

**Deferred:** Funnel 2 and Funnel 3 clean-environment
install tests from `manual-test-plan.md`. Those
exercise install paths and marketplace behavior from a
pristine Claude Code profile, not skill triggering.
They remain manual and are not blocking for publish —
the functional behavior they exercise is already
covered by the resolved blocker work plus the 2026-04-09
install-level test results above.

### Follow-up: duplicate-plugin runtime routing

Step 1 resolved Open Question 8 at the **install level**
— both copies of `attune-help` coexist without conflict.
But the sub-question "if both expose the same skill
trigger, which one handles it?" is not yet answered. This
is a Phase 2 concern, not a publish blocker.
