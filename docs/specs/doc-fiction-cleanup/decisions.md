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

- ~~Which of the untracked `attune_llm` docs are salvageable
  (mechanical rename) vs fictional (retire)?~~ **Resolved
  2026-05-30** by Phase 2 triage scout — see `phase-2-triage.md`.
  18-doc cohort classified into 4 buckets. Scout disagreed with
  the speculative "may be fiction" flag on `continuous-learning.md`
  and `markdown-agents.md` — both are MECHANICAL (every symbol
  resolves at `attune.learning` / `attune.agents_md`).
- Should the two near-identical `webhook-event-integration.md`
  example docs (`docs/examples/` and `docs/tutorials/examples/`,
  both fictional `attune.webhooks`) be retired too? They are out
  of the tracked set; flagged for Phase 2. *(Still open;
  out-of-cohort.)*

## Phase 2 outcomes (2026-05-30, PR-A — RETIRE + ARCHIVE batch)

### Retired (deleted)

- **`docs/how-to/hipaa-compliance.md`** — preflight Option 1.
  No standalone HIPAA-compliance feature ships today; the doc
  overpromised. Removed from nav + `features.yaml` + inbound refs
  in `how-to/index.md`, `examples/sbar-clinical-handoff.md`,
  `tutorials/examples/sbar-clinical-handoff.md`.
- **`docs/architecture/ENTERPRISE_PRIVACY_INTEGRATION.md`** —
  describes `EnterprisePrivacyConfig` (never built), marked
  "Status: Design Phase" 2025-11. Removed from `features.yaml`.
- **`docs/guides/RELEASE_PREPARATION.md`** — pinned to v3.7.0
  with `HealthcareWizard` smoke tests; release long shipped.
  Removed from nav. Historical reference left untouched in
  `docs/specs/deprecated-module-retirement/tasks.md:35` (closed
  task; revisionism would be worse than the dangling note).
- **`docs/migration-guide.md`** — the rename window closed
  (current version is past v3, shims gone). Doc misleads about
  the timeline. Removed from nav.
- **`docs/reference/USER_GUIDE.md`** — 2374 lines with heavy
  `coach_wizards` fiction. Retired without replacement this PR;
  follow-up task to author a thinner `getting-started.md` left
  for a separate spec (deferred consciously rather than rushing a
  thin replacement into this PR).

### Archived (moved to `docs/archive/`)

- **`docs/implementation/ANTHROPIC_COMPLIANCE_PLAN.md`** →
  `docs/archive/implementation/`. 1456-line implementation plan
  with `attune_llm/providers.py` paths that no longer exist;
  treated as historical fossil. Original `docs/implementation/`
  directory left in place for any future plan.
- **`docs/features/v2.3-memory-enhancement.md`** →
  `docs/archive/releases/`. Release-note style narrative pinned
  to "v2.3 / December 2025"; preserved as a historical fossil
  rather than rewritten as competing memory-architecture
  reference.

### Replaced with stub

- **`docs/DEVELOPER_GUIDE.md`** — replaced with a short redirect
  pointing readers at the Phase 1 outputs (`plugin-system.md`,
  `wizards.md`, `security-architecture.md`). A full Developer
  Guide may be authored in a future spec; this stub ensures the
  inbound link from `PROJECT_OVERVIEW.md:454` still resolves.

### Build verification

- `mkdocs build --strict` passes; pre-existing anchor warnings
  in `API_REFERENCE.md` and related docs are unrelated to this
  PR (long-standing issue, not introduced or worsened here).
- Grep sanity: zero remaining inbound references to the 5 retired
  docs outside of (a) the cleanup spec itself, (b) the
  `docs/archive/` tree, and (c) the historical
  `deprecated-module-retirement/tasks.md:35` note (intentional).

## Phase 2 outcomes (2026-05-30, PR-B — MECHANICAL batch)

### Renamed (5 docs, pure `attune_llm` → `attune` rename)

- **`docs/context-management.md`** — 3 imports renamed; all
  symbols (`ContextManager`, `CompactState`, `CompactionStateManager`,
  `HookRegistry`, `HookEvent`) resolve at the new paths.
