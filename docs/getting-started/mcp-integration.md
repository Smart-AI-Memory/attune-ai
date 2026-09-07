---
description: Connect Attune AI to Claude Code via MCP. Enable AI workflows, agent coordination, and pattern learning in your IDE.
---

# MCP Integration

Connect Attune AI workflows directly to Claude Code or Claude Desktop using the Model Context Protocol.

The Attune MCP server exposes all production workflows as native tools — security audits, test generation, performance analysis, and more.

---

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard for connecting AI applications to external tools and data sources. Attune AI exposes its workflows, authentication system, and telemetry as MCP tools.

---

## Quick Setup

### Option 1: Claude Code (Automatic)

**Best for:** Development workflows in VSCode

Attune AI includes `.claude/mcp.json` configuration. Claude Code automatically discovers the MCP server when you open the project.

1. **Install Attune AI:**

```bash
pip install attune-ai
```

2. **Open project in Claude Code**

The MCP server is automatically configured via `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "attune-ai": {
      "command": "uv",
      "args": ["run", "python", "-m", "attune.mcp.server"],
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "ATTUNE_REDIS_REQUIRED": "false"
      }
    }
  }
}
```

3. **Restart Claude Code** to load the server

4. **Use natural language:**

```
"Run a security audit on src/"
"Generate tests for config.py"
"Check my authentication configuration"
"Analyze performance bottlenecks"
```

### Option 2: Claude Desktop (Manual)

**Best for:** General-purpose AI workflows

Add to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
    "mcpServers": {
        "attune": {
            "command": "python",
            "args": ["-m", "attune.mcp.server"],
            "env": {
                "ANTHROPIC_API_KEY": "your-api-key-here",
                "PYTHONPATH": "/path/to/attune-ai/src"
            }
        }
    }
}
```

Then restart Claude Desktop.

---

## <!-- cap:mcp_registered_tool_count -->Available Tools (65)<!-- /cap -->

The Attune MCP server exposes all production workflows as tools:

### Workflow Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `security_audit` | Scan code for vulnerabilities, dangerous patterns, security issues | `path` |
| `bug_predict` | Analyze code patterns and predict potential bugs | `path` |
| `code_review` | Comprehensive code quality analysis with suggestions | `path` |
| `test_generation` | Generate tests for code (supports batch mode) | `module`, `batch` (optional) |
| `performance_audit` | Identify bottlenecks, memory leaks, optimization opportunities | `path` |
| `release_notes` | Changelog draft + go/no-go advisory (not a gate) | `path` (optional) |
| `doc_audit` | Audit documentation coverage and freshness | `path` |
| `doc_gen` | Generate documentation for source code | `source_path` |
| `test_audit` | Deep test coverage analysis | `path` |
| `refactor_plan` | Identify refactoring opportunities and generate roadmap | `path` |
| `dependency_check` | Audit dependencies for vulnerabilities and updates | `path` |
| `simplify_code` | Find and simplify overly complex code | `path` |
| `deep_review` | Multi-pass security + quality + test-gap review | `path` |
| `health_check` | Comprehensive project health score | `project_root` |
| `research_synthesis` | Synthesize insights from local source documents at a path | `path` (optional), `depth` (optional) |
| `analyze_batch` | Submit tasks to Anthropic Batch API (50% cost savings) | `requests` |
| `rag_knowledge_query` | Query the RAG corpus for contextual knowledge | `query` |

### Vision Tool

| Tool | Description | Required Args |
|------|-------------|---------------|
| `analyze_image` | Analyze an image using Claude's vision capabilities | `image_path` |

**`analyze_image` usage:**
```json
{
  "image_path": "screenshots/error.png",
  "prompt": "What error is shown and what might cause it?"
}
```

Supports `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`. Maximum file size: 10 MB.
Requires `ANTHROPIC_API_KEY` in the environment.

**Example — diagnosing a UI bug from a screenshot:**
```
User: "Analyze this screenshot and explain what's wrong"
Claude: [Invokes analyze_image with image_path="screenshots/bug.png"]
→ Returns analysis: "The modal is rendering behind the overlay (z-index issue)..."
```

### Authentication & Monitoring Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `auth_status` | Get authentication strategy status and configuration | none |
| `auth_recommend` | Get authentication recommendation for a file | `file_path` |
| `telemetry_stats` | Get cost savings, cache hit rates, workflow performance | `days` (optional) |
| `attune_get_level` | Get current Attune interaction level (1–5) | none |
| `attune_set_level` | Set the Attune interaction level | `level` |
| `context_get` | Retrieve a value from the session context store | `key` |
| `context_set` | Store a value in the session context store | `key`, `value` |

### Help System Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `help_lookup` | Look up guidance for a topic | `topic` |
| `help_init` | Initialize the help system for a project | none |
| `help_status` | Check help template freshness | none |
| `help_update` | Update stale help templates | none |
| `help_maintain` | Run help system maintenance tasks | none |

### Memory Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `memory_store` | Store a key-value pair in persistent memory | `key`, `value` |
| `memory_retrieve` | Retrieve a stored value | `key` |
| `memory_search` | Search stored memory by query | `query` |
| `memory_forget` | Delete a stored memory entry | `key` |
| `personal_memory_capture` | Save a topic to cross-session personal memory | `topic`, `content` |
| `personal_memory_recall` | Retrieve a personal memory topic | `topic` |
| `personal_memory_topics` | List all personal memory topics | none |
| `personal_memory_forget` | Delete a personal memory topic | `topic` |

### Redis Plugin Tools (attune-redis)

Installed with `pip install attune-ai`. Adds 5 additional tools:
`redis_memory_store`, `redis_memory_retrieve`, `redis_memory_search`,
`redis_memory_promote`, `redis_health_check`.

### MCP Resources (3)

| Resource URI | Description |
|--------------|-------------|
| `attune://workflows` | List of all available workflows |
| `attune://auth/config` | Current authentication strategy configuration |
| `attune://telemetry` | Cost tracking and performance metrics |

