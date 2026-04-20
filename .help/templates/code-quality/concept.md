---
type: concept
feature: code-quality
depth: concept
generated_at: 2026-04-19T18:45:25.513463+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Code Quality

Code quality is a comprehensive analysis that examines your code from multiple perspectives at once — security, quality, performance, and architecture — through a coordinated team of specialized reviewers.

## How the review process works

The `CodeReviewWorkflow` coordinates four specialized subagents that each focus on their domain expertise:

- **Security reviewer** — Scans for vulnerabilities, insecure patterns, and potential attack vectors
- **Quality reviewer** — Catches style violations, likely bugs, and correctness issues
- **Performance reviewer** — Identifies bottlenecks, inefficient patterns, and scalability concerns
- **Architecture reviewer** — Evaluates structure, coupling, complexity, and design patterns

Each subagent analyzes the same codebase independently, then their findings are synthesized into a unified report with an overall health score from 0-100.

## Report structure

When a review completes, you receive a structured markdown report containing:

- **Summary** — Executive overview with the health score and key takeaways
- **Security** — Vulnerabilities and security anti-patterns found
- **Quality** — Style issues, likely bugs, and correctness problems
- **Performance** — Bottlenecks and optimization opportunities
- **Architecture** — Structural issues like high coupling or complexity
- **Suggestions** — Prioritized action items for improvement

## Integration points

The workflow integrates with the broader Attune system through the Agent SDK, allowing it to be triggered from skills, tasks, or direct workflow execution. Results are returned as structured `WorkflowResult` objects that other components can process or display.
