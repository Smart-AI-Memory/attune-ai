# Tasks — Discovery Sweep
**Status:** complete (2026-05-13) — Phase 1, 2A, 2B, 3 shipped; Phase 4 closed empty per P2.7 surface evaluation.
| Phase | Status | Shipped via |
|---|---|---|
| Phase 1 — Engine + PatternScanSource | done | [#303](https://github.com/Smart-AI-Memory/attune-ai/pull/303), [#306](https://github.com/Smart-AI-Memory/attune-ai/pull/306) FP filter, [#309](https://github.com/Smart-AI-Memory/attune-ai/pull/309) AST filter |
| Phase 1.5 — Second-pass design landings | done | [#312](https://github.com/Smart-AI-Memory/attune-ai/pull/312) |
| Phase 2A — Shared LLM adapter base | done | [#313](https://github.com/Smart-AI-Memory/attune-ai/pull/313) |
| Phase 2B — Per-source adapters (×6) | done | [#314](https://github.com/Smart-AI-Memory/attune-ai/pull/314)–[#319](https://github.com/Smart-AI-Memory/attune-ai/pull/319) |
| Phase 2.7 — Surface evaluation | done | [#321](https://github.com/Smart-AI-Memory/attune-ai/pull/321) — KEEP all six standalones |
| Phase 3 — Output polish + JSON | done | [#320](https://github.com/Smart-AI-Memory/attune-ai/pull/320) (3.1/3.3/3.4/3.5), [#322](https://github.com/Smart-AI-Memory/attune-ai/pull/322) (3.2 ANSI badges) |
| Phase 4 — CLI deprecation | closed empty | P2.7 decision: zero deprecation candidates |

Ops-dashboard integration (originally bundled into Phase 4) carved out to follow-up spec [`discovery-sweep-ops-integration`](../discovery-sweep-ops-integration/) — **completed 2026-05-16**. Dashboard renders per-bucket chips on the workflows page, live source-by-source progress on the run_view page, and a scope-keyed drill-in detail page.

Phased plan. Each phase is independently shippable. See `decisions.md`, `requirements.md`, `design.md` for context.

> **DECIDE callouts** are spread across this file and the design docs. Resolve the relevant ones before starting each phase.

---

## Phase 1 — Engine + first non-LLM source

Goal: prove the engine + Protocol + verification rules + CLI integration end-to-end on the cheapest source (pattern scanning). Ships a usable `attune workflow run discovery-sweep --path X --no-llm` even before any LLM adapter exists.

- [x] **1.1** Create `src/attune/workflows/discovery_sweep/` package skeleton. Empty `__init__.py`, stub `workflow.py`, stub `cli_workflow.py`, `sources/` subpackage.
- [x] **1.2** Define `Finding`, `QuestionFinding`, `RejectedFinding`, `SweepResult`, `SweepMetadata` dataclasses in `workflow.py`. All frozen where appropriate.
- [x] **1.3** Define `FindingSource` Protocol in `workflow.py` (`@runtime_checkable`, async `discover(path, budget_usd) -> list[Finding]`).
- [x] **1.4** Implement `verification.py` — the five routing rules from `design.md` § Verification rules. Pure functions, no I/O, no LLM. Unit tests cover each rule + interactions.
- [x] **1.5** Implement `DiscoverySweepWorkflow.execute()` in `workflow.py`:
      - Accept `path`, `budget_usd` (default 10.00), `sources` (default `None` → use `default_sources()`), `no_llm` (default False).
      - Allocate budget across sources, `asyncio.gather` with `return_exceptions=True`.
      - Run verification, build `SweepResult`.
      - Return `WorkflowResult` whose `final_output` is the human-readable markdown rendering AND whose `metadata` carries the structured `SweepResult` for JSON output.
- [x] **1.6** Implement `PatternScanSource` in `sources/pattern_scan.py`. Wraps existing pattern scanning (find the existing scanner — likely in `src/attune/workflows/bug_predict_patterns.py` or `src/attune/security/` — and adapt). `name = "pattern-scan"`, `is_llm = False`. Returns `Finding` objects directly. Ignores `budget_usd`.
- [x] **1.7** Register `DiscoverySweepWorkflow` in `src/attune/workflows/__init__.py` (lazy import + `_DEFAULT_WORKFLOW_NAMES`). Add to `PATH_ARG_REGISTRY` in `src/attune/ops/data.py` (Category A: takes `path` kwarg).
- [x] **1.8** CLI smoke test: `attune workflow run discovery-sweep --path tests/fixtures/ --no-llm` returns a SweepResult with at least one finding from the pattern source.
- [x] **1.9** Tests:
      - `test_engine.py` — happy path with two fake sources, one returning findings, one raising
      - `test_verification.py` — each rule in isolation + the routing-order interaction
      - `test_pattern_scan_source.py` — runs against a fixture file with a known pattern hit
      - `test_discovery_sweep_registered.py` — drift guard: workflow appears in `list_workflows()` and `PATH_ARG_REGISTRY`
- [x] **1.10** Update CHANGELOG `[Unreleased]` § Added: discovery-sweep engine + PatternScanSource (no LLM).

---

## Phase 2 — LLM source adapters + retirement evaluation

Goal: wrap each audit-family workflow as a `FindingSource`. Each is an independent sub-PR.

### Phase 2A — Shared LLM adapter infrastructure

- [x] **2A.1** Implement `llm_source_base.py`:
      - `STRUCTURED_EMIT_FOOTER` constant (the prompt-augmentation string from design.md)
      - `parse_findings_json(text, source_name) -> list[Finding]` with text-only fallback
      - Optional `LLMSource` marker mixin (`is_llm = True`)
- [x] **2A.2** Tests for `parse_findings_json`: well-formed block, malformed JSON, missing block, multiple blocks (use last), block with extra prose. Each → expected Finding list.
- [x] **2A.3** CHANGELOG: shared LLM adapter base shipped (no user-visible behavior change).

### Phase 2B — Per-source adapters (one PR each)

Each sub-task ships an adapter that:

1. Conforms to `FindingSource` Protocol + sets `is_llm = True` and an appropriate `budget_multiplier` (see `decisions.md` § Cost discipline for defaults)
2. Augments the wrapped workflow's prompt with `STRUCTURED_EMIT_FOOTER` **at the workflow-instance level** — see `design.md` § "Prompt augmentation lives at the workflow-instance level"
3. Invokes the wrapped workflow (mocks-friendly — no `claude_agent_sdk` imports at module scope)
4. Parses findings via `parse_findings_json`
5. Adds itself to `default_sources()`

- [x] **P2.1** `BugPredictSource` wrapping `BugPredictionWorkflow` in `src/attune/workflows/bug_predict.py`. `budget_multiplier=1.5`. Unit tests mock `BugPredictionWorkflow.execute()`. Integration test uses `@pytest.mark.integration` (the project-standard gate) — **not** `HAS_API_KEY` skipif, which masked code regressions as Anthropic network flakes (see the `HAS_API_KEY`-gated lesson in CLAUDE.md). Update CHANGELOG.
- [x] **P2.2** `SecurityAuditSource` wrapping `SecurityAuditWorkflow` in `src/attune/workflows/security_audit.py`. `budget_multiplier=4.0` (multi-subagent fan-out). Same test pattern as P2.1.
- [x] **P2.3** `DependencyCheckSource` wrapping `DependencyCheckWorkflow`. `budget_multiplier=0.5` (mostly deterministic CVE feed). Same test pattern as P2.1.
- [x] **P2.4** `PerfAuditSource` wrapping `PerformanceAuditWorkflow`. `budget_multiplier=1.0` (default — shipped this rather than 1.5 per implementation review). Same test pattern as P2.1.
- [x] **P2.5** `DocAuditSource` wrapping `DocAuditWorkflow`. `budget_multiplier=1.0`. Same test pattern as P2.1.
- [x] **P2.6** `TestAuditSource` wrapping `TestAuditWorkflow`. `budget_multiplier=1.0`. Same test pattern as P2.1. (Distinct lens — see `decisions.md`: test-quality scoring is not subsumed by bug-predict or doc-audit.)
- [x] **P2.7** **Surface evaluation — complete (2026-05-13).** Published at `docs/specs/discovery-sweep/surface-evaluation.md`. **Decision: KEEP all six standalone audit workflows alongside discovery-sweep. Zero deprecation candidates.** Reasoning is analytical (the adapter wrappers don't change wrapped-workflow behavior, so functional equivalence is structural; the retirement question reduces to UX, and three distinct user journeys justify keeping the standalones). Empirical pass attempted (test-audit standalone vs sweep-wrapped on `src/attune/security/` at `--depth quick`) but blocked by an SDK nested-CLI-execution issue — see the doc's "SDK infrastructure block" section. The empirical pass DID validate the engine's defense-in-depth around adapter failures (spec NFR-1). **Phase 4 (CLI deprecation) closes empty.**

---

## Phase 3 — Output polish + JSON mode

Goal: turn the markdown rendering into something pleasant and machine-readable.

- [x] **3.1** Implement `--json` flag in the CLI. Output matches the JSON schema in design.md § Data model.
- [x] **3.2** Improve human markdown rendering: clickable `file:line` links (already standard in attune output), severity-colored badges (use existing rich console formatting from `cli_minimal.py`).
- [x] **3.3** `--verbose` flag exposes rejected bucket with rule names.
- [x] **3.4** `--no-llm` flag filters to pattern-only sources.
- [x] **3.5** `--source <name>` flag (optional, defer if not needed).
- [x] **3.6** Tests:
      - `test_cli_json_output` — JSON parses, top-level shape matches schema
      - `test_cli_verbose_shows_rejected` — `--verbose` includes rejected bucket
      - `test_cli_no_llm_filters_sources` — only `is_llm = False` sources run

---

## Phase 4 — CLI surface deprecation

Goal: act on the surface-evaluation recommendations from P2.7. Only opens if P2.7 returns any DEPRECATE recommendations.

**Resolved (2026-05-13, Phase 1.5):** Old Phase 4 (ops-dashboard integration) is **deferred to a follow-up spec** — `discovery-sweep-ops-integration` — to be opened once `ops-runner-tier2` Phase 2 lands. The CLI deprecation work (previously Phase 5) is promoted to Phase 4 because it follows directly from P2.7 and ships under this spec.

**Closed empty (2026-05-13):** P2.7 surface evaluation returned zero DEPRECATE recommendations — see `surface-evaluation.md`. All six standalone audit workflows KEEP. Phase 4 has nothing to delete; the "Phase 4 has either shipped OR P2.7 returned zero DEPRECATE recommendations" definition-of-done clause fires. The 4.1–4.4 subtasks below are preserved as a record of what *would* have shipped had retirement been recommended; they are not actionable.

- [ ] ~~**4.1** For each DEPRECATE candidate (a standalone CLI entry, e.g. `attune workflow run bug-predict`), implement the deprecation shim (PEP 562 module-level `__getattr__` with `DeprecationWarning` per the existing CLAUDE.md lesson). The underlying workflow class stays.~~ (No candidates.)
- [ ] ~~**4.2** CHANGELOG `### Deprecated` entries for each affected CLI entry.~~ (No deprecations.)
- [ ] ~~**4.3** Migration alias in routing — e.g. `attune workflow run bug-predict --path X` continues to work for one release with a deprecation warning, recommending `attune workflow run discovery-sweep --path X --source bug-predict`.~~ (No migrations.)
- [ ] ~~**4.4** Update `.claude/plans/*` and `docs/specs/_sequencing.md` to reflect the deprecations.~~ (Sequencing already reflects the spec as complete.)

---

## Out-of-scope (follow-up spec) — Ops dashboard integration

Deferred from this spec on 2026-05-13. To land in a separate `discovery-sweep-ops-integration` spec once `ops-runner-tier2` Phase 2 ships. Originally:

- Discovery-sweep row in `workflows.html` honors the scope picker (already supported via `PATH_ARG_REGISTRY` from P1.7).
- Sweep results render as colored chips per bucket (queue/questions/rejected counts) in the row.
- Clicking a chip opens a detail view that lists findings (re-uses the existing run-view page).
- SSE event stream emits per-source progress so the dashboard shows a live progress bar.

---

## Definition of done

The spec is complete when:

- Phase 1 + 1.5 + 2A + all six of P2.1–P2.6 + P2.7 + Phase 3 have shipped
- Phase 4 (CLI deprecation) has either shipped OR P2.7 returned zero DEPRECATE recommendations
- The ops-dashboard follow-up spec (`discovery-sweep-ops-integration`) is open or shipped
- `discovery-sweep` appears in the `docs/specs/_sequencing.md` "Done" section
- P2.7 surface evaluation is published at `docs/specs/discovery-sweep/surface-evaluation.md`

---

## Out of scope (post-spec follow-ups)

- MCP tool exposure (`mcp__attune-ai__discovery_sweep`)
- Caching by git SHA
- Auto-fix / agentic remediation
- Cross-repo sweep
- `.help/features.yaml`-driven source configuration
