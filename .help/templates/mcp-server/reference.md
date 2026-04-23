---
type: reference
name: mcp-server
tags: [mcp, tools, server]
source: src/attune/mcp/**
---

# MCP server reference

Configure Claude to use Attune AI's Model Context Protocol server for workflow automation, contextual help, and memory management.

## Classes

| Class | Description |
|-------|-------------|
| `MemoryHandlersMixin` | Mixin providing memory tool handlers for EmpathyMCPServer |
| `RateLimiter` | Simple sliding-window rate limiter |
| `EmpathyMCPServer` | MCP server for Attune AI workflows |
| `WorkflowHandlersMixin` | Mixin providing workflow tool handlers for EmpathyMCPServer |

### RateLimiter methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `max_calls: int = 60, window_seconds: float = 60.0` | `None` | Create rate limiter with sliding window |
| `check` | `key: str` | `bool` | Check if key can make another call within rate limits |

### EmpathyMCPServer methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `workspace_root: str \| None = None, user_id: str \| None = None` | | Initialize MCP server for Attune AI workflows |
| `get_prompt_list` | | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `call_tool` | `tool_name: str, arguments: dict[str, Any]` | `dict[str, Any]` | Execute an MCP tool with given arguments |
| `get_tool_list` | | `list[dict[str, Any]]` | Get list of available tools |
| `get_resource_list` | | `list[dict[str, Any]]` | Get list of available resources |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_prompt_list` | `prompts: dict[str, dict[str, Any]]` | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompts: dict[str, dict[str, Any]], prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `create_server` | | `EmpathyMCPServer` | Create and return an Empathy MCP server instance |
| `main` | | `None` | Entry point for MCP server |
| `get_workflow_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for workflow execution tools |
| `get_utility_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for auth, telemetry, and session management |
| `get_help_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for contextual help and progressive documentation |
| `get_personal_memory_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for personal cross-session memory |
| `get_memory_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for memory store/retrieve/search/forget |
| `get_resources` | | `dict[str, dict[str, Any]]` | MCP resource definitions |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `get_prompt_messages` | `ValueError` | `'Unknown prompt: {...}'` |

## Tool schemas

### Utility tools

| Tool | Description | Required parameters | Optional parameters |
|------|-------------|-------------------|-------------------|
| `auth_status` | Get authentication strategy status. Shows current configuration, subscription tier, and default mode | | |
| `auth_recommend` | Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode | `file_path: str` | |
| `telemetry_stats` | Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance | | `days: int = 30` |
| `attune_get_level` | Get current interaction level (1-5). Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems | | |
| `attune_set_level` | Set interaction level (1-5) for this session | `level: int` (1-5) | |
| `context_get` | Get session context value | `key: str` | |
| `context_set` | Set session context value | `key: str, value: str` | |

### Help tools

| Tool | Description | Required parameters | Optional parameters |
|------|-------------|-------------------|-------------------|
| `help_lookup` | Look up contextual help for a topic, workflow, or error. Progressive mode escalates across template types | `topic: str` | `mode: str = 'progressive', file_path: str, last_workflow: str, reset: bool = False` |
| `help_maintain` | Check for stale help templates and regenerate them | | `dry_run: bool = False, batch: bool = False` |
| `help_init` | Bootstrap a project-local help system | `action: str` ('scan' \| 'accept') | `accepted: array` |
| `help_status` | Show staleness report for the project-local help system | | `features: array[str]` |
| `help_update` | Regenerate help templates for specific features or all stale features | | `features: array[str], dry_run: bool = False` |

### Personal memory tools

| Tool | Description | Required parameters | Optional parameters |
|------|-------------|-------------------|-------------------|
| `personal_memory_capture` | Save a decision, pattern, troubleshooting finding, or reference to personal cross-session memory | `topic: str, content: str` | `kind: str = 'decision', project_local: bool = False` |
| `personal_memory_recall` | Search personal cross-session memory with a natural language query | `query: str` | `k: int = 3, kind_filter: str` |
| `personal_memory_topics` | List all topics stored in personal cross-session memory | | |
| `personal_memory_forget` | Delete a topic from personal memory | `topic: str` | `kind: str` |

### Memory tools

| Tool | Description | Required parameters | Optional parameters |
|------|-------------|-------------------|-------------------|
| `memory_store` | Store data in attune-ai memory | `key: str, value: str` | `classification: str = 'PUBLIC', pattern_type: str` |
| `memory_retrieve` | Retrieve data from attune-ai memory by key or pattern ID | `key: str` | |
| `memory_search` | Search attune-ai memory for patterns matching a query | `query: str` | `pattern_type: str` |
| `memory_forget` | Remove data from attune-ai memory | `key: str` | `scope: str = 'all'` |

## Resources

| Resource | URI | Description | MIME type |
|----------|-----|-------------|-----------|
| `workflows` | `attune://workflows` | List of all available Attune workflows | `application/json` |
| `auth_config` | `attune://auth/config` | Current authentication strategy configuration | `application/json` |
| `telemetry` | `attune://telemetry` | Cost tracking and performance metrics | `application/json` |

## Constants

| Constant | Value |
|----------|-------|
| `_MEMORY_NOT_INSTALLED` | `'attune-ai memory module not installed. Run: pip install attune-ai'` |
| `_VOICE_SKIP_TOOLS` | Tools excluded from voice interface: `{'memory_store', 'memory_retrieve', 'memory_search', 'memory_forget', 'personal_memory_capture', 'personal_memory_recall', 'personal_memory_topics', 'personal_memory_forget', 'attune_get_level', 'attune_set_level', 'context_get', 'context_set', 'auth_status', 'auth_recommend', 'telemetry_stats'}` |
