# Tasks — Discovery Sweep

**Status:** approved — nothing shipped

Phased plan. Each phase is independently shippable. See `decisions.md`, `requirements.md`, `design.md` for context.

> **DECIDE callouts** are spread across this file and the design docs. Resolve the relevant ones before starting each phase.

---

## Phase 1 — Engine + first non-LLM source

Goal: prove the engine + Protocol + verification rules + CLI integration end-to-end on the cheapest source (pattern scanning). Ships a usable `attune workflow run discovery-sweep --path X --no-llm` even before any LLM adapter exists.

- [ ] **1.1** Create `src/attune/workflows/discovery_sweep/` package skeleton. Empty `__init__.py`, stub `workflow.py`, stub `cli_workflow.py`, `sources/` subpackage.
- [ ] **1.2** Define `Finding`, `QuestionFinding`, `RejectedFinding`, `SweepResult`, `SweepMetadata` dataclasses in `workflow.py`. All frozen where appropriate.
- [ ] **1.3** Define `FindingSource` Protocol in `workflow.py` per design.md § FindingSource Protocol. `@runtime_checkable`, with attributes `name: str`, `budget_multiplier: float`, `is_llm: bool`, and async method `discover(paths: list[str], budget_usd: float) -> list[Finding]`. **Important:** `discover` takes `paths: list[str]` (engine has already glob-expanded), NOT `path: str`.
- [ ] **1.4** Implement `verification.py` — the five routing rules from `design.md` § Verification rules. Pure functions, no I/O, no LLM. Unit tests cover each rule + interactions.
- [ ] **1.5** Implement `DiscoverySweepWorkflow.execute()` in `workflow.py`:
      - Accept `path: str` (the user's raw input — may be a glob, directory, or file), `budget_usd` (default 10.00), `sources` (default `None` → use `default_sources()`), `no_llm` (default False).
      - **Glob-expand `path`** into a concrete `list[str]` of files BEFORE fan-out. Sources receive the expanded list, never the raw input. Use `pathlib.Path.glob` or equivalent; handle directory→recursive-file-list and single-file→one-element-list as natural cases.
      - **Allocate budget proportionally** by source `budget_multiplier`: each LLM source gets `budget_usd × (source.budget_multiplier / sum_of_llm_multipliers)`. Non-LLM sources get `budget_usd=0.0` (they ignore it anyway). See decisions.md cost-discipline table for the multiplier values.
      - Fan out with `asyncio.gather`, `return_exceptions=True` — a crashed source becomes one questions entry, not a failed sweep.
      - Run verification, build `SweepResult`.
      - Return `WorkflowResult` whose `final_output` is the human-readable markdown rendering AND whose `metadata` carries the structured `SweepResult` for JSON output.
- [ ] **1.6** Implement `PatternScanSource` in `sources/pattern_scan.py`. Wraps existing pattern scanning (find the existing scanner — likely in `src/attune/workflows/bug_predict_patterns.py` or `src/attune/security/` — and adapt). `name = "pattern-scan"`, `is_llm = False`, `budget_multiplier = 0.0` (non-LLM, doesn't consume budget). Iterates the `paths` list directly, returns `Finding` objects.
- [ ] **1.7** Register `DiscoverySweepWorkflow` in `src/attune/workflows/__init__.py` (lazy import + `_DEFAULT_WORKFLOW_NAMES`). Add to `PATH_ARG_REGISTRY` in `src/attune/ops/data.py` (Category A: takes `path` kwarg).
- [ ] **1.8** CLI smoke test: `attune workflow run discovery-sweep --path tests/fixtures/ --no-llm` returns a SweepResult with at least one finding from the pattern source. Verify glob expansion works: `--path "tests/fixtures/**/*.py"` produces the same or larger finding set as `--path tests/fixtures/`.
- [ ] **1.9** Tests:
      - `test_engine.py` — happy path with two fake sources, one returning findings, one raising; budget allocation by multiplier (mock two LLM sources with multipliers 1.0 and 3.0, assert each receives `budget × ratio`); glob expansion (pass `"tests/fixtures/**/*.py"`, assert sources receive an expanded `list[str]`)
      - `test_verification.py` — each rule in isolation + the routing-order interaction
      - `test_pattern_scan_source.py` — runs against a fixture file with a known pattern hit; verify it iterates `paths: list[str]` correctly
      - `test_discovery_sweep_registered.py` — drift guard: workflow appears in `list_workflows()` and `PATH_ARG_REGISTRY`
- [ ] **1.10** Update CHANGELOG `[Unreleased]` § Added: discovery-sweep engine + PatternScanSource (no LLM).

---

## Phase 2 — LLM source adapters + surface evaluation

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

- [ ] **P2.1** `BugPredictSource` wrapping `BugPredictionWorkflow` in `src/attune/workflows/bug_predict.py`. Unit tests mock `BugPredictionWorkflow.execute()`. **Integration test uses `@pytest.mark.integration` marker (default-excluded), NOT `pytest.mark.skipif(not HAS_API_KEY)` — see CLAUDE.md lesson on poisoning the matrix when Anthropic flakes.** Establishes the pattern P2.2–P2.6 inherit. `budget_multiplier = 1.0`. Update CHANGELOG.
- [ ] **P2.2** `SecurityAuditSource` wrapping `SecurityAuditWorkflow` in `src/attune/workflows/security_audit.py`. Same pattern as P2.1. `budget_multiplier = 4.0` (multi-subagent fan-out — see decisions.md cost discipline).
- [ ] **P2.3** `DependencyCheckSource` wrapping `DependencyCheckWorkflow`. Same pattern. `budget_multiplier = 0.5`. **Note: hybrid source.** `DependencyCheckWorkflow` runs `pip-audit` (deterministic CVE feed) alongside LLM analysis. The adapter should pass through whatever the workflow emits, but if dogfood reveals the CVE half could short-circuit the LLM half entirely, that's a v1.1 optimization.
- [ ] **P2.4** `PerfAuditSource` wrapping `PerformanceAuditWorkflow`. Same pattern as P2.1. `budget_multiplier = 1.5`.
- [ ] **P2.5** `DocAuditSource` wrapping `DocAuditWorkflow`. Same pattern as P2.1. `budget_multiplier = 1.0`.
- [ ] **P2.6** `TestAuditSource` wrapping `TestAuditWorkflow`. Same pattern as P2.1. `budget_multiplier = 1.5`. Test-quality scoring is a distinct lens not covered by the other five — see decisions.md.
- [ ] **P2.7** **Surface evaluation (empirical, no code).** Runs AFTER all six LLM adapters ship so the eval has full-coverage signal. Run `attune workflow run discovery-sweep --path src/attune/security/` and `attune workflow run discovery-sweep --path src/attune/workflows/`. For each scope, also run each underlying workflow standalone (`attune workflow run bug-predict --path X`, etc.). Cross-reference findings.
      - Output: `docs/specs/discovery-sweep/surface-evaluation.md` with per-workflow recommendation:
        - **DEPRECATE CLI** — standalone CLI invocation is redundant; keep the workflow class (the sweep uses it as an adapter), deprecate the CLI entry
        - **KEEP CLI** — workflow has a use case the sweep doesn't serve (depth tuning, single-source debug, MCP-only consumers)
        - **DEFER** — not enough data; re-evaluate after more dogfood
      - For DEPRECATE candidates, draft the deprecation path (CHANGELOG entry, migration message in routing, timeline for actual removal).
      - Do NOT deprecate or delete anything in this task — recommendation only. Execution lives in Phase 4.

**Order resolved 2026-05-13:** P2.1 → P2.2 → P2.3 → P2.4 → P2.5 → P2.6 → P2.7. Surface eval (P2.7) runs LAST so it has full-coverage signal; Phase 4 then acts on it in a single pass. P2.1 is the prototype that establishes the structured-emit pattern for P2.2–P2.6 to follow.

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

## Phase 4 — CLI surface deprecation

Goal: act on the surface-evaluation recommendations from P2.7. Only opens if P2.7 returns any DEPRECATE CLI recommendations.

- [ ] **4.1** For each DEPRECATE CLI candidate, mark the standalone CLI invocation deprecated. The workflow class stays (the sweep still uses it as an adapter); only the user-facing `attune workflow run <name>` entry shows a deprecation warning pointing at `discovery-sweep`.
- [ ] **4.2** CHANGELOG `### Deprecated` entries.
- [ ] **4.3** Migration message in `cli_minimal.py` workflow routing — when the user types a deprecated workflow name, print a note + run anyway (don't break).
- [ ] **4.4** Update `.claude/plans/*` and `docs/specs/_sequencing.md` to reflect the deprecations.

---

## Definition of done

The spec is complete when:

- Phase 1 + 2A + all six of P2.1–P2.6 + P2.7 surface eval + Phase 3 have shipped
- Phase 4 has either shipped OR P2.7 returned zero DEPRECATE CLI recommendations
- `discovery-sweep` appears in the `docs/specs/_sequencing.md` "Done" section
- P2.7 surface evaluation document is published

---

## Out of scope (post-spec follow-ups)

- **Ops dashboard integration** — deferred to a follow-up spec `discovery-sweep-ops-integration`, triggered when `ops-runner-tier2` Phase 2 (scope picker) ships. Includes: row in `workflows.html`, colored chips per bucket, SSE per-source progress events, detail view re-using the run-view page.
- MCP tool exposure (`mcp__attune-ai__discovery_sweep`)
- Caching by git SHA
- Auto-fix / agentic remediation
- Cross-repo sweep
- `.help/features.yaml`-driven source configuration
