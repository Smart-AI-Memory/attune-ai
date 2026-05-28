# Decisions: Documentation Fiction Cleanup

This file records the per-doc retire/rewrite calls and the
triage that produced them.

---

## Triage of the 30 tracked stale docs (2026-05-28)

Each tracked doc (listed in a feature's `doc_paths`) was compared
against current source by an in-harness subagent. Result: 22 of
30 have real fact-drift (16 HIGH severity), 8 are formatting-only.

### Formatting-only (8) — out of scope, defer to normal regen

- `docs/how-to/memory-graph.md`
- `docs/how-to/unified-memory-system.md`
- `docs/reference/persistence.md`
- `docs/architecture/enhanced_escalation_architecture.md` (sketch)
- `docs/reference/agent-factory-api.md`
- `docs/reference/agent-factory-overview.md`
- `docs/reference/agent-factory-readme.md`
- `docs/how-to/resilience-patterns.md`

### Fact-drift HIGH (16) — copy-paste breaks

| Doc | What's wrong |
|-----|--------------|
| docs/how-to/short-term-memory-implementation.md | deleted `AgentCoordinator`/`AgentTask`/`TeamSession` |
| docs/reference/SHORT_TERM_MEMORY.md | same deleted coordination API + nonexistent methods |
| docs/how-to/context-management.md | `save_state`/`restore_latest`/`list_states` renamed |
| docs/how-to/learning-and-patterns.md | `extract`/`search`/`get_most_used` renamed or gone |
| docs/reference/pattern-library.md | `find_patterns`->`query_patterns`; `remove_pattern` gone |
| docs/how-to/multi-agent-coordination.md | `ConflictResolver()` deleted |
| docs/tutorials/META_ORCHESTRATION_TUTORIAL.md | fictional `attune orchestrate` CLI, `AGENT_REGISTRY`; "7 templates" (14) |
| docs/how-to/agent-factory.md | `attune_llm` import; mangled `Attune AIs` CLI |
| docs/how-to/smart-router.md | wizard->workflow rename breaks every example |
| docs/reference/cli-reference.md | dead `python -m attune.cli` / `attune.socratic` |
| docs/how-to/project-analysis-and-metrics.md | `ProjectSummary` fields renamed wholesale |
| docs/how-to/security-architecture.md | `attune_llm` + fictional `AccessControl`/`HealthcareWizard` |
| docs/architecture/PLUGIN_SYSTEM_README.md | fictional `BaseWizard`; real hook is `register_mcp_tools()` |
| docs/reference/wizards.md | entire API fictional (`attune_llm.wizards`) |
| docs/reference/software-wizards.md | entire API fictional (`coach_wizards`, 16 classes) |
| docs/how-to/webhook-integration.md | `attune.webhooks` package does not exist |

### Fact-drift MEDIUM (5) / LOW (1)

- MEDIUM: `docs/how-to/auto-chaining.md` (ChainTrigger fields),
  `docs/reference/multi-agent.md` (mkdocstrings points at wrong
  module), `docs/reference/llm-toolkit.md` (async `interact` +
  stale model IDs), `docs/how-to/telemetry-and-signals.md`
  (`record`->`track_llm_call`),
  `docs/reference/configuration.md` (`from_config`, default path).
- LOW: `docs/how-to/help-system-maintenance.md`
  (`help.jsonl`->`help_queries.jsonl`).

---

## Retire vs rewrite

### Retired (done 2026-05-28)

- **`docs/how-to/webhook-integration.md`** — RETIRED. 577 lines
  describing a fictional `attune.webhooks` package; real surface
  is one internal hook action, too thin for a standalone how-to.
  Removed from mkdocs nav, `features.yaml` (hooks doc_paths), and
  3 inbound links.
- **`docs/reference/software-wizards.md`** — RETIRED + merge.
  Near-duplicate of `wizards.md` (same fictional 16-class
  taxonomy). Real content (the 5 builtin wizards) folds into the
  `wizards.md` rewrite. Removed from `features.yaml` (wizards
  doc_paths) and 2 inbound links.

### Rewrite (real feature, fictional API)

- **`docs/how-to/security-architecture.md`** — rewrite against
  `SecurityAuditWorkflow` + `attune.security`
  (`PIIScrubber`/`SecretsDetector`/`AuditLogger`). High linkage
  (6 inbound), in nav.
- **`docs/architecture/PLUGIN_SYSTEM_README.md`** — rewrite to
  the workflow/MCP-centric model (`BasePlugin`, `BaseWorkflow`,
  `register_mcp_tools()`).
- **`docs/reference/wizards.md`** — rewrite to the real
  `attune.wizards` API (config-driven, `BaseWizard` lifecycle,
  module-level `list_wizards()`, 5 builtins). Absorb the
  salvageable parts of the retired `software-wizards.md`.

### attune_llm dead-import sweep (21 docs)

Mechanical for most: replace `attune_llm` -> `attune` and verify
the symbol still resolves at the new path. A few of these docs
(e.g. `hipaa-compliance.md`, `markdown-agents.md`,
`continuous-learning.md`) may themselves be fiction and warrant a
retire decision — to be triaged in Phase 2. See `tasks.md`.

---

## Open questions

- Which of the untracked `attune_llm` docs are salvageable
  (mechanical rename) vs fictional (retire)? Needs a Phase-2
  triage pass like the one done for the tracked 30.
- Should the two near-identical `webhook-event-integration.md`
  example docs (`docs/examples/` and `docs/tutorials/examples/`,
  both fictional `attune.webhooks`) be retired too? They are out
  of the tracked set; flagged for Phase 2.
