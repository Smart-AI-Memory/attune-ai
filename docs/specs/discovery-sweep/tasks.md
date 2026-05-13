# Tasks — Discovery Sweep

**Status:** approved — nothing shipped

Phased plan. Each phase is independently shippable. See `decisions.md`, `requirements.md`, `design.md` for context.

> **DECIDE callouts** are spread across this file and the design docs. Resolve the relevant ones before starting each phase.

---

## Phase 1 — Engine + first non-LLM source

Goal: prove the engine + Protocol + verification rules + CLI integration end-to-end on the cheapest source (pattern scanning). Ships a usable `attune workflow run discovery-sweep --path X --no-llm` even before any LLM adapter exists.

- [ ] **1.1** Create `src/attune/workflows/discovery_sweep/` package skeleton. Empty `__init__.py`, stub `workflow.py`, stub `cli_workflow.py`, `sources/` subpackage.
- [ ] **1.2** Define `Finding`, `QuestionFinding`, `RejectedFinding`, `SweepResult`, `SweepMetadata` dataclasses in `workflow.py`. All frozen where appropriate.
- [ ] **1.3** Define `FindingSource` Protocol in `workflow.py` (`@runtime_checkable`, async `discover(path, budget_usd) -> list[Finding]`).
- [ ] **1.4** Implement `verification.py` — the five routing rules from `design.md` § Verification rules. Pure functions, no I/O, no LLM. Unit tests cover each rule + interactions.
- [ ] **1.5** Implement `DiscoverySweepWorkflow.execute()` in `workflow.py`:
      - Accept `path`, `budget_usd` (default 10.00), `sources` (default `None` → use `default_sources()`), `no_llm` (default False).
      - Allocate budget across sources, `asyncio.gather` with `return_exceptions=True`.
      - Run verification, build `SweepResult`.
      - Return `WorkflowResult` whose `final_output` is the human-readable markdown rendering AND whose `metadata` carries the structured `SweepResult` for JSON output.
- [ ] **1.6** Implement `PatternScanSource` in `sources/pattern_scan.py`. Wraps existing pattern scanning (find the existing scanner — likely in `src/attune/workflows/bug_predict_patterns.py` or `src/attune/security/` — and adapt). `name = "pattern-scan"`, `is_llm = False`. Returns `Finding` objects directly. Ignores `budget_usd`.
- [ ] **1.7** Register `DiscoverySweepWorkflow` in `src/attune/workflows/__init__.py` (lazy import + `_DEFAULT_WORKFLOW_NAMES`). Add to `PATH_ARG_REGISTRY` in `src/attune/ops/data.py` (Category A: takes `path` kwarg).
- [ ] **1.8** CLI smoke test: `attune workflow run discovery-sweep --path tests/fixtures/ --no-llm` returns a SweepResult with at least one finding from the pattern source.
- [ ] **1.9** Tests:
      - `test_engine.py` — happy path with two fake sources, one returning findings, one raising
      - `test_verification.py` — each rule in isolation + the routing-order interaction
      - `test_pattern_scan_source.py` — runs against a fixture file with a known pattern hit
      - `test_discovery_sweep_registered.py` — drift guard: workflow appears in `list_workflows()` and `PATH_ARG_REGISTRY`
- [ ] **1.10** Update CHANGELOG `[Unreleased]` § Added: discovery-sweep engine + PatternScanSource (no LLM).

---

## Phase 2 — LLM source adapters + retirement evaluation

Goal: wrap each audit-family workflow as a `FindingSource`. Each is an independent sub-PR.

### Phase 2A — Shared LLM adapter infrastructure

- [ ] **2A.1** Implement `llm_source_base.py`:
      - `STRUCTURED_EMIT_FOOTER` constant (the prompt-augmentation string from design.md)
      - `parse_findings_json(text, source_name) -> list[Finding]` with text-only fallback
      - Optional `LLMSource` marker mixin (`is_llm = True`)
- [ ] **2A.2** Tests for `parse_findings_json`: well-formed block, malformed JSON, missing block, multiple blocks (use last), block with extra prose. Each → expected Finding list.
- [ ] **2A.3** CHANGELOG: shared LLM adapter base shipped (no user-visible behavior change).

### Phase 2B — Per-source adapters (one PR each)

Each sub-task ships an adapter that:

1. Inherits/conforms to `FindingSource` Protocol + `LLMSource` marker
2. Augments the wrapped workflow's prompt with `STRUCTURED_EMIT_FOOTER`
3. Invokes the wrapped workflow (mocks-friendly — no `claude_agent_sdk` imports at module scope)
4. Parses findings via `parse_findings_json`
5. Adds itself to `default_sources()`

