# attune-ai

Spec-driven development for Claude Code — turn requirements
into reliable software. 17 auto-triggering skills, zero
commands: say what you need and Claude picks the right skill.

**Version:** 8.5.0 | **License:** Apache 2.0

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

## Hooks

The plugin ships two security hooks:

- **PreToolUse** — blocks `eval()`, `exec()`, path
  traversal, and `rm -rf /` in Bash; validates file
  paths in Edit/Write
- **PostToolUse** — auto-formats Python with `black`
  and `ruff --fix` after Write/Edit

## Python Package (optional — unlocks CLI + MCP)

The plugin works standalone. Add the Python package
for CLI automation, 41 MCP tools, multi-agent
workflows, and cost tracking:

```bash
pip install 'attune-ai[developer]'
```

| Capability | Plugin only | + pip |
| ---------- | ----------- | ----- |
| 17 auto-triggering skills | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| 41 MCP tools | -- | Yes |
| `attune` CLI | -- | Yes |
| Multi-agent workflows | -- | Yes |
| Cost tracking | -- | Yes |

## Links

- [GitHub](https://github.com/Smart-AI-Memory/attune-ai)
- [PyPI](https://pypi.org/project/attune-ai/)
- [Documentation](https://smartaimemory.com/docs)
