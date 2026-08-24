---
name: mcp-server
source: content/features/mcp-server.md
tags:
- mcp
- tools
- server
type: warning
---

# The Model Context Protocol server that exposes attune workflows, help, and memory as tools

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| Tools don't appear in Claude Code | The `.mcp.json` entry is missing or the command can't launch | Add/repair the `mcpServers` entry; confirm `python -m attune.mcp.server` runs | high |
| `RuntimeWarning: coroutine 'AttuneMCPServer.call_tool' was never awaited` | `call_tool` invoked without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| Tool calls start getting rejected under load | The rate limiter tripped (60 calls / 60 s) | Slow the call rate, or construct with a higher `max_calls` | medium |
| A tool returns a "path/argument required" error | The tool's own input contract wasn't met | See that tool's feature page; the server just dispatches | medium |
| Can't tell why the connection failed | Logs aren't on stdout (stdio is the protocol channel) | Read `<tmp>/attune/attune-mcp.log` | low |

### Risk areas

- **`call_tool` is async.** Dispatching without `await` is the common
  mistake when driving the server from Python.
- **stdio is the protocol channel.** Don't print to stdout from a
  handler — logs go to the temp log file, not the console.
- **The server dispatches; tools own their contracts.** A tool-level
  error (bad args) is the tool's, not the server's.

### Diagnosis order

1. Confirm the server launches: `python -m attune.mcp.server`.
2. Confirm registration: the `.mcp.json` `mcpServers` entry.
3. From Python, `create_server().tools` / `get_resource_list()` to
   confirm the surface.
4. For a connection problem, read `<tmp>/attune/attune-mcp.log`.
5. For a single tool failing, consult that tool's feature page.
