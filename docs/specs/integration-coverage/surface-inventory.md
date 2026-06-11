# Surface inventory — non-mocked exercise per production surface

**Date:** 2026-06-11 (task 7)
**Method:** grep + reading across `tests/`, `attune_redis/tests/`,
`scripts/`, and `.github/workflows/`; registry counts verified
against source (not agent-reported).

## Mode definitions

- **LIVE** — real external dependency exercised (real
  `ANTHROPIC_API_KEY`, real `claude` CLI subprocess, real AMS/Redis
  server, real network).
- **REAL-INTERNAL** — the surface's own production code path runs
  for real; only the outermost boundary is faked
  (`claude_agent_sdk.query`, LLM client, `uvicorn.run`, network) or
  state lives in `tmp_path` file backends.
- **MOCK-ONLY** — the surface's own collaborators are mocked; the
  test proves wiring of mocks, not the surface.
- **none** — no automated exercise found.

A surface's verdict is its **best** mode found anywhere
(unit, integration, nightly, or a recorded dogfood receipt).

## Inventory

| Surface | Size | Best non-mocked exercise | Verdict |
|---|---|---|---|
| LLM providers (AnthropicProvider, EmpathyLLM) | 1 provider family | `tests/integration/test_llm_integration.py` — real API, nightly auth job | **LIVE** (nightly) |
| SDK workflows — discovery-sweep sources | 6 of 20 workflows | `tests/integration/test_discovery_sweep_*_integration.py` (6 files) — real key, real SDK subprocess, nightly auth job | **LIVE** (nightly) |
| SDK workflows — shell/adapter (all 20) | 20 in `_DEFAULT_WORKFLOW_NAMES` | per-workflow `execute()` tests with only `claude_agent_sdk.query` mocked (e.g. `tests/unit/workflows/test_test_audit_execute.py`); plus recorded keyless bug-predict dogfood receipt (sdk-subprocess-isolation decisions.md) | REAL-INTERNAL (LIVE receipt for bug-predict) |
| attune_redis AMS backend | `AMSMemoryBackend` + int8 proxy | `attune_redis/tests/test_integration.py` — real AMS server round-trips (16 tests), `@pytest.mark.integration` + `_ams_available()` gate | **LIVE** (local-only — never runs in CI; CI lacks an AMS service) |
| MCP tool handlers — memory/help/session (20 tools) | 20 of 41 | `tests/unit/test_mcp_memory_tools.py`, `test_mcp_help_handlers.py`, `tests/integration/test_mcp_dispatch.py` — real `call_tool → _dispatch_tool → handler` chain, real file backends in `tmp_path` | REAL-INTERNAL |
| MCP tool handlers — workflow tools (21 tools) | 21 of 41 | validation-layer tests only; the workflow is mocked at its source module (required since #728 — real SDK spawn crashes xdist workers) | **MOCK-ONLY past validation** |
| MCP stdio transport (handshake) | 1 | none automated — manual Claude Code sessions only | **none** |
| Ops dashboard routes | 14 modules, ~50 endpoints | `tests/unit/ops/` TestClient suites — real route handlers + real `tmp_path` backends (patterns lifecycle round-trip, runner persistence, home KPIs); LLM boundary faked | REAL-INTERNAL |
| CLI (`attune` …) | 12 simple + 8 grouped subcommands | `tests/unit/ops/test_cli.py` real `main()`/argparse dispatch (uvicorn mocked); `tests/integration/test_commands_integration.py` | REAL-INTERNAL (no test runs the installed console script as a subprocess) |
| Plugin hooks | 10 scripts / 6 events | `tests/unit/plugins/test_sdk_subprocess_gate.py` — `subprocess.run` of the real hook scripts with real stdin/env | REAL-INTERNAL |
| Memory tool bridge | `memory_tool.py` | `tests/unit/memory/test_memory_tool.py` — real commands against real `FileStashBackend` | REAL-INTERNAL |
| Memory backends — file | `FileStashBackend` | real round-trips throughout (`test_pattern_review.py`, gates, ops) | REAL-INTERNAL |
| Gates (envelope / spend / meter) | 4 modules | `tests/unit/gates/test_spend_gate.py` — real envelope file round-trips | REAL-INTERNAL |
| Wizards | 5 registered | `test_get_or_create_workflow_constructs_real_workflow` (real construction, no mocks); wizard *run* paths are mock-only | REAL-INTERNAL (construction only) |
| Release agent team | 5 subagents | via release-prep workflow `execute()` tests (query mocked) | REAL-INTERNAL |
| Routing / meta-workflows | cli_router, smart_router, chain executor | `tests/integration/test_intelligence_integration.py`, `test_natural_language_routing_v5_1.py` — in-memory, real code | REAL-INTERNAL |
| RAG workflow path | rag-code-gen | `tests/integration/rag/test_rag_workflow.py` — fake corpus + patched `query` | REAL-INTERNAL at best (importorskip-gated) |

Registry counts verified 2026-06-11: 20 workflow names in
`_DEFAULT_WORKFLOW_NAMES`; 41 tools in `_build_dispatch_table()`;
nightly auth selector is
`tests/integration -k "discovery_sweep or llm_integration"`.

## Gap ranking (worst first)

1. **MCP workflow tools (21 of 41) — no exercise past the
   validation layer, and NO MCP tool has LIVE exercise anywhere.**
   The handoff's "known-worst" call is confirmed with one nuance:
   the 20 memory/help/session tools DO get real dispatch-chain
   exercise (REAL-INTERNAL); the gap is the 21 workflow tools,
   whose handlers mock the workflow at source by necessity
   (#728 xdist crash). A live MCP exercise would have caught the
   `doc_orchestrator` no-op stub (CLAUDE.md lesson) and the
   `BugPredictWorkflow` ImportError class. Cheapest closure:
   one nightly-auth test that drives ONE workflow MCP tool
   end-to-end (real handler → real workflow → real key), reusing
   the existing `integration-auth.yml` budget cap.
2. **MCP stdio transport — zero automated exercise.** The
   handshake is exactly where the hand-rolled-loop failure
   (CLAUDE.md lesson) lived. A smoke test spawning
   `python -m attune.mcp.server` and completing `initialize`
   would be cheap and keyless.
3. **attune_redis LIVE suite never runs in CI.** 16 good live
   tests exist but gate themselves off everywhere except a dev
   machine with AMS running. Known mock-masking history (4 AMS
   behaviors invisible to 100+ green mocked tests). Closure
   options: a scheduled job with `redis:8` + AMS service
   containers, or accept local-only and record cadence.
4. **CLI console script as subprocess** — `main()` is exercised
   in-process, but no test runs the installed `attune` entry
   point; the editable-install console-script staleness class
   (CLAUDE.md lesson) is invisible to current tests.
5. **Wizard run paths** — construction is covered (the #727
   regression test); the interactive run loop is mock-only.

## Disposition

This table is the task-7 deliverable (inventory only). Gap
closures above are candidates for follow-up tasks; #1 and #2 are
small enough to be single-PR tasks against the existing nightly
job. No closure work is committed by this document.
