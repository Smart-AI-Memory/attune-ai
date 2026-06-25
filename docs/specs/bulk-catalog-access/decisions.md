# Bulk + Catalog Access — Decisions

---

## D1 — Scope: bulk + catalog only; wizard + agent deferred

**Decided (Patrick, 2026-06-25).** The four left-behind skills do not
share a cost class. `bulk` (backed by the existing `analyze_batch` tool)
and `catalog` (a registry read) are clean. `wizard` and `agent` are
*interactive orchestration* — no CLI/MCP path, driven by a form engine /
multi-step flows that a single-shot MCP call cannot drive. They move to a
separate `interactive-orchestration-access` spec that solves the
"multi-step-through-Claude" bridge once for both.

## D2 — Author in `plugin/skills/`, not by copying `.claude/skills/`

**Decided.** `plugin/skills/` is the shipped source of truth; the
`.claude/skills/` versions use legacy frontmatter (`category`, `aliases`,
`version`, `question:` picker) that the plugin convention and the sync
script do not carry. Adapt the *content*, rewrite the *frontmatter* to
the shipped shape (`name`, trigger-bearing `description`,
`argument-hint`).

## D-CAT — Catalog data path: thin `list_capabilities` MCP tool

**Agent recommendation.** Add a read-only `list_capabilities` MCP tool
returning the live `list_workflows()` / `list_wizards()` / tool-dispatch
keys, so the catalog renders from registries at call time (NFR-2) and
Claude doesn't shell out. ~30 lines, no engine code. Rejected
alternative D-CAT-b (CLI-only `attune features`): no new code, but
CLI-shaped output and wizards aren't in the CLI today, so the catalog
would be incomplete. Open for review (OQ1).

## D3 — Catalog vs attune-hub boundary

**Decided.** `attune-hub` routes ("where do I start"); `catalog`
enumerates ("show me everything"). Triggers partitioned accordingly so
the two don't shadow each other.

## D4 — Help topics optional

**Decided.** Both skills ship a literal fallback preamble, so missing
`help_lookup` topics degrade gracefully. Real help topics are a
follow-up, not a blocker.

---

## Open for review

- **OQ1:** Confirm D-CAT-a (thin `list_capabilities` MCP tool) vs D-CAT-b
  (CLI-only). The tool is the accurate path but is net-new (small) code.
- **OQ2:** Should the standing **registry-coverage guard** (a test that
  fails when a workflow/wizard/tool has no surface — would have caught
  all of discovery-sweep, bulk, catalog) be folded into this spec, or
  tracked as its own follow-up? Recommendation: its own follow-up, since
  it is a process control, not part of shipping these two skills.
