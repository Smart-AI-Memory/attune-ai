---
title: "Build a Custom AI Agent in 5 Minutes with Claude Code"
date: "2026-03-07"
author: "Patrick Roebuck"
excerpt: "Step-by-step tutorial: install Attune AI, create a custom agent using the Socratic Agent Builder, and run your first multi-agent workflow — all in under 5 minutes."
tags: ["tutorial", "Claude Code", "AI agents", "getting started", "Attune AI"]
published: true
---

# Build a Custom AI Agent in 5 Minutes with Claude Code

If you've ever wanted to build a production-ready AI agent without wrestling with boilerplate code, prompt engineering, and multi-agent orchestration — this tutorial is for you. Attune AI is designed for developers like Patrick who spend most of their time in code and want to get things done fast.

In this tutorial, you'll:
- Install Attune AI in seconds
- Create a custom agent using natural language guidance
- Run your first multi-agent workflow
- Understand cost optimization and tier-based routing

Let's get started.

## Why Attune AI?

Before we dive in, here's why Attune AI stands out:

**Zero Configuration** — Installs ready to use. No API key wrestling. No config files to setup.

**Cost-Optimized by Default** — Most tasks run on Haiku (cheap tier). Complex reasoning automatically escalates to Opus 4.6 (premium) only when needed.

**14 Pre-Built Agent Templates** — Test Coverage Analyzer, Security Auditor, Code Quality Reviewer, Documentation Writer, Performance Optimizer, Architecture Analyst, Refactoring Specialist, Test Generator, Test Validator, Report Generator, Documentation Analyst, Information Synthesizer, Code Simplifier, and General Purpose agents. Use them as-is or customize.

**Socratic Interaction** — The CLI asks you questions to guide discovery. No guessing what commands to run. No reading 50-page docs to get started.

---

## Step 1: Install Attune AI (30 seconds)

Open your terminal and run:

```bash
pip install attune-ai
```

That's it. Attune AI comes with zero-config defaults. It detects your environment and automatically uses Claude's Anthropic API subscription (if configured) with intelligent fallback to API keys for large modules.

Verify the installation:

```bash
attune --version
```

You should see: `Attune AI v3.9.0`

---

## Step 2: Verify Your Setup (30 seconds)

Run the status command to check your configuration:

```bash
attune auth-status
```

This shows:
- Which provider is active (Subscription or API)
- Available models and their tier costs
- Which LLM tiers are available

If you need to customize authentication, run:

```bash
attune auth-setup
```

But in most cases, the defaults just work.

---

## Step 3: Create Your First Custom Agent with Socratic Builder (2 minutes)

This is where Attune AI shines. Instead of writing YAML configs or wrestling with prompt engineering, you describe what you want in natural language.

Run:

```bash
attune agent create
```

The CLI will guide you through questions:

```
What do you want this agent to do?
> I need an agent that reviews Python code for security issues and suggests fixes
```

The Socratic Agent Builder will ask follow-up questions:

```
What specific security issues matter most?
- SQL injection
- Hard-coded secrets
- Path traversal
- Insecure deserialization
- All of the above? [y/n] y

Should this agent run in isolation or coordinate with other agents?
> It should work with a Code Quality Reviewer to ensure fixes don't break anything

What output format do you prefer?
- JSON report
- Markdown with line-by-line feedback
- Interactive CLI walkthrough
> Markdown with line-by-line feedback
```

Based on your answers, Attune AI generates a production-ready agent configuration:

```yaml
name: security-reviewer
description: |
  Reviews Python code for security vulnerabilities (SQL injection, secrets,
  path traversal, insecure deserialization). Coordinates with Code Quality
  Reviewer to validate fixes don't introduce regressions.
tier: CAPABLE  # Escalates to premium for complex analysis
output_format: markdown
dependencies:
  - code-quality-reviewer
  - test-generator
```

Your custom agent is now registered and ready to use.

---

## Step 4: Run Your First Workflow (1 minute)

Now let's put your agent to work. Attune AI comes with pre-built workflows that compose multiple agents. Try the security audit workflow:

```bash
attune workflow run security-audit --input '{"path": "./src"}'
```

