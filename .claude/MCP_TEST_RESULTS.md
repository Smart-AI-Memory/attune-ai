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

## Remaining Manual Tests

The following require a **clean** Claude Code environment
(no pre-existing attune plugins) per `manual-test-plan.md`:

- Funnel 1: Fresh `attune-ai` install from marketplace
- Funnel 2: Fresh `attune-help` install (no API key)
- Funnel 3: Both `attune-help` + `attune-author` coexist

These test install paths and marketplace behavior, not
skill triggering (which is verified above).
