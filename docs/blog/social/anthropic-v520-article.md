# Building 18 Production Workflows on the Claude Agent SDK

*For the Anthropic blog / community*

---

We just shipped [attune-ai v5.2.0](https://pypi.org/project/attune-ai/), completing a three-release migration to full Anthropic best-practices alignment. Every workflow now runs on the Claude Agent SDK with system prompt separation, per-agent model routing, and budget controls.

Here's what we built — and what we learned building it.

## Why the Agent SDK

Attune-ai ships 18 multi-agent workflows for Claude Code: code review, security audit, test generation, bug prediction, release prep, and more. Each workflow runs a team of 2-6 specialized Claude subagents.

Before v5.0, we managed agent lifecycle, message passing, and result collection ourselves. The Agent SDK replaced all of that with a clean abstraction that handles the hard parts — letting us focus on what each agent actually does.

### What Each Workflow Gets from the SDK

**System prompt separation.** Every workflow splits persona instructions (who the agent is) from task instructions (what it should do right now). This follows Anthropic's recommendation for keeping system context stable across runs.

**Model routing.** We route by task type, not by workflow:

- **Opus** — Security analysis, architecture review. Tasks where missing a subtle vulnerability is expensive.
- **Sonnet** — Code review, planning, test generation. Analytical work that needs quality but not maximum reasoning depth.
- **Haiku** — File scanning, linting, coverage indexing. High-volume mechanical tasks where speed matters more than nuance.

This isn't configuration — it's built into each workflow's agent definitions. A security audit workflow uses Haiku for file discovery, Sonnet for pattern analysis, and Opus for final validation. Three models in one workflow.

**Budget caps.** Every workflow enforces cost limits: $0.50 quick, $2.00 standard, $5.00 deep. Users can override with `ATTUNE_MAX_BUDGET_USD`. This was a direct response to early users running deep security audits on large codebases and getting surprised by costs.

**Structured output.** Security audits and code reviews return typed JSON with confidence scores, severity levels, and file locations — not just narrative text. This makes results machine-readable for CI integration.

## Claude Code Plugin Integration

Attune-ai is a Claude Code plugin. Each of the 18 workflows is exposed as one of 31 MCP tools, triggered automatically by 10 auto-invoking skills.

In practice, this means a user can say "check this module for security issues" and Claude calls the right MCP tool with the right parameters. No slash commands, no memorizing workflow names.

We also ship security hooks with the plugin:

- **PreToolUse** blocks `eval()`/`exec()` in bash commands and validates file paths on writes
- **PostToolUse** auto-formats Python output

These run automatically — zero configuration.

## What's New in v5.2.0

**Unified voice layer.** With 18 workflows returning results in different formats, we added a `VoiceFormatter` that normalizes output into a consistent tone. Structured data is preserved — voice is a presentation layer.

**Security hardening.** We ran our own `bug-predict` workflow against our source code and found 5 path traversal gaps (CWE-22) in file operations that accepted user paths without validation. The same scanning workflow we ship to users caught real vulnerabilities in our own 15,591-test codebase.

## The Migration Path

| Version | What Changed |
| ------- | ------------ |
| **v5.0** | Migrated all 15 workflows to Claude Agent SDK. Added system prompt separation, model routing, budget caps, structured output |
| **v5.1** | Built Claude Code plugin layer. 31 MCP tools, 10 skills, security hooks. Full plugin SDK compliance |
| **v5.2** | Added voice layer for consistent output. Hardened path validation. 15,591 tests passing |

## Try It

```bash
pip install 'attune-ai[developer]'
```

Type `/attune` in Claude Code. Socratic discovery asks what you're trying to accomplish and routes you to the right workflow.

- [GitHub](https://github.com/Smart-AI-Memory/attune-ai)
- [PyPI](https://pypi.org/project/attune-ai/)
- [Claude Agent SDK docs](https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk)
