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

## Resolved (was "Open for review")

- **OQ1 — RESOLVED (Patrick, 2026-06-25): D-CAT-a.** Ship the thin
  read-only `list_capabilities` MCP tool. The accurate, registry-driven
  path (wizards aren't in the CLI; NFR-2 forbids drift) outweighs the
  small net-new code. Implemented in `get_utility_tools()` +
  `_handle_list_capabilities` (`server.py`).
- **OQ2 — RESOLVED: its own follow-up, and already shipped.** The
  standing **registry-coverage guard** landed separately as PR #1079
  (`tests/unit/plugins/test_registry_coverage.py`) before this work. It
  actively guided this change: its hygiene check forced `analyze_batch`
  out of the tool allowlist once the `bulk` skill surfaced it.