---

## Example Usage

### In Claude Code

Natural language commands are automatically routed to the appropriate tool:

**Security Analysis:**
```
User: "Run a security audit on the authentication module"
Claude: [Invokes security_audit tool with path="src/auth/"]
```

**Test Generation:**
```
User: "Generate tests for the config module"
Claude: [Invokes test_generation tool with module="src/attune/config.py"]
```

**Cost Optimization:**
```
User: "What's my current authentication setup?"
Claude: [Invokes auth_status tool]
Response: {
  "success": true,
  "subscription_tier": "max",
  "default_mode": "api",
  "setup_completed": true
}
```

### In Claude Desktop

Direct tool invocation or natural language:

> **You:** Check for security vulnerabilities in my API code

> **Claude:** I'll run a security audit using the attune security_audit tool.
>
> *[Invokes security_audit(path="src/api/")]*
>
> Found 3 medium-severity issues:
> 1. SQL injection risk in query builder (line 42)
> 2. Missing input validation on user endpoint (line 78)
> 3. Weak password hashing algorithm (line 156)

---

## Testing the MCP Server

### Quick Test

```bash
# Test tool listing
echo '{"method":"tools/list","params":{}}' | PYTHONPATH=./src python -m attune.mcp.server

# Test tool execution
echo '{"method":"tools/call","params":{"name":"auth_status","arguments":{}}}' | PYTHONPATH=./src python -m attune.mcp.server
```

### Verify Integration

```bash
# Check server starts without errors
python -m attune.mcp.server --help

# View comprehensive test results
cat .claude/MCP_TEST_RESULTS.md
```

---

## Verification Hooks

Attune automatically validates outputs via Claude Code hooks:

**Python File Validation:**
- Syntax checking after file writes
- Imports and dependencies verified

**JSON File Validation:**
- Format checking after file writes
- Schema validation where applicable

**Workflow Output Verification:**
- AI-powered validation of workflow results
- Ensures required fields are present
- Catches common errors

Configuration in `.claude/settings.local.json` (automatically set up).

---

## Troubleshooting

### Server Not Starting

**Check Python environment:**
```bash
python -c "import attune.mcp.server; print('OK')"
```

**Check PYTHONPATH:**
```bash
# Should include src directory
echo $PYTHONPATH
```

### Tools Not Available in Claude Code

1. **Verify `.claude/mcp.json` exists** in project root
2. **Restart Claude Code** completely
3. **Check Claude Code status bar** for "attune" server
4. **Review logs** in Claude Code output panel

### Tools Not Available in Claude Desktop

1. **Verify config path** is correct for your OS
2. **Check JSON syntax** - use a validator
3. **Set PYTHONPATH** to absolute path of attune-ai/src
4. **Restart Claude Desktop** fully (quit and reopen)

### Tool Execution Fails

**Check API key:**
```bash
echo $ANTHROPIC_API_KEY
```

**Check workflow dependencies:**
```bash
pip install attune-ai
```

**Review error logs:**
- Claude Code: Output panel → "Claude Code" channel
- Claude Desktop: Application logs
- Direct test: Stderr output from python command

---

## MCP vs CLI vs Python API

| Use Case | Best Interface |
|----------|----------------|
| Development in VSCode | **MCP (Claude Code)** - Natural language, automatic discovery |
| Interactive exploration | **MCP (Claude Desktop)** - Conversational, guided workflows |
| CI/CD pipelines | **CLI** - `attune workflow run security-audit` |
| Custom integrations | **Python API** - Full programmatic control |

---

## Alternative Clients

The MCP server works with any MCP-compatible client:

- **Claude Code** (VSCode extension) - Automatic project discovery
- **Claude Desktop** - General-purpose AI assistant
- **Cursor IDE** - Similar configuration to Claude Desktop
- **Custom clients** - Use the MCP SDK to connect
- **CLI testing** - Pipe JSON-RPC messages directly

---

## Next Steps

- **[CLI Reference](../reference/cli-reference.md)** - Command-line interface
- **Python API** - Programmatic access
- **[How-to Guides](../how-to/index.md)** - Workflow documentation

---

## Legacy: Socratic MCP Server

**Note:** The Socratic workflow builder MCP server (`attune.socratic.mcp_server`) is deprecated in v6.3.0+. Use the production Attune MCP server (`attune.mcp.server`) instead, which exposes all workflows directly.