- [ ] **P2.1** `BugPredictSource` wrapping `BugPredictionWorkflow` in `src/attune/workflows/bug_predict.py`. Unit tests mock `BugPredictionWorkflow.execute()`. Integration test gated on `HAS_API_KEY`. Update CHANGELOG.
- [ ] **P2.2** `SecurityAuditSource` wrapping `SecurityAuditWorkflow` in `src/attune/workflows/security_audit.py`. Same pattern as P2.1.
- [ ] **P2.3** `DependencyCheckSource` wrapping `DependencyCheckWorkflow`. Same pattern.
- [ ] **P2.4** **Retirement evaluation (empirical, no code).** Run `attune workflow run discovery-sweep --path src/attune/security/` and `attune workflow run discovery-sweep --path src/attune/workflows/`. For each scope, also run candidate workflows that *might* be redundant (initial candidates: `test-audit`; later add others as P2.1–P2.3, P2.5 reveal subsumption). Cross-reference findings.
      - Output: `docs/specs/discovery-sweep/retirement-evaluation.md` with per-workflow RETIRE / KEEP / DEFER recommendation.
      - For RETIRE candidates, draft the deprecation path (lazy-import shim per the existing PEP 562 lesson, CHANGELOG entry, migration alias).
      - Do NOT delete anything in this task — recommendation only. Deletion is a separate PR.
- [ ] **P2.5** `PerfAuditSource` wrapping `PerformanceAuditWorkflow`. Same pattern as P2.1.
- [ ] **P2.6** `DocAuditSource` wrapping `DocAuditWorkflow`. Same pattern as P2.1.

> **DECIDE:** Order of P2.1–P2.6. The user's original prompts suggested P2.1=bug-predict first, then security-audit, then retirement eval (P2.4) — but the eval needs *some* LLM sources shipped to be meaningful, hence P2.4 placement here (after P2.1–P2.3 give us 3 LLM sources to evaluate). Revisit if dogfood shows the eval can run with fewer sources.

---

## Phase 3 — Output polish + JSON mode

Goal: turn the markdown rendering into something pleasant and machine-readable.

- [ ] **3.1** Implement `--json` flag in the CLI. Output matches the JSON schema in design.md § Data model.
- [ ] **3.2** Improve human markdown rendering: clickable `file:line` links (already standard in attune output), severity-colored badges (use existing rich console formatting from `cli_minimal.py`).
- [ ] **3.3** `--verbose` flag exposes rejected bucket with rule names.
- [ ] **3.4** `--no-llm` flag filters to pattern-only sources.
- [ ] **3.5** `--source <name>` flag (optional, defer if not needed).
- [ ] **3.6** Tests:
      - `test_cli_json_output` — JSON parses, top-level shape matches schema
      - `test_cli_verbose_shows_rejected` — `--verbose` includes rejected bucket
      - `test_cli_no_llm_filters_sources` — only `is_llm = False` sources run

---

## Phase 4 — Ops dashboard integration

Goal: surface sweep results in the ops dashboard from ops-runner-tier2.

- [ ] **4.1** Discovery-sweep row in `workflows.html` honors the scope picker (already supported via `PATH_ARG_REGISTRY` from P1.7).
- [ ] **4.2** Sweep results render as colored chips per bucket (queue/questions/rejected counts) in the row.
- [ ] **4.3** Clicking a chip opens a detail view that lists findings (re-uses the existing run-view page).
- [ ] **4.4** SSE event stream emits per-source progress (`source X started`, `source X finished with N findings`) so the dashboard shows a live progress bar.

> **DECIDE:** Phase 4 scope. Could be deferred to a follow-up spec (`discovery-sweep-ops-integration`) if ops-runner-tier2 isn't far enough along. Revisit when Phase 3 ships.

---

## Phase 5 — Retirement execution

Goal: act on the retirement recommendations from P2.4. Only opens if P2.4 returns any RETIRE recommendations.

- [ ] **5.1** For each RETIRE candidate, implement the deprecation shim (PEP 562 module-level `__getattr__` with `DeprecationWarning` per the existing CLAUDE.md lesson).
- [ ] **5.2** CHANGELOG `### Deprecated` entries.
- [ ] **5.3** Migration alias in routing if the workflow had a short CLI name (e.g. `test-audit` → `discovery-sweep`).
- [ ] **5.4** Update `.claude/plans/*` and `docs/specs/_sequencing.md` to reflect retirements.

---

## Definition of done

The spec is complete when:

- Phase 1 + 2A + at least 3 of P2.1–P2.6 + Phase 3 have shipped
- Phase 4 has either shipped OR been deferred to a named follow-up spec
- Phase 5 has either shipped OR P2.4 returned zero RETIRE recommendations
- `discovery-sweep` appears in the `docs/specs/_sequencing.md` "Done" section
- Phase 2 retirement evaluation is published

---

## Out of scope (post-spec follow-ups)

- MCP tool exposure (`mcp__attune-ai__discovery_sweep`)
- Caching by git SHA
- Auto-fix / agentic remediation
- Cross-repo sweep
- `.help/features.yaml`-driven source configuration
