---
type: reference
feature: mcp-server
depth: reference
generated_at: 2026-05-04T02:30:02.079856+00:00
source_hash: f7f2360f6ad84733ba187b2e644d9b01ac30e15d2ae8fe8567af6dfb064ee44b
status: generated
---

# MCP server

Build MCP-compatible servers that expose Attune AI workflows, help system, memory tools, and authentication utilities to clients like Claude Desktop.

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
| `__init__` | `max_calls: int = 60, window_seconds: float = 60.0` | `None` | Initialize rate limiter with call limits |
| `check` | `key: str` | `bool` | Check if key is within rate limits |

### EmpathyMCPServer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `workspace_root: str \| None = None, user_id: str \| None = None` | - | Initialize MCP server with workspace and user context |
| `get_prompt_list` | - | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `call_tool` | `tool_name: str, arguments: dict[str, Any]` | `dict[str, Any]` | Execute a tool with provided arguments |
| `get_tool_list` | - | `list[dict[str, Any]]` | Get list of available tools |
| `get_resource_list` | - | `list[dict[str, Any]]` | Get list of available resources |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_prompt_list` | `prompts: dict[str, dict[str, Any]]` | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompts: dict[str, dict[str, Any]], prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `create_server` | - | `EmpathyMCPServer` | Create and return an Empathy MCP server instance |
| `main` | - | `None` | Entry point for MCP server |
| `get_workflow_tools` | - | `dict[str, dict[str, Any]]` | Tool definitions for workflow execution tools |
| `get_utility_tools` | - | `dict[str, dict[str, Any]]` | Tool definitions for auth, telemetry, and session management |
| `get_help_tools` | - | `dict[str, dict[str, Any]]` | Tool definitions for contextual help and progressive documentation |
| `get_personal_memory_tools` | - | `dict[str, dict[str, Any]]` | Tool definitions for personal cross-session memory |
| `get_memory_tools` | - | `dict[str, dict[str, Any]]` | Tool definitions for memory store/retrieve/search/forget |
| `get_resources` | - | `dict[str, dict[str, Any]]` | MCP resource definitions |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `get_prompt_messages` | `ValueError` | 'Unknown prompt: {...}' |

### Tool schemas

#### get_utility_tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `auth_status` | - | Get authentication strategy status. Shows current configuration, subscription tier, and default mode |
| `auth_recommend` | `file_path: str` (required) | Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode |
| `telemetry_stats` | `days: int = 30` | Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance |
| `attune_get_level` | - | Get current interaction level (1-5). Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems |
| `attune_set_level` | `level: int` (required, min: 1, max: 5) | Set interaction level (1-5) for this session |
| `context_get` | `key: str` (required) | Get session context value |
| `context_set` | `key: str, value: str` (required) | Set session context value |

#### get_help_tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `help_lookup` | `topic: str` (required), `mode: str = 'progressive'`, `file_path: str`, `last_workflow: str`, `reset: bool = False` | Look up contextual help for a topic, workflow, or error. Progressive mode escalates across template types |
| `help_maintain` | `dry_run: bool = False`, `batch: bool = False` | Check for stale help templates and regenerate them |
| `help_init` | `action: str` (required), `accepted: array` | Bootstrap a project-local help system. Scans the project to discover features |
| `help_status` | `features: array` | Show staleness report for the project-local help system |
| `help_update` | `features: array`, `dry_run: bool = False` | Regenerate help templates for specific features or all stale features |

#### get_personal_memory_tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `personal_memory_capture` | `topic: str, content: str` (required), `kind: str = 'decision'`, `project_local: bool = False` | Save a decision, pattern, troubleshooting finding, or reference to personal cross-session memory |
| `personal_memory_recall` | `query: str` (required), `k: int = 3`, `kind_filter: str` | Search personal cross-session memory with a natural language query |
| `personal_memory_topics` | - | List all topics stored in personal cross-session memory |
| `personal_memory_forget` | `topic: str` (required), `kind: str` | Delete a topic from personal memory |

#### get_memory_tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `memory_store` | `key: str, value: str` (required), `classification: str = 'PUBLIC'`, `pattern_type: str` | Store data in attune-ai memory |
| `memory_retrieve` | `key: str` (required) | Retrieve data from attune-ai memory by key or pattern ID |
| `memory_search` | `query: str` (required), `pattern_type: str` | Search attune-ai memory for patterns matching a query |
| `memory_forget` | `key: str` (required), `scope: str = 'all'` | Remove data from attune-ai memory |

### Resources

| Resource | URI | Description |
|----------|-----|-------------|
| `workflows` | `attune://workflows` | List of all available Attune workflows |
| `auth_config` | `attune://auth/config` | Current authentication strategy configuration |
| `telemetry` | `attune://telemetry` | Cost tracking and performance metrics |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `_VOICE_SKIP_TOOLS` | `{'memory_store', 'memory_retrieve', 'memory_search', 'memory_forget', 'personal_memory_capture', 'personal_memory_recall', 'personal_memory_topics', 'personal_memory_forget', 'attune_get_level', 'attune_set_level', 'context_get', 'context_set', 'auth_status', 'auth_recommend', 'telemetry_stats'}` | Tools excluded from voice interfaces |
