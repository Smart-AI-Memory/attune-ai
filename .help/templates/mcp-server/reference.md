---
type: reference
feature: mcp-server
depth: reference
generated_at: 2026-04-19T18:48:03.281113+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# MCP Server reference

Run Attune AI tools through the Model Context Protocol. The MCP server exposes workflows, help system, memory storage, and utility functions as tools that Claude and other MCP clients can call.

## Classes

| Class | Parameters | Description |
|-------|------------|-------------|
| `MemoryHandlersMixin` | | Mixin providing memory tool handlers for EmpathyMCPServer |
| `RateLimiter` | `max_calls: int = 60, window_seconds: float = 60.0` | Simple sliding-window rate limiter |
| `EmpathyMCPServer` | `workspace_root: str \| None = None, user_id: str \| None = None` | MCP server for Attune AI workflows |
| `WorkflowHandlersMixin` | | Mixin providing workflow tool handlers for EmpathyMCPServer |

### RateLimiter methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `check` | `key: str` | `bool` | Check if a key is within rate limits |

### EmpathyMCPServer methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_prompt_list` | | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `call_tool` | `tool_name: str, arguments: dict[str, Any]` | `dict[str, Any]` | Execute a tool by name |
| `get_tool_list` | | `list[dict[str, Any]]` | Get list of available tools |
| `get_resource_list` | | `list[dict[str, Any]]` | Get list of available resources |

## Functions

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|--------|-------------|
| `get_prompt_list` | `prompts: dict[str, dict[str, Any]]` | `list[dict[str, Any]]` | | Get list of available prompts |
| `get_prompt_messages` | `prompts: dict[str, dict[str, Any]], prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | ValueError | Get messages for a specific prompt |
| `create_server` | | `EmpathyMCPServer` | | Create and return an Empathy MCP server instance |
| `main` | | `None` | | Entry point for MCP server |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `get_prompt_messages` | ValueError | 'Unknown prompt: {...}' |

## Tool schemas

### Utility tools

| Tool | Description | Required Parameters | Optional Parameters |
|------|-------------|-------------------|-------------------|
| `auth_status` | Get authentication strategy status. Shows current configuration, subscription tier, and default mode | | |
| `auth_recommend` | Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode | `file_path` (string) | |
| `telemetry_stats` | Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance | | `days` (integer, default: 30) |
| `attune_get_level` | Get current interaction level (1-5). Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems | | |
| `attune_set_level` | Set interaction level (1-5) for this session | `level` (integer, 1-5) | |
| `context_get` | Get session context value | `key` (string) | |
| `context_set` | Set session context value | `key` (string), `value` (string) | |

### Help tools

| Tool | Description | Required Parameters | Optional Parameters |
|------|-------------|-------------------|-------------------|
| `help_lookup` | Look up contextual help for a topic, workflow, or error. Progressive mode escalates across template types | `topic` (string) | `mode` (enum: progressive, preamble, related, workflow_help, precursor, search_tag, default: progressive), `file_path` (string), `last_workflow` (string), `reset` (boolean, default: false) |
| `help_maintain` | Check for stale help templates and regenerate them | | `dry_run` (boolean, default: false), `batch` (boolean, default: false) |
| `help_init` | Bootstrap a project-local help system | `action` (enum: scan, accept) | `accepted` (array of feature objects) |
| `help_status` | Show staleness report for the project-local help system | | `features` (array of strings) |
| `help_update` | Regenerate help templates for specific features | | `features` (array of strings), `dry_run` (boolean, default: false) |

### Memory tools

| Tool | Description | Required Parameters | Optional Parameters |
|------|-------------|-------------------|-------------------|
| `memory_store` | Store data in attune-ai memory | `key` (string), `value` (string) | `classification` (enum: PUBLIC, INTERNAL, SENSITIVE, default: PUBLIC), `pattern_type` (string) |
| `memory_retrieve` | Retrieve data from attune-ai memory by key or pattern ID | `key` (string) | |
| `memory_search` | Search attune-ai memory for patterns matching a query | `query` (string) | `pattern_type` (string) |
| `memory_forget` | Remove data from attune-ai memory | `key` (string) | `scope` (enum: session, persistent, all, default: all) |

### Tool schema functions

| Function | Returns | Description |
|----------|---------|-------------|
| `get_workflow_tools` | `dict[str, dict[str, Any]]` | Tool definitions for workflow execution tools |
| `get_utility_tools` | `dict[str, dict[str, Any]]` | Tool definitions for auth, telemetry, and session management |
| `get_help_tools` | `dict[str, dict[str, Any]]` | Tool definitions for contextual help and progressive documentation |
| `get_memory_tools` | `dict[str, dict[str, Any]]` | Tool definitions for memory store/retrieve/search/forget |

## Resources

| Resource | URI | Description | MIME Type |
|----------|-----|-------------|-----------|
| `workflows` | `attune://workflows` | List of all available Attune workflows | `application/json` |
| `auth_config` | `attune://auth/config` | Current authentication strategy configuration | `application/json` |
| `telemetry` | `attune://telemetry` | Cost tracking and performance metrics | `application/json` |

### Resource functions

| Function | Returns | Description |
|----------|---------|-------------|
| `get_resources` | `dict[str, dict[str, Any]]` | MCP resource definitions |

## Prompts

| Prompt | Description | Required Arguments | Optional Arguments |
|--------|-------------|-------------------|-------------------|
| `security-scan` | Run a comprehensive security scan on a directory | `path` | |
| `test-gen` | Generate behavioral tests for a Python module | `module` | `batch` |
| `cost-report` | Generate a cost optimization report | | `days` |

### Prompt functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_prompts` | | `dict[str, dict[str, Any]]` | MCP prompt definitions |

## Constants

| Constant | Values |
|----------|---------|
| `__all__` | `['EmpathyMCPServer', 'create_server']` |
| `_VOICE_SKIP_TOOLS` | `['memory_store', 'memory_retrieve', 'memory_search', 'memory_forget', 'attune_get_level', 'attune_set_level', 'context_get', 'context_set', 'auth_status', 'auth_recommend', 'telemetry_stats']` |

## Source files

- `src/attune/mcp/**`

## Tags

`mcp`, `tools`, `server`
