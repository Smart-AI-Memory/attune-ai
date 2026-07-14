---
type: faq
name: mcp-server-faq
feature: mcp-server
depth: faq
generated_at: 2026-07-14T15:58:53.618940+00:00
source_hash: 08e50eacebc45c71e34c3de6ca5e70b0eed13373bff884ee18bc5f88124ac95f
status: generated
---

# Mcp Server FAQ

## What is the MCP server?

`EmpathyMCPServer` — attune's Model Context Protocol server. It
exposes attune's workflows, help, and memory as MCP tools/resources/
prompts to a client like Claude Code, over stdio.

## How do I run it / make the tools show up?

Register `python -m attune.mcp.server` in `.mcp.json` (the
plugin ships one). Run it directly with the same command for testing.

## How many tools does it expose?

41 built-in — across workflow (21), utility (7), help (5),
memory (4), and personal-memory (4) categories — plus any registered
by installed plugins (e.g. attune-redis's five `redis_*` tools), and
3 resources and 3 prompts.

## Is `call_tool` async?

Yes — `await` it. `create_server()`, `get_resource_list()`,
and `get_prompt_list()` are synchronous.

## Why don't I see server output in my terminal?

stdio is the MCP protocol channel; logs go to
`<tmp>/attune/attune-mcp.log`.
