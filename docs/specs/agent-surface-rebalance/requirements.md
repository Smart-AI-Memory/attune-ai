# Spec: Agent Surface Rebalance

**Status**: retired (2026-05-12, see [decisions.md](decisions.md))
**Created**: 2026-05-12
**Origin**: Daily briefing carryover item — attune-ai has 1
subagent (`plugin/agents/setup-guide.md`) against 15 skills.
Several skills run long, context-heavy analyses (security-audit,
bug-predict, deep-review, refactor-plan, smart-test) whose
intermediate output bloats the main agent's context window
unnecessarily. The Agent SDK's subagent isolation is the
mechanism that already exists to fix this — it just isn't wired
into the skills that would benefit from it.

---

## Phase 1: Requirements

### Why

1. **Context window pressure during long scans.** A
   `security-audit` over `src/attune/` walks ~80k LOC, emits
   intermediate AssistantMessage TextBlocks for every file the
   workflow examines, and only the final report is load-bearing
   for the user. All the intermediate exploration text stays in
   the main agent's context and pushes load-bearing earlier
   content toward the compact threshold.

2. **The Agent SDK already supports the isolation pattern.**
   `collect_agent_output()` in
   `src/attune/workflows/agent_sdk_adapter.py` aggregates
   subagent outputs back to the parent. When a parent agent
   spawns a subagent via the SDK, only the subagent's terminal
   summary returns to the parent — the intermediate stream
   stays in the subagent's isolated session. This is the
   protection mechanism. It's documented in the existing
   "SDK adapter swallows subagent findings" lesson (which was
   later corrected — the adapter is fine, budget caps were
   the issue).

3. **A sibling plugin (`agents:*`) already exposes the pattern
   end-to-end.** The available skills list includes
   `agents:release-prep`, `agents:security-reviewer`,
   `agents:doc-generator`, `agents:test-writer`,
   `agents:sdk-agent`, `agents:state-manager`. These are
   *separate* from attune-ai's skills. The attune-ai plugin
   should not reinvent them, but should leverage subagent
   delegation in its own long-running skills.

4. **The `setup-guide.md` lone-agent precedent is the wrong
   anchor.** It's a one-shot setup helper, not an analytical
   workhorse. Treating it as the template for "what plugin
   agents look like" undersells the pattern. The analytical
   skills are the real candidates.

### What — high-level scope

- **In scope**: convert 2–3 long-running analysis skills to
  delegate to a subagent that runs the analysis and returns
  only a structured summary. Specifically:
    - `plugin/skills/security-audit` — the deepest scan
    - `plugin/skills/deep-review` (if present; not currently
      in `plugin/skills/` listing — verify and either include
      or replace with `bug-predict`)
    - `plugin/skills/refactor-plan` — multi-file analysis

- **Also in scope**: a `plugin/agents/analyzer-base.md`
  template that documents the conventions (read-only tools,
  budget caps, summary schema) so future analytical agents
  follow the same shape.

- **Out of scope (for this spec)**:
    - Converting `smart-test` / `bug-predict` — both already
      delegate to MCP workflows that run in their own SDK
      session. Their context cost is the MCP result, not the
      intermediate stream. Re-evaluate after the first
      conversion lands.
    - Replacing skills entirely with subagents. Skills remain
      the user-facing entry point; the subagent is an
      implementation detail of how the skill executes.
    - Any work on the `agents:*` sibling plugin.

### Done when

- 2–3 attune-ai skills route through dedicated subagents and
  return structured summaries to the main agent instead of
  full intermediate traces.
- `plugin/agents/analyzer-base.md` documents the convention.
- One real before/after measurement (token count in main
  context after a representative scan) demonstrates the
  protection actually works.
- No regression in the user-visible output quality of the
  converted skills — the summary the user sees is at least
  as actionable as the pre-conversion version.

### Non-goals

- A general framework for "skill → agent" auto-conversion.
  Each skill's conversion is bespoke because what counts as
  the "summary" differs per skill.
- Caching, parallel subagent dispatch, or other performance
  features. Scope is purely about context-window protection.
- Backwards-compat shims. The skill's user-facing contract
  stays identical; only the internal mechanism changes.

### Open questions (resolve in design phase)

1. Which exact 2–3 skills to convert first? The candidate list
   in "What" is initial; the design phase should pick based on
   actual context-cost measurements.
2. Where does the subagent's structured summary schema live?
   Inline in `analyzer-base.md`, in a Python module, or
   negotiated per-agent?
3. What's the right budget cap default for an analyzer
   subagent? The "SDK adapter" lesson shipped a $10 cap for
   multi-subagent workflows; a single analyzer is probably
   $2–$5 — confirm in design.
