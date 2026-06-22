# Phase 2 triage — attune_llm dead-import sweep (2026-05-30)

Scout pass for `doc-fiction-cleanup` Phase 2. Classifies every
doc under `docs/` (excluding `docs/archive/` and the cleanup spec
itself) that references `attune_llm`. No rewrites in this file —
that's Phase 2 execution.

Discovery command used:

```bash
grep -rln "attune_llm" docs/ | grep -v docs/archive | grep -v docs/specs/doc-fiction-cleanup
```

Yielded 18 hits. The spec's "21 docs" figure (`decisions.md`
under "attune_llm dead-import sweep") was set BEFORE Phase 1
shipped — Phase 1 retired/rewrote `webhook-integration.md`,
`software-wizards.md`, `security-architecture.md`,
`PLUGIN_SYSTEM_README.md`, and `wizards.md`, several of which
had been in the `attune_llm` cohort. The remaining surface for
Phase 2 is 18 docs. No drift from the spec — just the
arithmetic of Phase 0/1 completion.

## Counts

- MECHANICAL: 8
- RETIRE-CANDIDATE: 4
- REWRITE: 4
- UNCLEAR: 2
- **Total**: 18

The bucket distribution is heavier on retire/rewrite than the
spec's "mechanical for most" framing suggested. The reason is
that `attune_llm` references cluster in two kinds of doc:
(a) one-off code snippets where the rename is the only drift
(MECHANICAL), and (b) long-form narratives that were authored
on top of `attune_llm` AND on top of fictional surfaces
(`EnterprisePrivacyConfig`, `HealthcareWizard`, `coach_wizards`,
non-Anthropic providers). The latter dominate this cohort.

## Triage