This runs a complete workflow:
1. Your Security Reviewer agent scans the code
2. The Code Quality Reviewer validates proposed fixes
3. The Test Generator creates tests for risky code paths
4. Results are aggregated into a Markdown report

The output looks like:

```
✅ Security Audit Complete

📊 Summary
- Files scanned: 42
- Issues found: 8 (3 High, 4 Medium, 1 Low)
- Fixes suggested: 8
- Tests generated: 23

🔴 High Severity
[models/auth.py:45] Hard-coded API key in environment check
  Fix: Use getenv() with .env file
  Tests generated: 3

[utils/db.py:123] SQL query concatenation (SQL injection risk)
  Fix: Use parameterized queries
  Tests generated: 5

[config.py:78] Path traversal vulnerability in file upload handler
  Fix: Validate paths with security.path_validation module
  Tests generated: 4

...
```

The key insight: multiple agents worked together automatically. You didn't orchestrate them. Attune AI handled the composition, data flow, and result aggregation.

---

## Step 5: Try a Guided Workflow with Wizards (1 minute)

Workflows are for batch automation. When you need interactive, step-by-step guidance, use wizards:

```bash
attune wizard run debug
```

The Debug Wizard walks you through:
1. Selecting files to analyze
2. Describing the bug you're investigating
3. Asking Socratic questions to narrow scope
4. Generating hypotheses
5. Running targeted tests
6. Proposing fixes

This is perfect when you're investigating a live issue and need Claude's reasoning alongside your domain expertise.

---

## Step 6: Compose Agents — Sequential and Parallel Patterns (1 minute)

One of the most powerful features of Attune AI is composition. You can combine agents in specific patterns:

**Sequential Composition** — Run agents one after another, each using the previous agent's output:

```bash
attune workflow run --agents "analyzer → refactor → test-gen → validator"
```

Pipeline:
1. Code Analyzer identifies issues
2. Refactoring Specialist proposes improvements
3. Test Generator creates tests for changes
4. Test Validator ensures tests pass

**Parallel Composition** — Run independent analyses simultaneously:

```bash
attune workflow run security-audit --parallel \
  --agents "security-reviewer, quality-reviewer, performance-optimizer"
```

All three agents analyze your code in parallel. Results merge into a single report. This is 3x faster than sequential and costs the same.

**Conditional Composition** — Route to different agents based on code properties:

```bash
attune workflow run smart-review --input '{"path": "./src"}'
```

Smart routing:
- If code is security-critical → run Security Auditor (premium tier)
- If code is performance-sensitive → run Performance Optimizer
- If code is legacy/untested → run Test Generator first
- Otherwise → use Code Quality Reviewer (cheap tier)

This is how Attune AI achieves cost optimization. Most code uses Haiku (cheap). High-risk code automatically escalates to Opus 4.6 (premium) without manual intervention.

---

## Understanding Cost Optimization & Tier Routing

Here's the magic behind Attune AI's cost efficiency:

**Progressive Tier Escalation** — The CLI detects task complexity and routes to the cheapest capable model:

```python
# Your custom agent automatically does this:
# 1. Try Haiku (cheapest) for standard tasks
# 2. If Haiku returns uncertainty → escalate to Sonnet (mid-tier)
# 3. If Sonnet flags high-risk code → escalate to Opus (premium)

# Result: 80% of tasks use Haiku, 15% use Sonnet, 5% use Opus
# Cost savings: 60-70% vs. always using premium
```

When you created your agent in Step 3, the `tier: CAPABLE` setting enabled this behavior. Attune AI automatically selects the cheapest model capable of the task.

**Monitor Your Costs**:

```bash
attune telemetry export-csv costs.csv
```

This shows per-task costs, tier usage, and optimization opportunities. You can see exactly which tasks are expensive and adjust tier settings if needed.

---

## Your 14 Pre-Built Agent Templates

You don't always need to create custom agents. Attune AI includes 14 production-ready templates:

