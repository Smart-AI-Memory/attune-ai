---
description: Attune AI — Technical Brief: **For:** Technical due diligence, engineering leadership, architecture review --- ## Architecture Overview ┌───────────────
---

# Attune AI — Technical Brief

**For:** Technical due diligence, engineering leadership, architecture review

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Attune AI                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  CLI/API    │  │  VSCode     │  │  MCP Server             │  │
│  │  Interface  │  │  Extension  │  │  (Model Context Proto)  │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                 │
│         └────────────────┼─────────────────────┘                 │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Orchestration Layer                      │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │ SmartRouter │  │ MetaOrchest- │  │ SocraticWorkflow │  │  │
│  │  │ (Model Sel) │  │ rator (v4.4) │  │ Builder          │  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │                 Core Components                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │  │
│  │  │ BaseWizard  │  │ Pattern     │  │ Trajectory      │    │  │
│  │  │ (10 impls)  │  │ Library     │  │ Analyzer        │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │                  Memory System                             │  │
│  │  ┌─────────────────┐      ┌─────────────────────────┐     │  │
│  │  │ Redis (Short)   │      │ MemDocs (Long-Term)     │     │  │
│  │  │ Agent coord,    │      │ Patterns, decisions,    │     │  │
│  │  │ session state   │      │ semantic search         │     │  │
│  │  └─────────────────┘      └─────────────────────────┘     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │                 LLM Providers                              │  │
│  │  ┌──────────────────────────────────────────────────────┐   │  │
│  │  │  Anthropic Claude (Haiku · Sonnet · Opus)          │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. SmartRouter (Intelligent Model Selection)

Routes requests to the optimal model based on task complexity:

| Task Type | Model | Cost/1M tokens |
|-----------|-------|----------------|
| Simple queries, formatting | Haiku | $0.25 |
| Code generation, analysis | Sonnet | $3.00 |
| Architecture, complex reasoning | Opus | $15.00 |

**Result:** 34-86% cost reduction vs. always using premium models.

```python
from attune.routing import SmartRouter

router = SmartRouter()
result = router.route(
    task="Fix this null pointer exception",
    context={"file": "auth.py", "error_type": "NullPointer"}
)
# Automatically selects Sonnet for code fix
```

### 2. SocraticWorkflowBuilder

Creates optimized agent configurations through guided questions:

```python
from attune.socratic import SocraticWorkflowBuilder

builder = SocraticWorkflowBuilder()
session = builder.start_session("Automate security reviews")

# Framework asks clarifying questions
form = builder.get_next_questions(session)
# "What languages?" "What compliance requirements?"

session = builder.submit_answers(session, answers)

# Generates optimized multi-agent workflow
workflow = builder.generate_workflow(session)
```

### 3. Composition Strategy Library

Reusable `ExecutionStrategy` classes covering 10 composition patterns
for combining agents:

| Pattern | Use Case |
|---------|----------|
| Sequential | Step-by-step pipelines |
| Parallel | Independent concurrent tasks |
| Debate | Multiple perspectives on complex decisions |
| Teaching | Expert guides junior agent |
| Refinement | Iterative improvement loops |
| Adaptive | Dynamic strategy based on results |
| Conditional | Branch on intermediate results |
| Tool-Enhanced | Agents augmented with tool access |
| Prompt-Cached Sequential | Sequential with shared cached context |
| Delegation Chain | Orchestrator delegates down a chain |

### 4. Memory System (Dual-Tier)

**Short-Term (Redis):**
- Agent coordination during workflows
- Session state management
- Real-time inter-agent communication
- TTL-based automatic cleanup

**Long-Term (MemDocs):**
- Coding patterns learned from your codebase
- Past decisions and their outcomes
- Project context across sessions
- Semantic search for relevant history

```python
from attune.memory import UnifiedMemory

memory = UnifiedMemory()

# Store pattern
memory.store(
    key="auth_pattern",
    value={"approach": "JWT", "reason": "Team preference"},
    ttl=None  # Long-term storage
)

# Recall with semantic search
relevant = memory.search("authentication approach")
```

### 5. WizardRegistry (5 Interactive Wizards)

Wizards provide guided, multi-step interactive UX. Non-interactive
analysis (code review, bug prediction, docs, performance, dependency
health, research) ships as the 17 workflows.

| Wizard | Purpose |
|--------|---------|
| Security Audit Wizard | Guided OWASP scanning, vulnerability detection |
| Test Generation Wizard | Guided parametrized test generation |
| Refactoring Wizard | Guided safe refactoring |
| Release Preparation Wizard | Guided release readiness workflow |
| Debugging Wizard | Guided failure diagnosis |

---

## Security Architecture

### Built-in Protections

| Feature | Implementation |
|---------|----------------|
| PII Scrubbing | Automatic detection and redaction before LLM calls |
| Secrets Detection | Pre-commit hooks, runtime scanning |
| Path Validation | All file operations validated against traversal attacks |
| Audit Logging | All LLM interactions logged locally |
| Input Sanitization | No eval/exec, parameterized operations only |

---

## Integration Points

### Claude Code

Native integration ships as a Claude Code plugin. Installing the
plugin registers the skills and starts the MCP server:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

### MCP Server

The plugin launches a Model Context Protocol server
(`attune.mcp.server`) that exposes the workflows, memory, and help
tools to any MCP-compatible client:

```python
from attune.mcp.server import AttuneMCPServer

server = AttuneMCPServer()  # exposes 41 MCP tools
```

### Ops Dashboard (web)

- Real-time run monitoring and health score
- Cost tracking and telemetry analytics
- One-click workflow execution
- Living-docs and template browser

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Model routing decision | <10ms | Local classification |
| Wizard initialization | <100ms | Lazy loading |
| Memory recall (Redis) | <5ms | In-memory |
| Memory search (MemDocs) | <50ms | Semantic indexing |
| Full security scan | 2-10s | Depends on codebase size |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| Async | asyncio, aiohttp |
| Memory | Redis, SQLite (MemDocs) |
| LLM SDKs | anthropic |
| Testing | pytest, 21,000+ tests |
| CLI | Click |
| Packaging | Poetry, PyPI |

---

## Deployment Options

### 1. PyPI Installation
```bash
pip install attune-ai
```

### 2. Docker
```dockerfile
FROM python:3.11-slim
RUN pip install attune-ai
```

### 3. On-Premises
Full source available under Apache License 2.0 for enterprise deployment.

---

## API Examples

### Run a Workflow
```python
import asyncio

from attune.workflows import SecurityAuditWorkflow

result = asyncio.run(
    SecurityAuditWorkflow().execute({"path": "./src"})
)
print(result)
```

### Create Custom Agent
```python
from attune.socratic import SocraticWorkflowBuilder

builder = SocraticWorkflowBuilder()
session = builder.start_session("I need an agent for code reviews")
# ... answer questions ...
workflow = builder.generate_workflow(session)
workflow.execute({"files": ["main.py"]})
```

### Cost Tracking
```python
from attune.telemetry import CostTracker

tracker = CostTracker()
print(tracker.summary())
# Total: $12.50 | Saved: $89.30 (87% reduction)
```

---

## Source Code

**Repository:** [github.com/Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)

**License:** Apache License 2.0
- Free and open source for any use, including commercial
- No team-size, seat, or revenue restrictions
- Full source access to use, modify, and redistribute

---

## Contact

For technical questions or architecture deep-dive:

**Patrick Roebuck, Founder**
[smartaimemory.com/contact](https://smartaimemory.com/contact)
