# attune-ai

Developer workflow tools for Claude Code. Run security
audits, code reviews, test generation, performance
analysis, and release preparation through `/attune` or
let the plugin's skills auto-invoke based on what you
describe.

**Version:** 5.0.2 | **License:** Apache 2.0

## Installation

```bash
pip install attune-ai
```

## Usage

### Via /attune command

Type `/attune` in any Claude Code session for guided
routing:

```text
/attune                    # guided — asks what you need
/attune security           # run a security audit
/attune review             # run a code review
/attune tests              # generate tests
/attune perf               # performance analysis
/attune release            # release preparation
```

### Via skill auto-invocation

The plugin's skills trigger automatically based on what
you describe. Just ask naturally:

- "scan this code for vulnerabilities" — triggers
  `security-audit`
- "review the quality of src/" — triggers `code-quality`
- "generate tests for this module" — triggers
  `workflow-orchestration`
- "prepare for release" — triggers `release-prep`
- "store this pattern" — triggers `memory-and-context`

Skills are namespaced as `/attune-ai:skill-name` when
invoked directly (e.g., `/attune-ai:security-audit`).

## What It Does

| Workflow | What Happens |
| -------- | ------------ |
| `/attune security` | Scans for eval/exec, path traversal, hardcoded secrets, injection risks |
| `/attune review` | Reviews code for quality, correctness, and security issues |
| `/attune tests` | Generates unit tests with edge cases and security coverage |
| `/attune perf` | Identifies bottlenecks, memory issues, and optimization opportunities |
| `/attune release` | Runs health checks, changelog validation, and dependency audits |
| `/attune bugs` | Predicts likely bugs using pattern analysis and complexity metrics |

## Skills

| Skill | Description |
| ----- | ----------- |
| `security-audit` | Security vulnerability scanning |
| `code-quality` | Code review and bug prediction |
| `planning` | Feature, TDD, refactoring, and architecture planning |
| `refactor-plan` | Refactoring analysis and roadmap |
| `release-prep` | Pre-release health checks (manual invocation only) |
| `memory-and-context` | Persistent memory and empathy modulation (manual invocation only) |
| `workflow-orchestration` | Routes to the right workflow based on intent |

## When to Use

- You want to run multiple analysis passes before a
  release or PR
- You want security and quality checks without leaving
  Claude Code
- You want to generate tests for modules you haven't
  covered yet
- You want cost-optimized workflows that don't burn
  Opus tokens on triage work

## When NOT to Use

- Single-file edits where Claude Code's built-in
  capabilities are sufficient
- Projects not written in Python (workflow analysis
  is Python-focused)
- Environments without `pip` or Python 3.10+

## Troubleshooting

### MCP server not responding

The plugin requires the `attune-ai` Python package.
Verify it's installed:

```bash
pip show attune-ai
```

If missing, install it and restart Claude Code.

### Workflows return empty results

Check that you're pointing at a directory with Python
files. Most workflows analyze `.py` files specifically.

### Authentication errors

Configure your Anthropic API key:

```bash
python -m attune.models.auth_cli setup
```

## Links

- [GitHub](https://github.com/Smart-AI-Memory/attune-ai)
- [PyPI](https://pypi.org/project/attune-ai/)
- [Documentation](https://smartaimemory.com/docs)
