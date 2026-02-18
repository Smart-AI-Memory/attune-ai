# attune-ai

AI-powered developer workflows with Socratic discovery, persistent memory, and multi-agent orchestration for Claude Code. One command -- `/attune` -- intelligently routes you to security audits, code reviews, test generation, performance analysis, and more through a guided, conversational interface.

**Version:** 2.10.4 | **License:** Apache 2.0 | **Python:** 3.10+

## Installation

Install from PyPI:

```bash
pip install attune-ai
```

For multi-agent coordination with Redis:

```bash
pip install attune-ai[redis]
```

## Quick Start

After installation, use the single entry point in any Claude Code session:

```text
/attune
```

The Socratic discovery flow will ask what you need, understand your intent, and route you to the right workflow, skill, or tool -- no need to memorize commands. First-time users are guided through authentication setup automatically.

To configure LLM authentication directly:

```bash
python -m attune.models.auth_cli setup
```

## Skills

Skills are high-level capabilities exposed as slash commands within Claude Code.

| Skill | Description |
| ----- | ----------- |
| `memory-and-context` | Store, retrieve, search, and manage persistent memory across sessions. Set and query context for long-running tasks. |
| `workflow-orchestration` | Run automated analysis workflows: security audits, code reviews, test generation, bug prediction, performance analysis, and release preparation. |
| `refactor-plan` | Generate structured refactoring plans with dependency analysis, risk assessment, and step-by-step execution guidance. |

## MCP Tools

18 tools are available when connected via the Model Context Protocol, organized into two categories.

### Workflow Tools (10)

| Tool | Description |
| ---- | ----------- |
| `security_audit` | Scan for vulnerabilities including eval/exec usage, path traversal, hardcoded secrets, and injection risks |
| `bug_predict` | Predict likely bugs using pattern analysis, historical data, and code complexity metrics |
| `code_review` | Automated code review with style, correctness, and security checks |
| `test_generation` | Generate unit tests with edge cases, parametrized inputs, and security test coverage |
| `performance_audit` | Identify performance bottlenecks, unnecessary list copies, and optimization opportunities |
| `release_prep` | Pre-release checklist: version bumps, changelog validation, dependency audits, and health checks |
| `auth_status` | Check current LLM authentication configuration and provider status |
| `auth_recommend` | Get provider recommendations based on usage patterns and cost optimization |
| `telemetry_stats` | View cost tracking, token usage, and cache hit rate statistics |
| `dashboard_status` | Query agent coordination dashboard state and active workflow status |

### Memory, Empathy, and Context Tools (8)

| Tool | Description |
| ---- | ----------- |
| `memory_store` | Persist key-value data across sessions with optional TTL and metadata |
| `memory_retrieve` | Retrieve stored memory entries by key |
| `memory_search` | Search memory entries by content, tags, or metadata |
| `memory_forget` | Remove specific memory entries |
| `empathy_get_level` | Get the current empathy/verbosity level for responses |
| `empathy_set_level` | Adjust empathy/verbosity level to control response detail |
| `context_get` | Retrieve session or task context by key |
| `context_set` | Set session or task context for downstream tool use |

## Redis Upgrade Path

The default installation uses local storage for memory and single-agent operation. Adding Redis unlocks:

- **Multi-agent coordination** -- Multiple Claude Code agents share state and avoid duplicated work
- **Persistent memory across machines** -- Memory entries survive beyond a single environment
- **Agent dashboard** -- Real-time visibility into agent teams, task queues, and workflow progress
- **Distributed locking** -- Safe concurrent access to shared resources

Upgrade with a single command:

```bash
pip install attune-ai[redis]
```

Then set the `REDIS_URL` environment variable or configure via `/attune`.

## Links

- **Homepage:** [smartaimemory.com](https://smartaimemory.com)
- **GitHub:** [github.com/Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
- **PyPI:** [pypi.org/project/attune-ai](https://pypi.org/project/attune-ai/)
- **Documentation:** [smartaimemory.com/docs](https://smartaimemory.com/docs)