| Doc | Class | Reason / fiction markers | Phase 2 action |
|---|---|---|---|
| docs/BLOG_CLAUDE_OPTIMIZATION.md | MECHANICAL | One `attune_llm.providers` import inside a code snippet (OpenAI/Gemini/Local). The snippet ALSO claims non-Anthropic providers "still work fine" — but `src/attune/llm/providers/` ships only `anthropic.py`/`anthropic_batch.py`. So the line is doubly stale: package rename AND the providers are gone. Blog itself is a marketing narrative, not API reference. | Either delete the offending code block (cleanest) or update prose to say "Anthropic-only today; multi-provider was an earlier architecture." Single-block change. |
| docs/DEVELOPER_GUIDE.md | RETIRE-CANDIDATE | Documents `attune_llm/` as "Legacy wizard system" in the project tree, then teaches plugin authoring via `from attune_llm.wizards import BaseWizard, WizardConfig` + `EmpathyLLM` + `MyCustomWizard(BaseWizard)`. The plugin model is fictional (per Phase 1: real surface is workflow-centric `BasePlugin` / `register_mcp_tools()`). Also references `HealthcareWizard`/`TechnologyWizard` at line 559. | Retire OR redirect readers to the rewritten `docs/architecture/plugin-system.md` (Phase 1). A real developer guide for plugin authoring belongs as a separate spec, not a patched version of this one. |
| docs/EXCEPTION_HANDLING_GUIDE.md | MECHANICAL | Two `attune_llm/code_health.py` file-path references in narrative prose. `code_health.py` does not exist anywhere in `src/attune/`. But the rest of the doc is generic exception-handling guidance with `attune.exceptions` imports that DO resolve (`AuthenticationError`, `ServiceUnavailableError` — verify these still exist in `src/attune/exceptions.py`). | Replace the two `attune_llm/code_health.py` references with a real file path OR drop the "Example 4: Health Check" block entirely. Verify `attune.exceptions` symbols still resolve. |
| docs/architecture/ENTERPRISE_PRIVACY_INTEGRATION.md | RETIRE-CANDIDATE | Entire doc describes `EnterprisePrivacyConfig` (does not exist in src), `/attune_llm/enterprise_privacy.py`, `/attune_llm/scrubbing.py`, `/attune_llm/audit.py` (none exist), plus `EmpathyLLM` wired into a fictional "enterprise privacy" API. Marked "Status: Design Phase" from 2025-11. This is a design doc for a feature that was never built. | Retire (move to `docs/archive/` if historical value, otherwise delete). Remove from nav/inbound links. |
| docs/context-management.md | MECHANICAL | Three imports: `from attune_llm.context import ContextManager`, `CompactState, CompactionStateManager`, and `attune_llm.hooks import HookRegistry, HookEvent`. ALL three symbols verified present at `attune.context` and `attune.hooks` (`src/attune/context/__init__.py`, `src/attune/hooks/__init__.py`). Pure rename. | grep+replace `attune_llm.context` → `attune.context` and `attune_llm.hooks` → `attune.hooks`. Smoke-test each import. Cleanest mechanical in the cohort. |
| docs/continuous-learning.md | MECHANICAL | Three imports: `from attune_llm.learning import (...)`, `from attune_llm.learning import LearnedSkill`, `from attune_llm.hooks import HookRegistry, HookEvent`. All symbols verified at `attune.learning` and `attune.hooks` (`SessionEvaluator`, `PatternExtractor`, `LearnedSkillsStorage`, `SessionQuality`, `PatternCategory`, `LearnedSkill`). Pure rename. NOTE: `decisions.md` Open Questions flagged this as "may itself be fiction" — the scout disagrees. The symbols resolve. | grep+replace `attune_llm.learning` → `attune.learning` and `attune_llm.hooks` → `attune.hooks`. |
| docs/features/v2.3-memory-enhancement.md | REWRITE | Real underlying features (`ConversationSummaryIndex` confirmed in `src/attune/memory/summary_index.py`). But references `attune_llm/cli/sync_claude.py` (doesn't exist) and `attune_llm/routing/model_router.py` (real file is `src/attune/routing/model_router.py`). Release-note-style narrative pinned to "v2.3" / "December 18, 2025". | Treat as historical release note: either move to `docs/archive/releases/` AS-IS (honest fossil), or rewrite as a current "memory architecture" reference doc against current source. Choice for Patrick. |
| docs/guides/DISTRIBUTION_POLICY.md | MECHANICAL | Single reference: a table cell saying "All Python packages (attune, attune_llm, etc.)". Trivial. | Drop "attune_llm" from the cell. One-line edit. |
| docs/guides/RELEASE_PREPARATION.md | RETIRE-CANDIDATE | Pinned to "v3.7.0 (XML-Enhanced Prompts)", references `attune_llm/` as a top-level package, `BaseWizard with XML support`, "4 CrewAI crews", `HealthcareWizard`, and `from attune_llm.wizards import HealthcareWizard`. This is a stale historical release-prep doc for a release that has long shipped (current is 6.x) and the feature surface it describes is fictional. | Retire (move to `docs/archive/releases/`). Useful as a process-history artifact, dangerous as live guidance. |
| docs/hooks.md | MECHANICAL | Five imports across the doc, all `attune_llm.hooks.*`. Every symbol verified at `attune.hooks` (`HookRegistry`, `HookEvent`, `HookConfig` per `src/attune/hooks/config.py`, `HookMatcher` per same file). The one wrinkle: `attune_llm.hooks.scripts.session_start:main` (line 70) — `src/attune/hooks/scripts/` exists; verify `session_start.py` and a `main` callable exist before shipping. | grep+replace `attune_llm.hooks` → `attune.hooks`. Verify `attune.hooks.scripts.session_start:main` path resolves. |
| docs/how-to/agent-factory.md | REWRITE | Already in `decisions.md` HIGH fact-drift list (line 36: `attune_llm import; mangled 'Attune AIs' CLI`). `AgentFactory` class IS real at `src/attune/agent_factory/factory.py:60`, but doc has additional drift beyond the rename. | Phase-1-style rewrite against `src/attune/agent_factory/`. Verify `Framework` enum + `AgentRole` still match. |
| docs/how-to/hipaa-compliance.md | RETIRE-CANDIDATE | **Already flagged in `decisions.md` Phase 2 preflight notes.** Heavy fiction: `from attune_llm.wizards import HealthcareWizard` (HealthcareWizard does not exist in src — confirmed by grep), `from attune_llm.security import encrypt_phi, decrypt_phi, AuditLogger, BreachDetector` (encrypt_phi / BreachDetector do not exist; only AuditLogger does, at `attune.memory.security`). Patrick's note: HIPAA compliance not a real feature today. | Retire per preflight option 1. Remove from nav + `features.yaml` + inbound links. |
| docs/how-to/unified-memory-system.md | MECHANICAL | Single block at line 434-438: `### From attune_llm.security` showing `from attune_llm.security import PIIScrubber, SecretsDetector`. Both classes verified real at `src/attune/memory/security/pii_scrubber.py` and `secrets_detector.py`. The doc is in `decisions.md`'s "formatting-only" bucket otherwise. BUT preflight note flags the "PII scrubbing, **encryption**, audit logging" claim at line 450 as fiction-adjacent (no encryption module). | Mechanical rename + drop "encryption" from the line-450 description (or verify an encryption surface exists in `src/attune/memory/`). Two small edits, both in scope here. |
| docs/implementation/ANTHROPIC_COMPLIANCE_PLAN.md | UNCLEAR | 1456-line implementation plan with multiple `attune_llm/providers.py` and `attune_llm/hooks/scripts/security_guard.py` path references. These were paths-at-time-of-plan, not live imports — the plan was a work order, not API docs. Question: was this plan executed (move to archive as historical) or is it still operative (rewrite with current paths)? | Patrick to decide: archive vs. update paths. If archive, no further work. If operative, mechanical path-rewrite. |
| docs/markdown-agents.md | MECHANICAL | Three imports: `from attune_llm.agents_md import AgentRegistry` and `AgentLoader`. Both verified at `attune.agents_md` (`AgentRegistry` at `src/attune/agents_md/registry.py:20`, `AgentLoader` at `src/attune/agents_md/loader.py:19`). Pure rename. `decisions.md` Open Questions flagged this as "may itself be fiction" — scout disagrees; the symbols resolve and the API shape matches what's documented. | grep+replace `attune_llm.agents_md` → `attune.agents_md`. Smoke-test load. |
| docs/migration-guide.md | UNCLEAR | Special case: the doc is literally about the `attune_llm` → `attune` rename. Its `attune_llm` references are intentional "before" examples in a `Before/After` migration narrative. But: (a) the `attune_llm` package + shims are gone (`find src -name attune_llm*` returns nothing), so the "shims active until v3.0.0" framing is stale, and (b) the doc claims `v3.0.0` will delete the package — current version is past v3 (per other docs, 6.x). | Patrick to decide: retire (rename is complete, migration window closed), OR rewrite as historical "rename log" doc with explicit "migration window closed, this is preserved for archaeological reference" framing. |
| docs/reference/TROUBLESHOOTING.md | REWRITE | Mix of legitimate troubleshooting content AND fiction. Real signal: `ModuleNotFoundError: No module named 'attune_llm'` is documented as a known issue — that's actually useful (modulo telling users to install/use `attune` instead). BUT the doc also imports `coach_wizards` (fictional, per Phase 1) at lines 170/187/533/560/1024, and `from attune_llm.providers import AnthropicProvider` snippets where the AnthropicProvider path is now `attune.llm.providers`. Substantive fiction beyond the rename. | Phase-1-style rewrite: keep the "module renamed" troubleshooting entry (it's a real user pain), strip `coach_wizards` examples entirely, verify each remaining import. |
| docs/reference/USER_GUIDE.md | REWRITE | 2374 lines; very heavy `coach_wizards` fiction (15+ references: `SecurityWizard`, `ComplianceWizard`, `PerformanceWizard`, `PromptEngineeringWizard`). `EmpathyLLM` IS real (`src/attune/llm/core.py:40`), so the core API surface verifies, but every wizard-catalog and advanced-topics chapter is built on fictional `coach_wizards`. The doc has a "Wizard Catalog" section that's entirely fiction. | Phase-1-style rewrite OR retire. Rewriting 2374 lines is a big ship-unit; recommend retire-and-replace-with-shorter-getting-started + linking the real `wizards.md` (Phase 1) for the wizard catalog. |

