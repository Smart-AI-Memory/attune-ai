# Release Announcement — attune-docs marketplace split

**Drafted:** 2026-04-10
**Target release:** Phase 1 of the two-marketplace split plan
**Announcement channels:** GitHub release notes, LinkedIn post,
project README, `#attune-ai` user community (if/when created)

---

## GitHub release notes (short form)

### `attune-help` and `attune-author` have moved to their own marketplace

To keep the main `attune-ai` marketplace focused on the
developer-workflow plugin, the help and authoring plugins now
live in a dedicated marketplace:
[Smart-AI-Memory/attune-docs](https://github.com/Smart-AI-Memory/attune-docs).

**New users**

```text
/plugin marketplace add Smart-AI-Memory/attune-docs
/plugin install attune-help@attune-docs        # lookup-only
/plugin install attune-author@attune-docs      # authoring
```

**Existing users** (if you previously installed `attune-help`
or `attune-author` via the bundled `attune-ai` marketplace):

```text
/plugin marketplace add Smart-AI-Memory/attune-docs
/plugin uninstall attune-help@attune-ai
/plugin uninstall attune-author@attune-ai
/plugin install attune-help@attune-docs
/plugin install attune-author@attune-docs
```

**Nothing changes for `attune-ai` users.** The
`/plugin marketplace add Smart-AI-Memory/attune-ai` +
`/plugin install attune-ai@attune-ai` flow still installs the
same developer-workflow plugin with 14 auto-triggering skills,
41 MCP tools, and the full set of workflows.

Why split:

- `attune-help` is a lookup-only runtime that works without an
  API key — it should not require the full `attune-ai` AI stack
- `attune-author` is the authoring toolkit for knowledge bases
  — distinct audience from developer-workflow users
- Smaller, focused plugins load faster and are easier to
  understand
- Each plugin can ship on its own cadence now that sub-package
  publish workflows exist in their standalone repos

See the [Migration section](https://github.com/Smart-AI-Memory/attune-ai/blob/main/README.md#migration)
of the main README for the full upgrade flow.

---

## LinkedIn post (long form, ASCII-marker code blocks)

Shipping a small but meaningful housekeeping update to Attune AI today.

`attune-help` (lookup-only help runtime) and `attune-author`
(knowledge-base authoring toolkit) have moved to their own
Claude Code marketplace: `Smart-AI-Memory/attune-docs`.

Why it matters:

- `attune-help` is the lightweight side — it renders
  progressive-depth help templates and doesn't need an
  Anthropic API key to be useful. Bundling it with the full
  `attune-ai` plugin was making it harder for users who only
  wanted the help runtime.
- `attune-author` is a distinct tool for a distinct audience —
  people who build and maintain knowledge bases, not
  developers looking for workflow automation.
- Each now ships on its own cadence out of its own repo with
  its own OIDC-trusted publishing workflow.

`attune-ai` itself is unchanged — still 14 skills, 41 MCP
tools, and the full developer-workflow stack on the
`Smart-AI-Memory/attune-ai` marketplace.

Upgrade commands for existing users who had the bundled setup:

--- CODE START ---
/plugin marketplace add Smart-AI-Memory/attune-docs
/plugin uninstall attune-help@attune-ai
/plugin uninstall attune-author@attune-ai
/plugin install attune-help@attune-docs
/plugin install attune-author@attune-docs
--- CODE END ---

Full migration notes in the README:
https://github.com/Smart-AI-Memory/attune-ai#migration

---

## Checklist before hitting publish

- [ ] All three funnel tests pass from a clean Claude Code
  profile (funnel 1 verified 2026-04-10; funnels 2 and 3
  deferred as not publish-blocking per Blocker 2 resolution)
- [ ] `pip install 'attune-help[plugin]'` resolves and
  `python -c "from attune_help.mcp.server import main"` works
- [ ] `pip install 'attune-author[plugin]'` resolves and
  `python -c "from attune_author.mcp.server import main"` works
- [ ] Main `attune-ai` MCP server initializes with 41 tools
- [ ] README migration banner and Migration section are live
  on main
- [ ] `Smart-AI-Memory/attune-docs` marketplace.json lists
  both `attune-help` and `attune-author` with correct
  `ref` fields and plugin versions
- [ ] `.claude-plugin/marketplace.json` in the main
  `attune-ai` repo lists only `attune-ai` (no `attune-help`
  or `attune-author` entries)
- [ ] CHANGELOG.md entry for the migration (if the version
  bump is tagged as part of this work)

---

## Do not include in the announcement

- Do not link to the internal plan doc
  (`.claude/plans/attune-two-marketplace-split-2026-04-08.md`)
  — it's process documentation, not user-facing
- Do not mention "Blocker 1" or "Blocker 2" by name —
  those are internal tracking labels
- Do not link to `.claude/MCP_TEST_RESULTS.md` — also
  internal

---

## Post-publish follow-ups

1. Watch `Smart-AI-Memory/attune-docs` issues for migration
   pain points during the first week
2. If downloads spike on `attune-help` without spiking on
   `attune-author`, that validates the split hypothesis —
   the two audiences are genuinely separate
3. Consider a follow-up post after 2-4 weeks with usage
   stats from pepy.tech for both sub-packages
