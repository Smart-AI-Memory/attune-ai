# attune-ai

Developer workflow tools for Claude Code. Run security
audits, code reviews, test generation, performance
analysis, and release preparation through a single
`/attune` command that routes to the right workflow
based on what you describe.

**Version:** 3.0.0 | **License:** Apache 2.0

## Installation

```bash
pip install attune-ai
```

## Usage

Type `/attune` in any Claude Code session. Describe
what you need and the plugin routes you to the right
workflow:

```text
/attune                    # guided — asks what you need
/attune security           # run a security audit
/attune review             # run a code review
/attune tests              # generate tests
/attune perf               # performance analysis
/attune release            # release preparation
```

Each workflow uses tiered model routing — fast tasks
run on Claude Haiku, analysis on Claude Sonnet, and
deep reasoning on Claude Opus — so you spend tokens
where they matter.

## What It Does

| Command | What Happens |
|---------|--------------|
| `/attune security` | Scans for eval/exec, path traversal, hardcoded secrets, injection risks |
| `/attune review` | Reviews code for quality, correctness, and security issues |
| `/attune tests` | Generates unit tests with edge cases and security coverage |
| `/attune perf` | Identifies bottlenecks, memory issues, and optimization opportunities |
| `/attune release` | Runs health checks, changelog validation, and dependency audits |
| `/attune bugs` | Predicts likely bugs using pattern analysis and complexity metrics |

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

### Command not found for /attune

Ensure the plugin is installed in your Claude Code
plugin directory. Run `claude plugin list` to verify.

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
