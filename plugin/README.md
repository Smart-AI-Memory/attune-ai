# attune-ai

Developer workflow tools for Claude Code. 11
auto-triggering skills for security audits, code
reviews, test generation, bug prediction, and release
preparation. Say what you need — Claude picks the right
skill.

**Version:** 5.3.2 | **License:** Apache 2.0

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

### Natural language (recommended)

Just describe what you need in Claude Code:

- "review my code" — triggers `code-quality`
- "scan for security issues" — triggers `security-audit`
- "generate tests for src/" — triggers `smart-test`
- "fix failing tests" — triggers `fix-test`
- "predict bugs" — triggers `bug-predict`
- "generate docs" — triggers `doc-gen`
- "plan this feature" — triggers `planning`
- "refactor this module" — triggers `refactor-plan`
- "prepare a release" — triggers `release-prep`

### Commands

| Command | What It Does |
| ------- | ------------ |
| `/attune` | Guided discovery hub — asks what you need |
| `/spec` | Spec-driven dev: brainstorm, plan, execute |

## Skills

| Skill | Triggers On |
| ----- | ----------- |
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
for CLI automation, 31 MCP tools, multi-agent
workflows, and cost tracking:

```bash
pip install 'attune-ai[developer]'
```

| Capability | Plugin only | + pip |
| ---------- | ----------- | ----- |
| 11 auto-triggering skills | Yes | Yes |
| Prompt-based analysis | Yes | Yes |
| 31 MCP tools | -- | Yes |
| `attune` CLI | -- | Yes |
| Multi-agent workflows | -- | Yes |
| Cost tracking | -- | Yes |

## Links

- [GitHub](https://github.com/Smart-AI-Memory/attune-ai)
- [PyPI](https://pypi.org/project/attune-ai/)
- [Documentation](https://smartaimemory.com/docs)