- **`docs/continuous-learning.md`** — 3 imports renamed; all
  symbols (`SessionEvaluator`, `PatternExtractor`,
  `LearnedSkillsStorage`, `SessionQuality`, `PatternCategory`,
  `LearnedSkill`, `HookRegistry`, `HookEvent`) verified present.
  This closes the previously-open "may be fiction" question on
  this doc — scout was correct, every symbol resolves.
- **`docs/hooks.md`** — 4 imports renamed (`HookRegistry`,
  `HookEvent`, `HookConfig`, `HookMatcher`). One example
  pointer broken even after rename: replaced
  `attune_llm.hooks.scripts.session_start:main` with
  `attune.hooks.scripts.first_time_init:main` (real script in
  the same dir; semantically aligned for SessionStart events;
  `session_start.py` does not exist in current source).
- **`docs/markdown-agents.md`** — 3 imports renamed
  (`AgentRegistry`, `AgentLoader`). Closes the second
  previously-open "may be fiction" question — scout was correct.
- **`docs/how-to/unified-memory-system.md`** — 2 imports renamed
  (`PIIScrubber`, `SecretsDetector` from `attune.security`).
  Also: dropped "encryption" from the inline description of
  `security-architecture.md` at line ~450 (no encryption module
  exists; was overpromising) per Phase 2 preflight note.

### Pruned fiction (3 docs, partial cleanup)

- **`docs/EXCEPTION_HANDLING_GUIDE.md`** — deleted the entire
  35-line "Example 4: Health Check with Specific Handlers"
  section (referenced `attune_llm/code_health.py:393`;
  `code_health.py` does not exist in source). Also removed the
  bullet pointing to `attune_llm/code_health.py` in the
  "Codebase Examples" section. Examples 1, 2, 3, and 5 retained
  (Example 5 auto-renumbered to 4 by markdown convention; no
  inbound deep-links to anchors).
- **`docs/BLOG_CLAUDE_OPTIMIZATION.md`** — deleted a 3-line
  fenced code block `from attune_llm.providers import
  OpenAIProvider, GeminiProvider, LocalProvider`. The multi-
  provider story is broader fiction than the rename (real
  surface is Anthropic-only today), but the surrounding prose
  + table are left intact for the BLOG owner to revisit
  separately. Scope-bounded to the import-line fiction.
- **`docs/guides/DISTRIBUTION_POLICY.md`** — single trivial
  change: `(attune, attune_llm, etc.)` → `(attune, etc.)` in
  a table cell.

### Verification

- Net diff: -41 lines (18 insertions, 59 deletions).
- `mkdocs build --strict` passes.
- Grep sanity: remaining `attune_llm` references confined to
  (a) `docs/archive/` (intentional fossils), (b) the cleanup
  spec itself, (c) the pending REWRITE targets `agent-factory.md`
  and `TROUBLESHOOTING.md` (Phase 2 PR-C and Phase 3 respectively).

---

## Phase 2 preflight notes (2026-05-30)

Caught during Phase 1 review; carries forward as constraint when
Phase 2 triages these specific docs.

- **`docs/how-to/hipaa-compliance.md`** — Patrick (2026-05-30):
  *"we don't absolutely have HIPAA compliance the way we used to."*
  Phase 2 triage cannot assume the doc can be rewritten to a still-real
  HIPAA-compliance feature surface. Likely outcomes, in order of
  preference:
  1. **Retire.** No standalone HIPAA-compliance feature ships today;
     the doc as it stands overpromises. Remove from nav + features.yaml
     + inbound links.
  2. **Rewrite-narrow.** If primitives in `attune.security` (PII
     scrubber, audit logger) are useful *building blocks* for HIPAA
     workflows without being compliance themselves, rewrite as a
     "Building blocks for HIPAA-adjacent workflows" how-to with
     explicit "this is not a compliance claim" framing. Verify against
     source before going this route.
  3. **Keep current** — not viable; the doc is fiction-adjacent and
     a copy-paste hazard for users in regulated environments.
- **`docs/how-to/unified-memory-system.md`** — line 450 describes
  `security-architecture.md` as covering "PII scrubbing, **encryption**,
  audit logging." Encryption is fiction-adjacent (no real encryption
  module in `attune.security`). Phase 2 triage of this doc must update
  the description to drop "encryption" or document what surface does
  exist if any (verify against `src/attune/memory/`).
