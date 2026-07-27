# attune-ai

Spec-driven development for Claude Code — turn requirements
into reliable software. <!-- cap:skill_count -->26 auto-triggering skills<!-- /cap -->, zero
commands: say what you need and Claude picks the right skill.

**Version:** 10.6.0 | **License:** Apache 2.0

## Install

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

Update an existing install:

```bash
claude plugin update attune-ai
```

## Usage

Just describe what you need in Claude Code:

- "what can attune do?" — triggers `attune-hub`
- "review my code" — triggers `code-quality`
- "scan for security issues" — triggers `security-audit`
- "generate tests for src/" — triggers `smart-test`
- "fix failing tests" — triggers `fix-test`
- "predict bugs" — triggers `bug-predict`
- "generate docs" — triggers `doc-gen`
- "plan this feature" — triggers `planning`
- "refactor this module" — triggers `refactor-plan`
- "prepare a release" — triggers `release-prep`
- "build from a spec" — triggers `spec`

## Skills

| Skill | Triggers On |
| ----- | ----------- |
| `attune-hub` | what can attune do, help, capabilities |
| `spec` | build from scratch, brainstorm and execute |
| `security-audit` | security, vulnerability, scan |
| `code-quality` | review, quality, bugs, code smell |
| `bug-predict` | predict bugs, risky code, what might break |
| `doc-gen` | generate docs, documentation, README |
| `smart-test` | test gaps, generate tests, coverage |
| `fix-test` | fix test, broken test, debug test |
| `workflow-orchestration` | workflow, analyze, run |
| `planning` | plan, feature, architecture, TDD |
| `refactor-plan` | refactor, tech debt, simplify |
| `release-prep` | release, publish, deploy |
| `memory-and-context` | memory, store, retrieve |

## Agents

Autonomous sub-agents (auto-discovered from `plugin/agents/`):

| Agent | Use it when |
| ----- | ----------- |
| `setup-guide` | checking prerequisites; installing/configuring attune-ai, Redis, MCP |
| `spec-author` | spec a new feature — runs the SDD requirements interview and writes `requirements.md` (Phase 1 only; design/tasks stay gated) |
| `help-content-explainer` | explain an attune-help template *for your repo* — grounds the template's guidance in your actual code (read-only) |
| `security-reviewer` | read-only security pass — scans for eval/exec, path traversal, injection, secrets; reports findings by severity |
| `release-prep-auditor` | pre-release pre-flight — version/tree/CI/changelog/security/deps → ready or not-ready verdict (reports only) |
| `refactor-planner` | analyze a target for smells/duplication/complexity → prioritized refactoring roadmap (plans only) |

## Hooks

The plugin ships two security hooks:

- **PreToolUse** — blocks `eval()`, `exec()`, path
  traversal, and `rm -rf /` in Bash; validates file
  paths in Edit/Write
- **PostToolUse** — auto-formats Python with `black`
  and `ruff --fix` after Write/Edit

## Python Package (optional — unlocks CLI + MCP)

The plugin works standalone. Add the Python package
for CLI automation, <!-- cap:mcp_registered_tool_count -->60 MCP tools<!-- /cap -->, multi-agent
workflows, and cost tracking:

```bash
pip install 'attune-ai[developer]'
```

| Capability | Plugin only | + pip |
| ---------- | ----------- | ----- |
| <!-- cap:skill_count -->26 auto-triggering skills<!-- /cap --> | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| <!-- cap:mcp_registered_tool_count -->60 MCP tools<!-- /cap --> | -- | Yes |
| `attune` CLI | -- | Yes |
| Multi-agent workflows | -- | Yes |
| Cost tracking | -- | Yes |

## Links

- [GitHub](https://github.com/Smart-AI-Memory/attune-ai)
- [PyPI](https://pypi.org/project/attune-ai/)
- [Documentation](https://smartaimemory.com/docs)