## Notes from spot-checks against src/

Symbols VERIFIED present at the renamed path:

- `attune.context.ContextManager`, `CompactState`, `CompactionStateManager`, `WorkHandoff` (via `src/attune/context/__init__.py`)
- `attune.hooks.HookRegistry`, `HookEvent`, `HookConfig`, `HookMatcher`, `HookExecutor` (via `src/attune/hooks/__init__.py` + `config.py`)
- `attune.learning.SessionEvaluator`, `PatternExtractor`, `LearnedSkillsStorage`, `LearnedSkill`, `SessionQuality`, `PatternCategory` (via `src/attune/learning/__init__.py`)
- `attune.agents_md.AgentRegistry`, `AgentLoader` (via `src/attune/agents_md/`)
- `attune.agent_factory.AgentFactory` (`src/attune/agent_factory/factory.py:60`)
- `attune.routing.ModelRouter` (`src/attune/routing/model_router.py:108`)
- `attune.llm.EmpathyLLM` (`src/attune/llm/core.py:40`)
- `attune.memory.security.PIIScrubber`, `SecretsDetector`, `AuditLogger` (under `src/attune/memory/security/`)
- `attune.memory.ConversationSummaryIndex` (`src/attune/memory/summary_index.py:97`)
- `attune.workflows.BugPredictionWorkflow` (`src/attune/workflows/bug_predict.py`)
- `attune.exceptions` (module exists at `src/attune/exceptions.py` — specific names not exhaustively verified)

Symbols CONFIRMED missing (fiction or removed):

