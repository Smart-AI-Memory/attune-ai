# Tasks: Documentation Fiction Cleanup

Phased so each phase ships independently and keeps
`mkdocs build --strict` green.

---

## Phase 0 — Retire pure fiction (DONE 2026-05-28)

- [x] Retire `docs/how-to/webhook-integration.md` (delete + nav +
  `features.yaml` + 3 inbound links).
- [x] Retire `docs/reference/software-wizards.md` (delete +
  `features.yaml` + 2 inbound links).
- [x] Verify no dangling refs; `features.yaml` parses.

Lives on branch `claude/exciting-chaum-3a59a5` (worktree),
pending commit + PR.

---

## Phase 1 — Rewrite the 3 real-feature docs

Each: read current source, write accurate doc, verify every
concrete claim, surface for review before finalizing.

- [x] Rewrite `docs/reference/wizards.md` to the real
  `attune.wizards` API; absorb salvageable `software-wizards.md`
  content (5 builtin wizards). Shipped 2026-05-30; flagged
  entry-point-group mismatch (`empathy.wizards` in registry.py vs
  `attune.wizards` in pyproject.toml) as a separate code-fix task.
- [x] Rewrite `docs/how-to/security-architecture.md` against
  `SecurityAuditWorkflow` + `attune.security`. Shipped 2026-05-30;
  blast-radius grep confirmed zero anchor deep-links (slug renames
  break nothing). HIPAA / encryption follow-ups for Phase 2 captured
  in `decisions.md` "Phase 2 preflight notes".
- [x] Rewrite `docs/architecture/PLUGIN_SYSTEM_README.md` to the
  `BasePlugin` / `register_mcp_tools()` model. Shipped 2026-05-30
  at new path `docs/architecture/plugin-system.md` (renamed for
  consistency with the rest of `docs/architecture/`). Inbound refs
  updated in `docs/ARCHITECTURE.md` and `.help/features.yaml`. Zero
  anchor deep-links existed, so the rename broke nothing.

---

## Phase 2 — attune_llm dead-import sweep (21 docs)

- [ ] Triage each `attune_llm`-referencing doc: mechanical
  rename (`attune_llm` -> `attune`, verify symbol) vs retire
  (doc is itself fiction).
- [ ] Apply renames; verify symbols resolve.
- [ ] Decide on the two `webhook-event-integration.md` example
  docs (retire vs rewrite-narrow).
- [ ] Triage the remaining MEDIUM/LOW fact-drift docs from
  `decisions.md` (auto-chaining, multi-agent, llm-toolkit,
  telemetry-and-signals, configuration, help-system-maintenance).

---

## Phase 3 — Fix the 16 HIGH fact-drift tracked docs

The non-fiction HIGH docs (renamed symbols, not fictional APIs)
— regen-via-attune-author candidates IF the project-doc regen
path works (verify on one doc first; note `doc-audit` SDK path is
blocked). Otherwise manual rewrite.

- [ ] Verify attune-author project-doc regen works on one
  low-risk doc.
- [ ] Regen or rewrite the memory cluster, smart-router,
  cli-reference, project-analysis, agent-factory how-to.

---

## Guardrail idea (optional)

- [ ] Add a CI check that greps `docs/` (excluding `archive/`)
  for dead import prefixes (`attune_llm`, `coach_wizards`,
  `attune.webhooks`) and fails if any reappear. Prevents
  regression once the sweep is done.
