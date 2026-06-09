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

### 3. MetaOrchestrator

Automatically composes agent teams using 6 composition patterns:

| Pattern | Use Case |
|---------|----------|
| Sequential | Step-by-step pipelines |
| Parallel | Independent concurrent tasks |
| Debate | Multiple perspectives on complex decisions |
| Teaching | Expert guides junior agent |
| Refinement | Iterative improvement loops |
| Adaptive | Dynamic strategy based on results |

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

### 5. WizardRegistry (10 Smart Wizards)

| Wizard | Purpose |
|--------|---------|
| SecurityWizard | OWASP scanning, vulnerability detection |
| TestGenWizard | Parametrized test generation |
| CodeReviewWizard | Style, complexity, best practices |
| BugPredictWizard | Pattern-based bug prediction |
| RefactorWizard | Safe refactoring suggestions |
| DocGenWizard | Documentation generation |
| PerfWizard | Performance analysis |
| DepsWizard | Dependency health checks |
| ResearchWizard | Technical research assistance |
| ReleaseWizard | Release preparation workflows |

---

## Security Architecture

### Built-in Protections

| Feature | Implementation |
|---------|----------------|
| PII Scrubbing | Automatic detection and redaction before LLM calls |
| Secrets Detection | Pre-commit hooks, runtime scanning |
| Path Validation | All file operations validated against traversal attacks |
| Audit Logging | All LLM interactions logged for compliance |
| Input Sanitization | No eval/exec, parameterized operations only |

### Compliance Readiness

- **SOC2:** Audit trails, access controls, encryption
- **HIPAA:** PII handling, data retention policies, BAA-ready
- **GDPR:** Data minimization, right to erasure support

---

## Integration Points

### Claude Code

```python
# Native integration with Claude Code workflows
from attune.claude import ClaudeCodeIntegration

integration = ClaudeCodeIntegration()
integration.register_wizards()  # Adds all 10 wizards
integration.enable_memory()     # Persistent context
```

### MCP Server

```python
# Model Context Protocol server for IDE integration
from attune.mcp import EmpathyMCPServer

server = EmpathyMCPServer()
server.expose_tools([
    "security_scan",
    "generate_tests",
    "predict_bugs",
    "analyze_performance"
])
```

### VSCode Extension

- Real-time health score dashboard
- Cost tracking and analytics
- One-click workflow execution
- Memory visualization

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
| Language | Python 3.8+ |
| Async | asyncio, aiohttp |
| Memory | Redis, SQLite (MemDocs) |
| LLM SDKs | anthropic |
| Testing | pytest, 125+ tests |
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
from attune import EmpathyOS

empathy = EmpathyOS()
result = empathy.workflow.run(
    "security-scan",
    input={"path": "./src"}
)
print(result.findings)
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

**License:** Apache License 2.0 0.9
- Free for teams ≤5 employees
- Commercial license required for 6+
- Full source access for modification

---

## Contact

For technical questions or architecture deep-dive:

**Patrick Roebuck, Founder**
[smartaimemory.com/contact](https://smartaimemory.com/contact)
