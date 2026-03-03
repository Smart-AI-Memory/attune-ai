# X/Twitter Posts for Attune AI

Draft posts for promoting attune-ai. Each post targets a different angle.

---

## Post 1: Launch / General Awareness

> We built 27 developer workflows so you don't have to.
>
> Security audits. Perf checks. Test generation. Release readiness. All from one command:
>
> /attune
>
> Free, open source, $0 in Claude Code.
>
> pip install attune-ai
>
> github.com/Smart-AI-Memory/attune-ai

---

## Post 2: Cost Optimization Angle

> Most AI dev tools charge per API call.
>
> Attune AI runs as a Claude Code skill — $0 on your existing subscription.
>
> When you do use the API, 3-tier routing (Haiku/Sonnet/Opus) saves 34-86% by auto-selecting the cheapest model that can handle the task.
>
> pip install attune-ai

---

## Post 3: Perf Audit Case Study (Blog Promo)

> Ran `/attune perf` on our own codebase.
>
> Score: 67/100.
>
> Two triple-nested loops flagged. Fixed with itertools.product() + Redis pipelining.
>
> Ran it again: 100/100.
>
> Full case study: [link to blog post]

---

## Post 4: Comparison / Positioning

> How attune-ai fits in the AI dev tools landscape:
>
> - LangGraph/AutoGen = build agents from scratch
> - Aider/Codex = AI writes your code
> - CodeRabbit = reviews your PRs
> - Attune = 27 ready-to-use workflows + multi-agent teams + cost routing
>
> It's the workflow layer between coding agents and orchestration frameworks.

---

## Post 5: Security Audit Demo

> One command to scan your Python codebase for security issues:
>
> /attune security
>
> Checks for: eval/exec injection, path traversal, hardcoded secrets, XSS, insecure random, dependency vulnerabilities.
>
> Scored output. Specific file:line references. Zero config.
>
> github.com/Smart-AI-Memory/attune-ai

---

## Post 6: Release Readiness

> Shipping a release? Let a 4-agent team check it first:
>
> /attune release
>
> - Security Auditor checks vulnerabilities
> - Test Coverage verifies thresholds
> - Code Quality runs linting
> - Documentation scores your docstrings
>
> All gates must pass. All for $0 in Claude Code.

---

## Post 7: Claude Code Plugin

> New: attune-ai now ships as a Claude Code plugin.
>
> 18 MCP tools. 3 skills. Socratic discovery.
>
> Type /attune and describe what you need in plain English. It routes to the right workflow automatically.
>
> "find security vulnerabilities" -> security-audit
> "prepare for release" -> release-prep
>
> pip install attune-ai

---

## Post 8: For the Thread (Longer Form)

> Thread: Why we built attune-ai and what we learned.
>
> 1/ Developer tools have a gap. Coding agents (Aider, Claude Code) write code. Orchestration frameworks (LangGraph) let you build agent systems. But nobody ships ready-to-use workflows.
>
> 2/ We wanted: type one command, get a security audit with a score. Type another, get a 4-agent release readiness check. No boilerplate, no agent definitions.
>
> 3/ Cost was a huge pain point. Every API call to Opus costs ~$0.45. But most tasks don't need Opus. Our 3-tier routing uses Haiku ($0.005) for simple tasks, Sonnet ($0.08) for analysis, Opus only when needed.
>
> 4/ The real unlock: running as Claude Code skills. Workflows execute through the Task tool using your subscription. Actual cost: $0.
>
> 5/ Today: 27+ workflows, 18 MCP tools, 4 execution strategies, 85% test coverage, Apache 2.0 licensed.
>
> pip install attune-ai
> github.com/Smart-AI-Memory/attune-ai

---

## Hashtags to Consider

- #AI #DevTools #Claude #Anthropic #OpenSource #Python #DeveloperExperience #AIAgents #MCP #ClaudeCode

## Posting Schedule Suggestion

| Day | Post | Why |
| --- | ---- | --- |
| Mon | Post 1 (Launch) | Start the week with awareness |
| Wed | Post 3 (Case study) | Mid-week educational content |
| Fri | Post 2 (Cost) | End of week, budget-conscious angle |
| Next Mon | Post 5 (Security) | Feature-specific hook |
| Next Wed | Post 8 (Thread) | Deep dive for engaged followers |
| Next Fri | Post 6 (Release) | Feature-specific hook |
