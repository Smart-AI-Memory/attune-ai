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

## Phase 2 — attune_llm dead-import sweep (18 docs, scout 2026-05-30)

- [x] Triage each `attune_llm`-referencing doc: mechanical
  rename (`attune_llm` -> `attune`, verify symbol) vs retire
  (doc is itself fiction). Done 2026-05-30 — see
  [`phase-2-triage.md`](phase-2-triage.md) (18 docs classified;
  fewer than the spec's 21-doc estimate). Buckets: 8 MECHANICAL,
  4 RETIRE-CANDIDATE, 4 REWRITE, 2 UNCLEAR. Scout disagreed with
  `decisions.md` "Open Questions" on `continuous-learning.md` and
  `markdown-agents.md` — both are MECHANICAL, every symbol resolves.
- [x] **RETIRE + ARCHIVE batch (PR-A, 2026-05-30):** retired
  `hipaa-compliance.md`, `ENTERPRISE_PRIVACY_INTEGRATION.md`,
  `guides/RELEASE_PREPARATION.md`, `migration-guide.md`,
  `reference/USER_GUIDE.md`; archived `ANTHROPIC_COMPLIANCE_PLAN.md`
  and `features/v2.3-memory-enhancement.md` under `docs/archive/`;
  replaced `DEVELOPER_GUIDE.md` with a redirect stub pointing at
  Phase 1's `plugin-system.md`/`wizards.md`/`security-architecture.md`.
  Inbound refs cleaned in `mkdocs.yml` (4 nav entries), `.help/features.yaml`
  (3 entries), `how-to/index.md`, both `sbar-clinical-handoff.md`,
  `how-to/telemetry-and-signals.md`, `reference/index.md`. `mkdocs build --strict`
  passes.
- [x] **MECHANICAL batch (PR-B, 2026-05-30):** 8 docs renamed
  `attune_llm` → `attune` with per-import verification.
  Net -41 lines. Renamed: `context-management.md` (3 imports),
  `continuous-learning.md` (3 imports), `hooks.md` (4 imports
  + replaced broken `session_start:main` with real
  `first_time_init:main`), `markdown-agents.md` (3 imports),
  `unified-memory-system.md` (2 imports + dropped "encryption"
  from line 450 per Phase 2 preflight). Pruned: a 35-line
  fictional `Example 4: Health Check` block in
  `EXCEPTION_HANDLING_GUIDE.md` (`attune_llm/code_health.py`
  doesn't exist); a 3-line broken multi-provider import snippet
  in `BLOG_CLAUDE_OPTIMIZATION.md`; one `attune_llm` mention
  in `guides/DISTRIBUTION_POLICY.md`. `mkdocs build --strict`
  passes. Zero remaining `attune_llm` references outside
  `docs/archive/`, the cleanup spec, and the pending REWRITE
  targets (agent-factory.md, TROUBLESHOOTING.md).
- [ ] **REWRITE batch (PR-C, ≤1 doc this session):**
  `agent-factory.md` recommended. Deferred to Phase 3:
  `TROUBLESHOOTING.md` (mixed real troubleshooting + fiction;
  needs careful surgery).
- [ ] Decide on the two `webhook-event-integration.md` example
  docs (retire vs rewrite-narrow). *Open from prior phase; not
  in the attune_llm cohort.*
- [ ] Triage the remaining MEDIUM/LOW fact-drift docs from
  `decisions.md` (auto-chaining, multi-agent, llm-toolkit,
  telemetry-and-signals, configuration, help-system-maintenance).
  *Open from prior phase; not in the attune_llm cohort.*

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
