---
description: Choose your learning path for Attune AI. Quick Start, Tutorial, or Deep Dive approaches based on your experience level.
---

# Getting Started

Welcome to Attune AI! This guide will take you from zero to running your first AI workflow in about 10 minutes.

---

## Your Journey

```
Installation (2 min) → First Steps (5 min) → Choose Your Path (3 min)
```

| Step | What You'll Do | Time |
|------|----------------|------|
| 1. [Installation](installation.md) | Install the framework and set up an API key | 2 min |
| 2. [First Steps](first-steps.md) | Run your first AI workflow | 5 min |
| 3. [Choose Your Path](choose-your-path.md) | Pick the approach that fits your needs | 3 min |

---

## Quick Install

If you're in a hurry:

```bash
# Install
pip install attune-ai[developer]

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run a workflow
attune workflow run security-audit --path ./src
```

Then come back here to understand what you just did!

---

## What is Attune AI?

Attune AI is a production-ready toolkit for building AI systems that:

- **Automate software tasks** - Security audits, code review, test generation
- **Coordinate multiple AI agents** - Teams of specialized agents working together
- **Optimize costs** - Smart routing between cheap/capable/premium models
- **Remember context** - Short-term and long-term memory for AI agents

### Key Concepts

| Concept | What It Does |
|---------|--------------|
| **Workflows** | Pre-built automations (security audit, release prep, test coverage) |
| **Meta-Orchestration** | Automatic composition of agent teams based on your task |
| **Tiered Models** | Route tasks to cheap/capable/premium models based on complexity |
| **Memory** | Redis-backed short-term memory for agent coordination |

---

## Prerequisites

- **Python 3.10+** (check with `python --version`)
- **pip** (latest version recommended)
- **API key** for at least one LLM provider (Anthropic recommended)

---

## Next Step

Ready? Start with [Installation](installation.md).

---

## Already Installed?

Jump to:

- [First Steps](first-steps.md) - Run your first workflow
- [Choose Your Path](choose-your-path.md) - Find the right approach for you
- [CLI Cheatsheet](../reference/CLI_CHEATSHEET.md) - Quick command reference
