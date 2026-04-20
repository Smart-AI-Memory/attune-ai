---
type: reference
feature: mcp-server
depth: reference
generated_at: 2026-04-20T01:20:13.171508+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# MCP server API reference

Build MCP-compliant servers and integrate Attune AI workflows with Claude Desktop and other MCP clients.

## Classes

| Class | Parameters | Returns | Description |
|-------|------------|---------|-------------|
| `MemoryHandlersMixin` | | | Mixin providing memory tool handlers for EmpathyMCPServer |
| `RateLimiter` | `max_calls: int = 60, window_seconds: float = 60.0` | `None` | Simple sliding-window rate limiter |
| `EmpathyMCPServer` | `workspace_root: str \| None = None, user_id: str \| None = None` | | MCP server for Attune AI workflows |
| `WorkflowHandlersMixin` | | | Mixin providing workflow tool handlers for EmpathyMCPServer |

### RateLimiter methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `check` | `key: str` | `bool` | Check if a key is within rate limits |

### EmpathyMCPServer methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_prompt_list` | | `list[dict[str, Any]]` | Get list of available prompts |
| `get_prompt_messages` | `prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt |
| `call_tool` | `tool_name: str, arguments: dict[str, Any]` | `dict[str, Any]` | Execute a tool by name with arguments |
| `get_tool_list` | | `list[dict[str, Any]]` | Get list of available tools |
| `get_resource_list` | | `list[dict[str, Any]]` | Get list of available resources |

## Functions

| Function | Parameters | Returns | Description | Raises |
|----------|------------|---------|-------------|--------|
| `get_prompt_list` | `prompts: dict[str, dict[str, Any]]` | `list[dict[str, Any]]` | Get list of available prompts | |
| `get_prompt_messages` | `prompts: dict[str, dict[str, Any]], prompt_name: str, arguments: dict[str, str]` | `list[dict[str, Any]]` | Get messages for a specific prompt | ValueError — 'Unknown prompt: {...}' |
| `create_server` | | `EmpathyMCPServer` | Create and return an Empathy MCP server instance | |
| `main` | | `None` | Entry point for MCP server | |
| `get_workflow_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for workflow execution tools | |
| `get_utility_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for auth, telemetry, and session management | |
| `get_help_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for contextual help and progressive documentation | |
| `get_memory_tools` | | `dict[str, dict[str, Any]]` | Tool definitions for memory store/retrieve/search/forget | |
| `get_resources` | | `dict[str, dict[str, Any]]` | MCP resource definitions | |
| `get_prompts` | | `dict[str, dict[str, Any]]` | MCP prompt definitions | |

## Tool schemas

### Utility tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `auth_status` | Get authentication strategy status. Shows current configuration, subscription tier, and default mode. | None |
| `auth_recommend` | Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode. | `file_path` (string, required) — Path to file to analyze |
| `telemetry_stats` | Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance. | `days` (integer, default: 30) — Number of days to analyze |
| `attune_get_level` | Get current interaction level (1-5). Level 1=Reactive, 2=Guided, 3=Proactive, 4=Anticipatory, 5=Systems. | None |
| `attune_set_level` | Set interaction level (1-5) for this session. | `level` (integer, 1-5, required) — Interaction level |
| `context_get` | Get session context value. | `key` (string, required) — Context key to retrieve |
| `context_set` | Set session context value. | `key` (string, required) — Context key<br>`value` (string, required) — Context value |

### Help tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `help_lookup` | Look up contextual help for a topic, workflow, or error. Progressive mode escalates across template types. Repeated calls auto-advance. | `topic` (string, required) — Topic slug, template ID, workflow name, or tag<br>`mode` (enum: progressive, preamble, related, workflow_help, precursor, search_tag, default: progressive)<br>`file_path` (string) — File path for precursor mode<br>`last_workflow` (string) — Name of the last workflow<br>`reset` (boolean, default: false) — Reset depth to concept level |
| `help_maintain` | Check for stale help templates and regenerate them. Detects when source files have changed since last generation. | `dry_run` (boolean, default: false) — Only report stale templates<br>`batch` (boolean, default: false) — Submit to Anthropic Batch API for 50% cost savings |
| `help_init` | Bootstrap a project-local help system. Scans the project to discover features, returns proposals for review. | `action` (enum: scan, accept, required) — scan: discover features, accept: save manifest<br>`accepted` (array of objects) — List of accepted feature proposals (only used with action=accept) |
| `help_status` | Show staleness report for the project-local help system. Reports which features have current vs stale templates. | `features` (array of strings) — Optional list of feature names to check |
| `help_update` | Regenerate help templates for specific features or all stale features in the project-local help system. | `features` (array of strings) — Feature names to regenerate<br>`dry_run` (boolean, default: false) — Only report what would change |

### Memory tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `memory_store` | Store data in attune-ai memory. Use for structured knowledge, patterns, and cross-agent coordination. | `key` (string, required) — Unique identifier<br>`value` (string, required) — Content to store<br>`classification` (enum: PUBLIC, INTERNAL, SENSITIVE, default: PUBLIC)<br>`pattern_type` (string) — Category for pattern matching |
| `memory_retrieve` | Retrieve data from attune-ai memory by key or pattern ID. | `key` (string, required) — Key or pattern_id to retrieve |
| `memory_search` | Search attune-ai memory for patterns matching a query. | `query` (string, required) — Search string<br>`pattern_type` (string) — Filter by pattern type |
| `memory_forget` | Remove data from attune-ai memory. | `key` (string, required) — Key or pattern_id to remove<br>`scope` (enum: session, persistent, all, default: all) — Scope of removal |

## Resources

| Resource | URI | Description | MIME Type |
|----------|-----|-------------|-----------|
| `workflows` | `attune://workflows` | List of all available Attune workflows | `application/json` |
| `auth_config` | `attune://auth/config` | Current authentication strategy configuration | `application/json` |
| `telemetry` | `attune://telemetry` | Cost tracking and performance metrics | `application/json` |

## Prompts

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `security-scan` | Run a comprehensive security scan on a directory. Checks for eval/exec usage, path traversal, hardcoded secrets, and broad exception handling. | `path` (required) — Directory or file to scan |
| `test-gen` | Generate behavioral tests for a Python module. Creates pytest test files with Given/When/Then structure. | `module` (required) — Path to Python module<br>`batch` (optional) — Set to 'true' to generate tests for all modules |
| `cost-report` | Generate a cost optimization report. Shows LLM spend by workflow, cache hit rates, and savings from tier routing. | `days` (optional) — Number of days to analyze (default: 30) |

## Constants

| Constant | Description |
|----------|-------------|
| `_VOICE_SKIP_TOOLS` | Tools excluded from voice interfaces: memory operations, context management, authentication status |
