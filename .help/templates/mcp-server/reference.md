---
type: reference
feature: mcp-server
depth: reference
generated_at: 2026-04-14T14:59:18.690518+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# MCP Server API Reference

## Classes

| Class | Description |
|-------|-------------|
| `MemoryHandlersMixin` | Mixin providing memory tool handlers for EmpathyMCPServer |
| `RateLimiter` | Simple sliding-window rate limiter |
| `EmpathyMCPServer` | MCP server for Attune AI workflows |
| `WorkflowHandlersMixin` | Mixin providing workflow tool handlers for EmpathyMCPServer |

### RateLimiter

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `max_calls: int = 60, window_seconds: float = 60.0` | `None` | Initialize rate limiter |
| `check` | `key: str` | `bool` | Check if request is within rate limit |

### EmpathyMCPServer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `workspace_root: str \| None = None, user_id: str \| None = None` | `None` | Initialize MCP server |
| `get_prompt_list` | | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `call_tool` | `tool_name: str, arguments: dict[str, Any]` | `dict[str, Any]` | Execute a tool |
| `get_tool_list` | | `list[dict[str, Any]]` | Get list of available tools |
| `get_resource_list` | | `list[dict[str, Any]]` | Get list of available resources |

## Functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|--------|-------------|
| `get_prompt_list` | `prompts: dict[str, dict[str, Any]]` | `list[dict[str, Any]]` | | Get list of available prompts |
| `get_prompt_messages` | `prompts: dict[str, dict[str, Any]], prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | `ValueError` | Get messages for a specific prompt |
| `create_server` | | `EmpathyMCPServer` | | Create and return an Empathy MCP server instance |
| `main` | | `None` | | Entry point for MCP server |
| `get_workflow_tools` | | `dict[str, dict[str, Any]]` | | Tool definitions for workflow execution tools |
| `get_utility_tools` | | `dict[str, dict[str, Any]]` | | Tool definitions for auth, telemetry, and session management |
| `get_help_tools` | | `dict[str, dict[str, Any]]` | | Tool definitions for contextual help and progressive documentation |
| `get_memory_tools` | | `dict[str, dict[str, Any]]` | | Tool definitions for memory store/retrieve/search/forget |
| `get_resources` | | `dict[str, dict[str, Any]]` | | MCP resource definitions |
| `get_prompts` | | `dict[str, dict[str, Any]]` | | MCP prompt definitions |

### Error Messages

| Exception | Message |
|-----------|---------|
| `ValueError` | `'Unknown prompt: {...}'` |

## Tool Definitions

### Utility Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `auth_status` | Get authentication strategy status. Shows current configuration, subscription tier, and default mode | None |
| `auth_recommend` | Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode | `file_path: string` (required) |
| `telemetry_stats` | Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance | `days: integer = 30` |
| `attune_get_level` | Get current interaction level (1-5). Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems | None |
| `attune_set_level` | Set interaction level (1-5) for this session | `level: integer` (required, 1-5) |
| `context_get` | Get session context value | `key: string` (required) |
| `context_set` | Set session context value | `key: string` (required), `value: string` (required) |

### Help Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `help_lookup` | Look up contextual help for a topic, workflow, or error. Progressive mode escalates across template types: concept → procedural → reference | `topic: string` (required), `mode: enum = 'progressive'`, `file_path: string`, `last_workflow: string`, `reset: boolean = false` |
| `help_maintain` | Check for stale help templates and regenerate them. Detects when source files have changed since last generation | `dry_run: boolean = false`, `batch: boolean = false` |
| `help_init` | Bootstrap a project-local help system. Scans the project to discover features, returns proposals for review | `action: enum` (required), `accepted: array` |
| `help_status` | Show staleness report for the project-local help system (.help/features.yaml) | `features: array` |
| `help_update` | Regenerate help templates for specific features or all stale features in the project-local help system | `features: array`, `dry_run: boolean = false` |

#### Help Tool Enums

| Parameter | Allowed Values |
|-----------|----------------|
| `mode` | `progressive`, `preamble`, `related`, `workflow_help`, `precursor`, `search_tag` |
| `action` | `scan`, `accept` |

### Memory Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `memory_store` | Store data in attune-ai memory. Use for structured knowledge, patterns, and cross-agent coordination | `key: string` (required), `value: string` (required), `classification: enum = 'PUBLIC'`, `pattern_type: string` |
| `memory_retrieve` | Retrieve data from attune-ai memory by key or pattern ID | `key: string` (required) |
| `memory_search` | Search attune-ai memory for patterns matching a query | `query: string` (required), `pattern_type: string` |
| `memory_forget` | Remove data from attune-ai memory | `key: string` (required), `scope: enum = 'all'` |

#### Memory Tool Enums

| Parameter | Allowed Values |
|-----------|----------------|
| `classification` | `PUBLIC`, `INTERNAL`, `SENSITIVE` |
| `scope` | `session`, `persistent`, `all` |

## Resources

| Resource | URI | Description | MIME Type |
|----------|-----|-------------|-----------|
| `workflows` | `attune://workflows` | List of all available Attune workflows | `application/json` |
| `auth_config` | `attune://auth/config` | Current authentication strategy configuration | `application/json` |
| `telemetry` | `attune://telemetry` | Cost tracking and performance metrics | `application/json` |

## Prompts

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `security-scan` | Run a comprehensive security scan on a directory. Checks for eval/exec usage, path traversal, hardcoded secrets, and broad exception handling | `path: string` (required) |
| `test-gen` | Generate behavioral tests for a Python module. Creates pytest test files with Given/When/Then structure | `module: string` (required), `batch: string` |
| `cost-report` | Generate a cost optimization report. Shows LLM spend by workflow, cache hit rates, and savings from tier routing | `days: string` |

## Constants

| Constant | Value |
|----------|-------|
| `_MEMORY_NOT_INSTALLED` | `'attune-ai memory module not installed. Run: pip install attune-ai'` |

### Voice-Skipped Tools

Tools excluded from voice interfaces:

| Tool Set |
|----------|
| `memory_store`, `memory_retrieve`, `memory_search`, `memory_forget` |
| `attune_get_level`, `attune_set_level`, `context_get`, `context_set` |
| `auth_status`, `auth_recommend`, `telemetry_stats` |