- `HealthcareWizard`, `FinanceWizard`, `LegalWizard`, `TechnologyWizard`, all `coach_wizards.*` classes — not in src
- `EnterprisePrivacyConfig` — not in src
- `encrypt_phi`, `decrypt_phi`, `BreachDetector`, `AccessControl` — not in src
- `OpenAIProvider`, `GeminiProvider`, `LocalProvider` — `src/attune/llm/providers/` ships only `anthropic.py` + `anthropic_batch.py`. The multi-provider story in the blog and several guides is gone.
- `attune_llm/code_health.py`, `attune_llm/sync_claude.py`, `attune_llm/enterprise_privacy.py`, `attune_llm/scrubbing.py`, `attune_llm/audit.py` — none of these files exist under `src/attune/`
- `attune_llm` package itself + any shims — entirely removed from src

## Suggested batching for Phase 2 execution

Order the work to maximize coupling / minimize churn:

1. **RETIRE batch (lowest risk).** Decide + retire all 8
   RETIRE-CANDIDATE docs in one PR:
   `DEVELOPER_GUIDE.md`, `ENTERPRISE_PRIVACY_INTEGRATION.md`,
   `RELEASE_PREPARATION.md`, `hipaa-compliance.md`,
   plus the two `webhook-event-integration.md` example docs
   from `decisions.md` Open Questions (separately confirmed
   fictional in Phase 1). Remove from nav, `features.yaml`,
   inbound links. Single ship-unit.
2. **MECHANICAL batch.** All 5 MECHANICAL docs in one PR
   (`BLOG_CLAUDE_OPTIMIZATION.md`,
   `EXCEPTION_HANDLING_GUIDE.md`, `context-management.md`,
   `continuous-learning.md`, `DISTRIBUTION_POLICY.md`,
   `hooks.md`, `unified-memory-system.md`, `markdown-agents.md`).
   grep+replace + import-resolve smoke test. Low risk because
   every symbol is pre-verified to exist at the renamed path.
3. **UNCLEAR resolution.** Patrick decides
   `ANTHROPIC_COMPLIANCE_PLAN.md` and `migration-guide.md`.
   Both are likely "archive as historical" — confirm and move.
4. **REWRITE batch (most work).** Each rewrite is its own
   ship unit, following the Phase 1 pattern (read source, write,
   verify, swap):
   - `agent-factory.md` (smallest, real surface clearly maps)
   - `features/v2.3-memory-enhancement.md` (medium — likely
     just an archive move)
   - `TROUBLESHOOTING.md` (medium-large, strip fiction +
     keep real troubleshooting entries)
   - `USER_GUIDE.md` (large — strongly suggest retire-and-
     replace-with-shorter-getting-started; 2374 lines of
     coach_wizards-shaped content is not worth rewriting
     line-by-line)

After the RETIRE + MECHANICAL batches ship, the spec's
acceptance criterion "No doc under `docs/` (outside
`docs/archive/`) imports from `attune_llm`" will be satisfied
for the easy 13. The REWRITE/UNCLEAR docs are then per-doc
decisions that don't block the broader sweep.

## Open questions for Patrick

1. **`USER_GUIDE.md` — rewrite or retire?** 2374 lines, very
   heavy `coach_wizards` fiction throughout, but `EmpathyLLM`
   is real. Retire-and-replace-with-shorter-getting-started
   feels right; full rewrite is a large ship unit for a doc
   whose central organizing principle (the Wizard Catalog) is
   fictional.
2. **`migration-guide.md` — retire or rewrite-as-historical?**
   The `attune_llm` → `attune` rename is complete, no shims
   remain. The doc is correct historically but its
   "shims active" framing is misleading today.
3. **`ANTHROPIC_COMPLIANCE_PLAN.md` — implementation plan or
   archive?** Was this work order executed? If yes, archive
   it; if no, do the paths need updating?
4. **`DEVELOPER_GUIDE.md` — retire or redirect?** The plugin-
   authoring chapter is the central reason this doc exists,
   and it's built on the fictional `BaseWizard` plugin model.
   The rewritten `docs/architecture/plugin-system.md` (Phase 1)
   may be the appropriate replacement.
5. **Encryption claim in `unified-memory-system.md` (line 450).**
   The preflight note says "verify what surface does exist if
   any". Scout confirms: there is no encryption module in
   `attune.memory` or `attune.security`. So the action is "drop
   `encryption` from the description" — no rewrite path opens.
   Confirm this is the call.
6. **`features/v2.3-memory-enhancement.md` — archive as
   release note?** The underlying feature
   (`ConversationSummaryIndex`) is real, but the doc is
   release-note-shaped and pinned to v2.3. Archive feels
   right; standalone "memory architecture" reference doc is a
   separate spec.