| Agent | Use Case |
|-------|----------|
| Test Coverage Analyzer | Measure and improve test coverage |
| Security Auditor | Find vulnerabilities and suggest fixes |
| Code Quality Reviewer | Catch bugs, style issues, anti-patterns |
| Documentation Writer | Generate docs from code |
| Performance Optimizer | Identify and fix performance bottlenecks |
| Architecture Analyst | Evaluate system design |
| Refactoring Specialist | Suggest and implement refactors |
| Test Generator | Create parametrized test suites |
| Test Validator | Verify test quality and coverage |
| Report Generator | Aggregate findings into reports |
| Documentation Analyst | Audit and improve documentation |
| Information Synthesizer | Extract insights from code |
| Code Simplifier | Reduce complexity, flatten nesting |
| General Purpose | Custom analysis you define |

Use any of these directly:

```bash
attune agent run test-coverage-analyzer --input '{"path": "./src"}'
```

Or combine them in workflows:

```bash
attune workflow run --agents "test-gen → test-validator → quality-reviewer"
```

---

## What's Happening Behind the Scenes?

When you ran those commands, here's what Attune AI did:

**Step 1-2: Installation & Setup**
- Detected your environment (Python version, project structure)
- Configured API authentication (subscription or API key)
- Cached agent templates and workflow definitions

**Step 3: Agent Creation**
- Used the Socratic prompt to understand your needs
- Generated a custom agent configuration
- Registered it in the local agent registry
- Validated the config (type checking, dependency resolution)

**Step 4: Workflow Execution**
- Parsed the workflow definition (security-audit)
- Instantiated agents (Security Reviewer, Code Quality Reviewer, Test Generator)
- Managed data flow between agents (output of one feeds input of next)
- Handled tier escalation (routing to appropriate LLM)
- Aggregated results into Markdown

**Step 5: Wizard Execution**
- Loaded the Debug Wizard definition
- Presented interactive prompts
- Captured your responses
- Built a dynamic execution plan based on your answers
- Ran analyses with Claude, displaying results in real-time

**Step 6: Composition**
- Parsed agent composition syntax (sequential, parallel, conditional)
- Built a DAG (directed acyclic graph) of agent tasks
- Scheduled execution (parallel where possible)
- Merged results from multiple agents

---

## Next Steps: Level Up Your Agents

Now that you've built and run your first agent, here's where to go next:

**Customize Agent Behavior** — [Agents Configuration Guide](/workflows/)
Learn how to tweak tier settings, adjust output formats, and add custom validation.

**Build Multi-Agent Workflows** — [Workflow Tutorial](/workflows/)
Compose agents into production pipelines. Learn about sequential, parallel, and conditional composition patterns.

**Use the Full CLI** — [Claude Code Getting Started](/framework-docs/getting-started/)
Discover all 50+ CLI commands. The tutorial covered basics — there's much more power available.

**Monitor Costs in Production** — [Cost & Profiling Guide](/workflows/)
Track real-world usage. See which agents are expensive. Optimize tier settings based on data.

**Deploy to Production** — [Deployment Guide](/framework-docs/getting-started/)
Integrate Attune AI into CI/CD pipelines. Run workflows on every PR. Automate code reviews, testing, documentation.

---

## Summary

In 5 minutes, you:

✅ Installed Attune AI v3.9.0 (30 seconds)
✅ Verified your setup (30 seconds)
✅ Created a custom Security Reviewer agent (2 minutes)
✅ Ran your first multi-agent workflow (1 minute)
✅ Explored interactive wizards and composition patterns (1 minute)

You experienced:
- **Zero-config installation** — Just `pip install`
- **Socratic guidance** — The CLI asked questions, not you reading docs
- **Multi-agent composition** — Agents worked together automatically
- **Cost optimization** — Most tasks used cheap models, escalated intelligently
- **Production-ready output** — Markdown reports, line-by-line feedback

The best part? You barely scratched the surface. Attune AI's 14 pre-built agents, 50+ workflows, and powerful composition patterns are all available. Use them as templates or combine them in ways that match your workflow.

Go build something amazing.

---

**Have questions?** Open an issue on [GitHub](https://github.com/Smart-AI-Memory/attune-ai/issues) or ask in [GitHub Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions).

**Want to contribute?** Check out the [Contributing Guide](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CONTRIBUTING.md).
