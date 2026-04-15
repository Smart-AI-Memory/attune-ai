# Plan B Manual Test Plan — Steps 1 and 8

These tests require a **clean Claude Code environment** (ideally
a second machine or a profile Patrick has not used before).
They cannot be run from inside the current Claude Code session
because `/plugin marketplace add` manipulates the session's own
plugin state.

## Prerequisites

- A clean Claude Code install with no `attune-*` plugins
  installed. `claude plugin list` should return nothing starting
  with `attune-`.
- `/mcp` should show no attune-related MCP servers.
- A local clone of `Smart-AI-Memory/attune-ai` at
  `/Users/patrickroebuck/attune-ai` with the
  `feature/attune-plugin-split-prep` branch merged to main and
  the per-plugin tags pushed (prerequisite: Plan B step 2).

---

## Step 1 — Duplicate-plugin sandbox test

**Goal:** Determine whether installing `attune-help` from two
different marketplaces triggers duplicate skills, a conflict
error, or silent shadowing. The result determines whether
Plan B step 6 (slimming the attune-ai marketplace) must happen
before or after step 5 (publishing attune-docs).

### Steps

1. Start fresh Claude Code session. Verify no attune plugins
   installed:

   ```
   /plugin list
   /mcp
   ```

2. Add the root attune-ai marketplace (which currently
   ONLY lists attune-ai, not attune-help — so this should be
   a no-op for our test). We need a second marketplace that
   DOES list attune-help to create the duplicate condition.

3. Add the scratch wrapper marketplace with attune-help:

   ```
   /plugin marketplace add /tmp/attune-docs-scratch/step3-relative
   ```

   Expected: marketplace "attune-docs-scratch" added.

4. Install attune-help from the scratch marketplace:

   ```
   /plugin install attune-help@attune-docs-scratch
   ```

   Expected: attune-help plugin installed. `/plugin list`
   shows `attune-help@attune-docs-scratch`.

5. Now create the duplicate condition. Add a SECOND
   marketplace that also lists attune-help. The easiest way
   is to create a throwaway test marketplace at
   `/tmp/attune-docs-scratch/step3-dup/` with the same
   contents but a different `name` field:

   ```
   /plugin marketplace add /tmp/attune-docs-scratch/step3-dup
   ```

6. Try to install attune-help from the duplicate:

   ```
   /plugin install attune-help@attune-docs-scratch-dup
   ```

7. **Observe and document:**
   - Does Claude Code error? What's the exact message?
   - Does it install and coexist? Does `/plugin list` show
     both entries?
   - Do skills trigger twice, or does one shadow the other?
   - Does `/mcp` show two MCP servers or one?
   - Test a skill trigger ("show me the concept for plugin")
     and observe which plugin handles it.

8. Cleanup:

   ```
   /plugin uninstall attune-help@attune-docs-scratch
   /plugin uninstall attune-help@attune-docs-scratch-dup
   /plugin marketplace remove attune-docs-scratch
   /plugin marketplace remove attune-docs-scratch-dup
   ```

### Result to record in the main plan

Open `.claude/plans/attune-two-marketplace-split-2026-04-08.md`
and replace the "UNKNOWN" text in Open Question 8 with the
observed behavior. This determines the safe publish order for
steps 5 and 6.

---

## Step 8 — End-to-end test of all three funnels

**Goal:** Verify every install path works before announcing.
Runs AFTER steps 5-7 are complete (attune-docs repo exists,
attune-ai marketplace has the cross-promotion hook).

### Funnel 1 — Developer building an AI product

1. Clean Claude Code session.
2. `/plugin marketplace add Smart-AI-Memory/attune-ai`
3. `/plugin install attune-ai@attune-ai`
4. Verify: `/plugin list` shows attune-ai.
5. Trigger a skill by natural language:
   - Type: "security audit src/"
   - Expected: The `/attune-ai:security-audit` skill fires.
6. Verify `/mcp` shows the attune-ai MCP server.
7. **Must NOT see**: any attune-help or attune-author plugin
   listed (bundle was deliberately removed from this
   marketplace).
8. Uninstall and remove the marketplace.

### Funnel 2 — Downstream consumer reading `.help/` templates

1. Clean Claude Code session.
2. `/plugin marketplace add Smart-AI-Memory/attune-docs`
3. `/plugin install attune-help@attune-docs`
4. Verify: `/plugin list` shows ONLY attune-help (not
   attune-author).
5. Test without ANY `ANTHROPIC_API_KEY` set — unset the env
   var and restart Claude Code if needed.
6. Trigger a lookup skill:
   - Type: "show me the concept for plugin"
   - Expected: The `/attune-docs:lookup-topic` skill fires
     and renders a template without requiring AI.
7. Verify `/mcp` shows attune-help-mcp server and NO
   attune-author server.

### Funnel 3 — Builder shipping help content with an AI app

1. Clean Claude Code session (with `ANTHROPIC_API_KEY` set
   this time).
2. `/plugin marketplace add Smart-AI-Memory/attune-docs`
3. `/plugin install attune-help@attune-docs`
4. `/plugin install attune-author@attune-docs`
5. Verify: `/plugin list` shows both plugins.
6. Verify: `/mcp` shows both MCP servers.
7. Trigger an author skill:
   - Type: "set up help in this project"
   - Expected: `/attune-docs:author-init` fires.
8. Trigger a read skill:
   - Type: "what's stale?"
   - Expected: `/attune-docs:author-status` fires.
9. Run through the full author workflow in a throwaway test
   project:
   - author-init (bootstrap)
   - author-generate (create a template)
   - author-status (verify fresh)
   - modify source, check stale
   - author-maintain (regenerate)

### Success criteria

- [ ] Funnel 1: attune-ai installs standalone, no help tools
  present, skills trigger correctly
- [ ] Funnel 2: attune-help installs standalone, works without
  AI keys, lookup skills trigger
- [ ] Funnel 3: Both plugins coexist in the same session, all
  author skills trigger, full workflow runs end-to-end
- [ ] Total time for funnel 3 from "clean environment" to
  "both plugins installed and skills verified" is under 60
  seconds (per the plan's success criteria)

### Record results

Add a section to
`.claude/plans/attune-two-marketplace-split-2026-04-08.md`
under "Phase 1 test results" with timestamps and any deviations
from expected behavior. If any funnel fails, DO NOT proceed to
step 9 (publish and announce).
