# Attune AI: Spec-Driven Development for Claude Code

Attune AI adds structured development workflows to
Claude Code. Type `/spec` and describe what you want
to build — it brainstorms, decomposes the work into
reviewable tasks, then executes task-by-task with
quality gates after each step.

```
/spec add rate limiting to the API
```

The spec lifecycle — brainstorm, plan, review, execute
— ensures you approve the approach before any code is
written. Quality gates run security scans and tests
after each task. High-severity findings block
auto-approval, so you stay in control.

Plans are saved as markdown files in `.claude/plans/`.
Close your session mid-spec and resume later — state
persists in the plan file itself.

18 multi-agent workflows, 36 MCP tools, 13 slash
commands. Open source, Apache 2.0.

```bash
pip install 'attune-ai[developer]' && attune setup
```

[GitHub](https://github.com/Smart-AI-Memory/attune-ai) |
[PyPI](https://pypi.org/project/attune-ai/)
