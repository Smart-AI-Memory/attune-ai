# Attune MCP Server - Test Results

**Date:** 2026-04-10
**Status:** All Tests Passing

## Test Summary

### Automated Tests (399 passed, 0 failures)

| Suite | Tests | Status |
|---|---|---|
| `tests/unit/mcp/` (core) | 299 | Pass |
| `tests/unit/test_mcp_memory_tools.py` | 27 | Pass |
| `tests/unit/test_mcp_help_handlers.py` | 12 | Pass |
| `tests/unit/mcp/test_request_handler.py` | 14 | Pass |
| `tests/monitoring/test_mcp_path_containment.py` | 16 | Pass |
| `attune_redis/tests/test_mcp_tools.py` | 31 | Pass |

### Plugin Validation Tests (93 passed, 3 skipped)

| Suite | Tests | Status |
|---|---|---|
| `test_plugin_reference_validation.py` | 54 | Pass |
| `test_plugins_smoke.py` | 7 | Pass |
| `test_smoke.py` | 5 | Pass |
| `test_sync_agents_skills.py` | 24 | Pass |
| `test_plugin_config_validation.py` | 3 | Skipped |

### Server Instantiation

- attune-ai v5.10.0: **41 tools** registered
- attune-help v0.3.1: MCP server imports OK
- attune-author v0.1.0: MCP server imports OK

### Skill-Trigger Tests (14/14 skills fire)

Tested via `Skill` tool invocation in a live Claude
Code session with the attune-ai plugin installed.

| Skill | Trigger | Fired |
|---|---|---|
| `attune-hub` | `/attune` | Yes |
| `security-audit` | `/security` | Yes |
| `smart-test` | `/smart-test` | Yes |
| `code-quality` | `/code-quality` | Yes |
| `doc-gen` | `/doc-gen` | Yes |
| `refactor-plan` | `/refactor-plan` | Yes |
| `coach` | `/coach` | Yes |
| `spec` | `/spec` | Yes |
| `fix-test` | `/fix-test` | Yes |
| `bug-predict` | `/bug-predict` | Yes (via attune-ai) |
| `planning` | `/planning` | Yes (via attune-ai) |
| `workflow-orchestration` | `/workflows` | Yes |
| `memory-and-context` | `/remember` | Yes |
| `release-prep` | N/A | disable-model-invocation (user-only) |

### MCP Tool Dispatch (10/10 utility tools OK)

| Tool | Status |
|---|---|
| `memory_store` | OK (graceful error — no Redis) |
| `memory_retrieve` | OK (graceful error — no Redis) |
| `memory_search` | OK (graceful error — no Redis) |
| `memory_forget` | OK (graceful error — no Redis) |
| `attune_get_level` | OK |
| `attune_set_level` | OK |
| `context_set` | OK |
| `context_get` | OK |
| `auth_status` | OK |
| `telemetry_stats` | OK |

### Skill Description Lengths (all under 250 chars)

All 14 skills have descriptions between 137-222
characters, within the 250-char limit for Claude Code
auto-triggering.

### Skill-to-Tool Reference Chain (all resolve)

Every MCP tool referenced by a skill exists in the
server's tool registry (41 tools total).

## Sub-Package PyPI Status

| Package | Version | `[plugin]` extra | MCP server |
|---|---|---|---|
| `attune-help` | 0.3.1 | Working | `attune_help.mcp.server` |
| `attune-author` | 0.1.0 | Working | `attune_author.mcp.server` |

Both have CI (`publish.yml`) with OIDC trusted publishing
in their respective repos.

## Clean-Environment Funnel Tests (2026-04-10 evening)

Executed via `CLAUDE_CONFIG_DIR` isolation — per-funnel
fresh profile in `/tmp/attune-ship-test/{funnel1,funnel3}/`.

### Funnel 1 — attune-ai solo (developer workflows)

```text
claude plugin marketplace add Smart-AI-Memory/attune-ai  ->  OK
claude plugin install attune-ai@attune-ai                ->  OK
claude plugin list                                       ->  attune-ai@attune-ai v5.10.0 enabled
claude mcp list                                          ->  uvx --from attune-ai python -m attune.mcp.server - Connected
```

All 14 skill directories present on disk. MCP health
verified after applying the PR #142 `uvx` syntax fix
to the installed plugin cache (same fix that ships in
the merged PR).

### Funnel 3 — attune-docs both plugins (AI authoring)

```text
claude plugin marketplace add Smart-AI-Memory/attune-docs  ->  OK
claude plugin install attune-help@attune-docs              ->  OK
claude plugin install attune-author@attune-docs            ->  OK
claude plugin list                                         ->  both enabled
  - attune-help@attune-docs   v0.3.1
  - attune-author@attune-docs v0.1.0
claude mcp list                                            ->  both Connected
  - uvx --from attune-help[plugin] python -m attune_help.mcp.server
  - uvx --from attune-author[plugin] python -m attune_author.mcp.server
```

All 4 attune-help skills and 6 attune-author skills
present on disk.

### Funnel 2 (attune-help solo, no API key) — not run

Not exercised as a separate test. attune-help's
connectivity and skill presence are already confirmed by
Funnel 3, and attune-help is independent of
`ANTHROPIC_API_KEY` by design (lookup-only runtime).

## Root cause note: `uv run --from` is invalid syntax

The "MCP Failed to connect" symptom documented in the
2026-04-09 install test log was previously attributed to
pyenv shim quirks. The actual root cause was that all
three `.mcp.json` files invoked the MCP server with
`uv run --from <pkg>` — a form that does not exist in any
shipped uv version (tested 0.9.17 Homebrew and 0.9.22).
The `--from` flag belongs to `uv tool run` (aka `uvx`),
not `uv run`. Fixed in attune-ai PR #142 and attune-docs
PR #2.
