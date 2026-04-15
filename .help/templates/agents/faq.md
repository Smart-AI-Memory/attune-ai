---
type: faq
feature: agents
depth: faq
generated_at: 2026-04-14T15:09:42.319429+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agents FAQ

## What are agents?

Agents are AI-powered components that automate release preparation tasks. The main agents handle test coverage analysis, documentation checks, code quality assessment, and security auditing to determine if your codebase is ready for release.

## When should I use agents?

Use agents when you need to assess release readiness across multiple quality dimensions. The `ReleasePrepTeam` coordinates all agents in parallel and produces a `ReleaseReadinessReport` with pass/fail gates and actionable feedback.

## How do I run a release readiness check?

Create a `ReleasePrepTeam` and call `assess_readiness()`:

```python
from attune.agents import ReleasePrepTeam

team = ReleasePrepTeam()
report = team.assess_readiness("path/to/your/project")
print(report.format_console_output())
```

## What quality gates do agents check?

Agents evaluate test coverage, documentation completeness, code quality (via ruff), type hints, complexity metrics, and security vulnerabilities. You can customize the thresholds when creating a `ReleasePrepTeam`.

## How does tier escalation work?

The `ReleaseAgent` base class uses progressive escalation: CHEAP → CAPABLE → PREMIUM. If a cheaper model can't complete the task confidently, the agent automatically escalates to a more capable (and expensive) model.

## Can I use agents with other AI frameworks?

Yes. The system provides adapters for LangChain, LangGraph, AutoGen, and Haystack. Call `get_langchain_adapter()`, `get_langgraph_adapter()`, `get_autogen_adapter()`, or `get_haystack_adapter()` to integrate with your existing AI workflow.

## How do I debug agent failures?

Run `pytest -k "agents" -v` to check if the core functionality works. For runtime issues, enable debug logging and check the `ReleaseAgentResult.findings` field for detailed error information. Each agent result includes execution time, cost, and confidence metrics.

## Where are the source files?

- `src/attune/agents/**` - Core agent implementations
- `src/attune/agent_factory/**` - Framework adapters and utilities

**Tags:** `agents`, `ai`, `release`
