# Bulk + Catalog Access — Requirements

**Status:** implemented (2026-06-25) — OQ1/OQ2 resolved in decisions
**Owner:** Patrick + agent
**Scope:** ship two left-behind skills into the plugin surface.

---

## Problem

A full access audit (2026-06-25) found four polished, `category: primary`
skills living in `.claude/skills/` — `catalog`, `wizard`, `agent`,
`bulk` — that have **never** shipped in the plugin. Git history confirms
they were left behind, not deliberately cut: `plugin/skills/` (the
shipped source of truth, synced to `.agents/skills/` by
`scripts/sync_agents_skills.py`) never contained them.

Two of the four are clean to ship now because their capability already
has a surface or needs no interactive bridge:

- **`bulk`** — batch processing (50% cost). The `analyze_batch` MCP tool
  already exists; the skill is the missing discovery layer.
- **`catalog`** — "browse everything attune offers". Pure read over the
  live registries; the discovery surface itself currently doesn't ship.

The other two (`wizard`, `agent`) are **interactive orchestration** — no
CLI/MCP path, driven by a form engine / multi-step flows. They share a
harder design problem and are deferred to a separate
`interactive-orchestration-access` spec. **Out of scope here.**

---

## Goals

- A plugin user can discover and trigger batch processing via a `bulk`
  skill that calls the existing `analyze_batch` MCP tool.
- A plugin user can ask "what can attune do?" and get an accurate,
  **registry-driven** catalog of workflows, wizards, and tools via a
  `catalog` skill — no hand-maintained lists (the website-accuracy rule).

---

## Functional requirements

- **FR-1** `plugin/skills/bulk/SKILL.md` exists, follows the shipped
  plugin skill conventions (frontmatter `name` + trigger-bearing
  `description` + `argument-hint`; body with `help_lookup` preamble,
  scoping, execution, output), and instructs calling `analyze_batch`.
- **FR-2** `plugin/skills/catalog/SKILL.md` exists, same conventions, and
  renders the catalog from live data — `list_workflows()`,
  `list_wizards()`, and the MCP tool list — not a static list.
- **FR-3** Both skills pass `sync_agents_skills.py --check` (their
  `.agents/skills/` mirrors are regenerated in the same change).
- **FR-4** Both skills name only real tools/commands (reference
  validation) and disambiguate triggers from existing skills (`bulk`
  vs nothing overlapping; `catalog` vs `attune-hub`, which is the
  routing hub — catalog is the *enumeration* surface).

## Non-functional requirements

- **NFR-1** No new workflow/wizard engine code. `bulk` reuses
  `analyze_batch`; `catalog` reads existing registries (a thin read-only
  `list_capabilities` MCP tool is permitted if it is the cleanest
  registry-driven path — see design D-CAT).
- **NFR-2** Catalog accuracy: counts and names come from the registries
  at call time; the spec adds no number that can drift.
- **NFR-3** Trigger phrasing follows the #1068 disambiguation discipline.

---

## Acceptance criteria (Done when)

- [x] `bulk` and `catalog` appear in `plugin/skills/`, lint clean, and
  `sync_agents_skills.py --check` passes (mirrors regenerated).
- [x] `bulk` invokes `analyze_batch`; the tool resolves and the skill
  references only it.
- [x] `catalog` output matches `list_workflows()` / `list_wizards()` /
  live tool list at call time (via the `list_capabilities` tool;
  dogfooded: 22 workflows / 5 wizards / 43 tools).
- [x] `test_plugin_reference_validation` and `test_sync_agents_skills`
  pass; no count claims hand-authored in the skills.
- [x] README counts updated (43 tools, 20 skills); catalog renders
  counts from the live registry, not hand-authored.

---

## Out of scope

- `wizard` and `agent` skills → separate
  `interactive-orchestration-access` spec (interactive form engine /
  multi-step flows need a Claude-driven bridge).
- A standing "registry-coverage guard" test (catches future
  left-behind capability) — recommended follow-up, noted in decisions,
  not required for this spec.
