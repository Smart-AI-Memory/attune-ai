---
name: skill-workflow-orchestration
source: plugin/skills/workflow-orchestration/SKILL.md
summary: This template documents the `/workflow-orchestration` command, which allows
  developers to execute seven different structured analysis workflows (security, code
  review, testing, performance, bug detection, documentation, and release validation)
  directly within Claude Code conversations.
tags:
- skill
- claude-code
type: quickstart
---

# Quickstart: /workflow-orchestration

Run structured analysis workflows directly in your Claude Code conversation — covering security, code review, testing, performance, bugs, documentation, and releases.

## Usage

```
/workflow-orchestration <workflow>
```

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `security` | Scan for vulnerabilities and security issues |
| `review` | Perform a structured code review |
| `tests` | Analyze test coverage and quality |
| `perf` | Identify performance bottlenecks |
| `bugs` | Detect potential bugs and logic errors |
| `docs` | Audit and improve documentation |
| `release` | Run pre-release checks and validation |

## Example

```
/workflow-orchestration security
```

## Output

Results are returned as structured output within your Claude Code conversation.

## Next Steps

For complete configuration options and advanced usage, see the full reference:

```
attune help-docs ref-skill-workflow-orchestration
```

## Related Topics

*No related topics yet.*
