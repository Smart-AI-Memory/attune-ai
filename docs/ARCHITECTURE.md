---
description: Attune AI - Architecture Overview: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Attune AI - Architecture Overview

**Last Updated:** July 29, 2026
**Status:** Living Document

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Module Dependency Map](#module-dependency-map)
3. [Core Components](#core-components)
4. [Agent Templates & Strategies](#agent-templates-strategies)
5. [Claude-Native LLM System](#claude-native-llm-system)
6. [MCP Server Integration](#mcp-server-integration)
7. [Memory Architecture](#memory-architecture)
8. [Workflow System](#workflow-system)
9. [Agent State & Teams](#agent-state-teams)
10. [Hook System](#hook-system)
11. [Caching Strategy](#caching-strategy)
12. [Security Model](#security-model)
13. [Deployment Architecture](#deployment-architecture)
14. [Performance Characteristics](#performance-characteristics)

---

## System Overview

Attune AI is a workflow-and-agent system for AI-assisted
development. The framework enables:

- **Workflow execution** - SDK-native workflows with quality
  gates and tier routing
- **Agent teams** - Fan-out workflow agents with score-based
  quality gates (`AgentTeam`)
- **Agent state persistence** - Execution history, checkpoints,
  and recovery across sessions
- **Cost optimization** - 34-86% savings through intelligent
  tier routing
- **Production-ready security** - Path validation, audit logging,
  HIPAA compliance options

### Design Principles

1. **Cost-awareness by default** - Route to cheapest model that
   meets quality requirements
2. **Privacy-first** - Local telemetry, encrypted long-term
   memory, user data stays local
3. **Fail gracefully** - Degrade functionality rather than crash
4. **Quality gates** - Enforce score thresholds before passing
   results downstream

---

## Module Dependency Map

The codebase is organized into a 5-tier dependency
hierarchy. Lower tiers never import from higher tiers.

### Tier Structure

```text
Tier 1 — Foundation (no internal deps)
  security/path_validation    Zero deps, CWE-22 protection
  _deprecation                Zero deps, CLI warnings

Tier 2 — Configuration
  config.py                   AttuneConfig, load_config
  config/                     UnifiedConfig, sections, XML
  models/                     MODEL_REGISTRY, auth strategy

Tier 3 — Infrastructure
  memory/                     Unified two-tier (Redis + persistent)
  cache/                      Hash + semantic caching
  telemetry/                  Cost tracking, metrics
  agents/                     SDK, state persistence, recovery

Tier 4 — Domain Logic
  workflows/ (145 files)      13+ workflow implementations
  meta_workflows/             Intent detection, routing
  orchestration/              Agent templates, strategies
  socratic/                   Guided agent generation

Tier 5 — Entry Points
  cli_minimal.py              Primary CLI (attune command)
  cli_router.py               Keyword → skill routing
  commands/                   Markdown command definitions
  wizards/                    Guided multi-step flows
```

### Cross-Module Dependencies

```text
                  security/path_validation
                          ↑
          ┌───────────────┼───────────────┐
          │               │               │
       config          models          memory
          ↑               ↑               ↑
          │               │               │
     workflows ──────→ models        orchestration
          ↑               │               ↑
          │               │               │
   meta_workflows    telemetry         agents
          ↑                               ↑
          │                               │
     cli_router ←── commands ──→ wizards
```

### Codebase Metrics (v11.0.0)

| Metric | Value |
|--------|-------|
| Python files | 731 |
| Lines of code | 189,910 |
| Functions (incl. methods) | 5,154 |
| Classes | 889 |
| Subpackages | 50 |
| Tests | 23,597 collected |

### Key Coupling Metrics (v11.0.0)

Dependents = files under `src/attune/` importing the module.

| Module | Dependents | Role |
|--------|-----------|------|
| security/path_validation | 77 | Path traversal guard |
| config | 26 | Configuration |
| models | 52 | Model registry, tiers |
| memory | 53 | Unified storage API |
| meta_workflows | 31 | Orchestration hub |
| workflows | 59 | Workflow engine |
| mcp | 49 core tools | Claude Code integration |

---

## Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   CLI Tool   │  │  VSCode Ext  │  │  Python API      │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────────┐
│         ▼                  ▼                  ▼              │
│                  Agent & Strategy Layer                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent Templates  →  Execution Strategies  →  Teams  │   │
│  │       ↓                    ↓                   ↓       │   │
│  │  14 pre-built     Sequential/Parallel/    AgentTeam   │   │
│  │  templates        Debate/Refinement/…     (fan-out)   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                             ▼                                │
│                    Workflow Execution Layer                  │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Sequential│  │   Parallel   │  │  Debate/Teaching/    │  │
│  │  Pipeline │  │  Validation  │  │  Refinement/Adaptive │  │
│  └─────┬─────┘  └──────┬───────┘  └──────────┬───────────┘  │
└────────┼────────────────┼──────────────────────┼──────────────┘
         │                │                      │
┌────────┼────────────────┼──────────────────────┼──────────────┐
│        ▼                ▼                      ▼               │
│              Claude-Native LLM Router (Anthropic)            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Tier Selection (CHEAP/CAPABLE/PREMIUM)              │    │
│  │       ↓                                                │    │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐  │    │
│  │  │ Haiku 4.5  │  │ Sonnet 4.6   │  │  Opus 4.6   │  │    │
│  │  │  (CHEAP)   │  │ (CAPABLE)    │  │  (PREMIUM)  │  │    │
│  │  └────────────┘  └──────────────┘  └─────────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
         │                │                      │
┌────────┼────────────────┼──────────────────────┼──────────────┐
│        ▼                ▼                      ▼               │
│                   Support Services                            │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐  │
│  │  Cache   │  │  Memory  │  │Telemetry│  │  Security    │  │
│  │  (Hybrid)│  │  (Redis) │  │ (Local) │  │  (Audit Log) │  │
│  └──────────┘  └──────────┘  └─────────┘  └──────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## Agent Templates & Strategies

The `attune.orchestration` package provides the reusable
building blocks for agent work: pre-built agent templates and
a library of execution strategies. Workflows and agent teams
draw on these directly.

### Pre-Built Agent Templates

The framework includes 14 specialized agent templates,
available via `get_template`, `get_all_templates`,
`get_templates_by_capability`, and `get_templates_by_tier`:

1. **Security Auditor** - Vulnerability scanning, OWASP checks, dependency audits
2. **Test Coverage Analyzer** - Gap analysis, edge case detection, assertion suggestions
3. **Code Quality Reviewer** - Best practices, anti-patterns, refactoring suggestions
4. **Documentation Writer** - Completeness checks, clarity improvements, API docs
5. **Performance Optimizer** - Bottleneck detection, optimization recommendations
6. **Architecture Analyst** - Design patterns, SOLID principles, scalability analysis
7. **Refactoring Specialist** - Code restructuring, extract method, simplification
8. **Dependency Checker** - CVE scanning, license compliance, update recommendations
9. **Bug Predictor** - Predictive analysis, risk scoring, prevention steps
10. **Release Coordinator** - Version management, changelog, release validation
11. **Integration Tester** - API testing, contract verification, compatibility checks
12. **API Designer** - REST/GraphQL design, schema validation, documentation
13. **DevOps Engineer** - CI/CD, infrastructure, deployment automation
14. **Code Simplifier** - Complexity reduction, inline helpers, flatten conditionals

### Execution Strategies

The `attune.orchestration.execution_strategies` module
provides composable strategies, selected via `get_strategy`.
Each describes how a set of agents combine their work.

**Sequential (Pipeline)**
```
Agent A → Agent B → Agent C → Final Result
```
Use when: Each agent depends on previous agent's output

**Parallel (Validation)**
```
      ┌→ Agent A →┐
Task ─┼→ Agent B →┼→ Synthesis → Final Result
      └→ Agent C →┘
```
Use when: Independent validations, aggregate findings

**Debate (Consensus)**
```
Agent A ⟷ Agent B ⟷ Agent C → Synthesis → Final Result
```
Use when: Need consensus, conflicting perspectives valuable

**Teaching (Cost Optimization)**
```
Junior Agent → (if confidence < threshold) → Expert Agent
```
Use when: Optimize costs, most tasks are simple

**Refinement (Iterative)**
```
Draft Agent → Review Agent → Polish Agent → Final Result
```
Use when: Quality > speed, content generation

**Adaptive (Right-Sizing)**
```
Classifier → Route to appropriate specialist
```
Use when: Unknown complexity, need optimal resource allocation

---

## Claude-Native LLM System

### Tier-Based Routing

Attune AI is built exclusively for Anthropic Claude.
The framework routes requests to the most cost-effective
Claude model that meets quality requirements:

| Tier | Model | Cost/Task* | Use Cases |
|------|-------|------------|-----------|
| **CHEAP** | Claude Haiku 4.5 | ~$0.005 | Formatting, simple tasks |
| **CAPABLE** | Claude Sonnet 4.6 | ~$0.08 | Bug fixes, code review |
| **PREMIUM** | Claude Opus 4.6 | ~$0.45 | Architecture, design |

*Typical task: 5,000 input tokens, 1,000 output tokens

### Provider Architecture

```text
┌────────────────────────────────────────────────┐
│           Anthropic Provider                   │
│  ┌──────────────────────────────────────────┐ │
│  │  Auth Strategy                           │ │
│  │  - Subscription (Claude Code, free)      │ │
│  │  - API key (CLI/CI, pay per use)         │ │
│  └──────────────────────────────────────────┘ │
│                     ↓                          │
│  ┌──────────────────────────────────────────┐ │
│  │  Tier Selection                          │ │
│  │  - Task complexity analysis              │ │
│  │  - Cost constraints                      │ │
│  │  - Quality requirements                  │ │
│  └──────────────────────────────────────────┘ │
│                     ↓                          │
│  ┌──────────────────────────────────────────┐ │
│  │  Claude Features                         │ │
│  │  - Prompt caching (90% cost reduction)   │ │
│  │  - Extended thinking                     │ │
│  │  - 200K-1M context window               │ │
│  │  - Advanced tool use                     │ │
│  └──────────────────────────────────────────┘ │
│                     ↓                          │
│  ┌─────────────────────────────────────────┐  │
│  │  Anthropic SDK (messages API)           │  │
│  └─────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### Fallback Strategy

```text
Try CHEAP tier (Haiku)
  ↓ (quality insufficient)
Escalate to CAPABLE (Sonnet)
  ↓ (still insufficient)
Escalate to PREMIUM (Opus)
  ↓ (API error)
Retry with exponential backoff
  ↓ (all retries exhausted)
Raise AllProvidersFailedError
```

---

## MCP Server Integration

Attune exposes 25+ tools to Claude Code via the Model
Context Protocol (MCP).

### Architecture

```text
Claude Code
    │
    ▼
┌──────────────────────────────────────────────┐
│          AttuneMCPServer                     │
│  ┌────────────────────────────────────────┐  │
│  │  WorkflowHandlersMixin                │  │
│  │  - security-audit, code-review        │  │
│  │  - bug-predict, test-gen, perf-audit  │  │
│  │  - doc-gen, refactor-plan             │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  MemoryHandlersMixin                  │  │
│  │  - recall, save, delete patterns      │  │
│  │  - unified memory stash and search    │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  Security Guards                      │  │
│  │  - _validate_file_path() on all I/O   │  │
│  │  - RateLimiter per tool call          │  │
│  │  - Workspace isolation                │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### Data Flow

1. Claude Code sends MCP tool call (e.g., `code-review`)
2. Server validates file path via `_validate_file_path()`
3. Lazy-imports the target workflow class
4. Executes workflow with validated inputs
5. Returns structured `WorkflowResult` to Claude Code

---

## Memory Architecture

The framework uses a two-tier memory system: short-term (Redis) and long-term (encrypted patterns).

### Short-Term Memory (Redis)

```
┌────────────────────────────────────────────────┐
│             Redis Instance                     │
│  Port: 6379 (default)                         │
│  Persistence: RDB snapshots                   │
│                                                │
│  Data Structures:                             │
│  ┌──────────────────────────────────────────┐ │
│  │  Hash: user:{user_id}:context            │ │
│  │    - Recent interactions                 │ │
│  │    - Session state                       │ │
│  │    - Preference cache                    │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  Sorted Set: patterns:by_score           │ │
│  │    - Pattern ID → Usage score            │ │
│  │    - Evict least-used patterns           │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  String: cache:{hash}                    │ │
│  │    - LLM response cache                  │ │
│  │    - TTL: 24 hours                       │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

### Long-Term Memory (Encrypted Patterns)

```
~/.attune/
├── patterns/
│   ├── security/
│   │   ├── sql_injection_20260115.enc
│   │   └── xss_vulnerability_20260112.enc
│   ├── bugs/
│   │   └── null_reference_20260110.enc
│   └── fixes/
│       └── add_null_check_20260110.enc
└── keys/
    └── master.key  # AES-256-GCM encryption key
```

**Encryption**: AES-256-GCM with authenticated encryption
**Format**: JSON serialized, then encrypted
**Access**: Only via the long-term memory API (validates
classification)

---

## Workflow System

### Base Workflow Architecture

```python
class BaseWorkflow:
    """Base class for all workflows."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.tier = config.tier  # CHEAP, CAPABLE, PREMIUM
        self.cache_enabled = config.cache_enabled
        self.quality_gates = config.quality_gates

    async def execute(self, **kwargs) -> WorkflowResult:
        """Execute workflow with quality gates."""
        # 1. Validate inputs
        self._validate_inputs(**kwargs)

        # 2. Check cache (if enabled)
        if self.cache_enabled:
            cached = self._check_cache(**kwargs)
            if cached:
                return cached

        # 3. Execute workflow logic
        result = await self._execute_impl(**kwargs)

        # 4. Apply quality gates
        if not self._meets_quality_gates(result):
            result = await self._refine(result)

        # 5. Cache result
        if self.cache_enabled:
            self._cache_result(**kwargs, result=result)

        return result
```

### Built-In Workflows

1. **Security Audit** - OWASP top 10, CVE scanning, secret detection
2. **Bug Prediction** - Predictive analysis, risk scoring, prevention steps
3. **Code Review** - Best practices, anti-patterns, improvement suggestions
4. **Test Generation** - Parametrized tests, edge cases, assertion suggestions
5. **Documentation Generation** - API docs, README, examples
6. **Release Preparation** - Parallel validation (security + tests + docs + quality)
7. **Test Coverage Boost** - Sequential improvement (analyze → generate → validate)
8. **Dependency Check** - CVE scanning, license compliance, update recommendations
9. **Performance Audit** - Bottleneck detection, optimization suggestions
10. **Refactoring Plan** - Design patterns, SOLID principles, incremental steps

---

## Agent State & Teams

### Agent State Persistence

```text
attune.agents.state/
├── models.py        # AgentExecutionRecord, AgentStateRecord
├── store.py         # AgentStateStore - JSON-based persistent storage
├── recovery.py      # AgentRecoveryManager - interrupted agent recovery
└── __init__.py
```

**Storage:** `.attune/agents/state/{agent_id}.json`

- Execution history (max 100 entries per agent, trims oldest)
- Checkpoints for recovery support
- Accumulated metrics (success rate, cost, timing)
- Uses `_validate_file_path()` with `allowed_dir` for security

### Agent Teams

`AgentTeam` (`attune.agents.team`) runs several workflow agents
in a single fan-out pass, then enforces score-based quality
gates. It is fan-out plus gates only — there is no sequential,
two-phase, or DAG topology and no strategy parameter.

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)
report = asyncio.run(team.run(["src/"]))
print(report.passed, report.blockers, report.warnings, report.cost)
```

**Building blocks:**

- `WorkflowAgent(key, workflow_cls, *, files=None, score_fn=None,
  default_score=None, escalate=False)` — wraps a workflow class
  as a team member.
- `GateSpec(name, agent_key, threshold, critical=True)` — a
  score threshold an agent must meet.
- `team.run(target)` is async; `target` is a path string or a
  list of path strings.
- `TeamReport(passed, gates, results, blockers, warnings, cost)`
  carries the outcome; each `AgentResult(key, score, cost,
  success, details)` records one agent's run.

---

## Hook System

Concrete scripts that Claude Code runs on lifecycle events.

### Hook Events

| Event | Trigger | Use Case |
| ----- | ------- | -------- |
| PreToolUse | Before tool execution | Block dangerous commands |
| PostToolUse | After tool execution | Log results, validate |
| SessionStart | Session begins | Load state, set context |
| SessionEnd | Session ends | Save state, cleanup |
| Stop | Agent stops | Reminder hooks, save |

### Architecture

```text
Claude Code (event fires)
    │  stdin: {"tool_name": ..., "tool_input": ...}
    ▼
attune/hooks/scripts/<hook>.py   (wired via the plugin's hooks.json)
    ├── read + validate stdin JSON  (fail open → exit 0 on bad input)
    ├── PreToolUse:  exit 0 = allow, exit 2 = block
    └── other events: perform side effect, exit 0
```

**Security:** guards fail **open** (exit 0) on malformed input so a
hook defect degrades to a no-op instead of blocking a real tool call.
Each script runs under a `hooks.json` timeout on the critical path.
(The former in-process engine — `HookRegistry` / `HookExecutor` — was
removed in v13.0.0.)

---

## Caching Strategy

The framework uses a hybrid caching approach: hash-only (fast, exact matches) and semantic (similar prompts).

### Hash-Only Cache (Default)

```python
import hashlib

def compute_cache_key(prompt: str, model: str, temperature: float) -> str:
    """Compute deterministic hash for cache lookup."""
    content = f"{prompt}|{model}|{temperature}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Performance**: ~5μs lookup time
**Hit Rate**: 100% on identical prompts (30-40% typical in development)

### Hybrid Cache (Semantic Matching)

```python
from sentence_transformers import SentenceTransformer

class HybridCache:
    def __init__(self, similarity_threshold: float = 0.95):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.threshold = similarity_threshold
        self.hash_cache = {}  # Fast exact matches
        self.semantic_index = {}  # Embeddings for similarity

    def get(self, prompt: str) -> str | None:
        # 1. Try hash cache (exact match)
        hash_key = compute_cache_key(prompt, ...)
        if hash_key in self.hash_cache:
            return self.hash_cache[hash_key]

        # 2. Try semantic similarity
        embedding = self.model.encode(prompt)
        for cached_embedding, cached_response in self.semantic_index.items():
            similarity = cosine_similarity(embedding, cached_embedding)
            if similarity >= self.threshold:
                return cached_response

        return None
```

**Performance**: ~50ms lookup time (embedding generation)
**Hit Rate**: Up to 57% on similar prompts (benchmarked on security audit)

---

## Security Model

### Defense in Depth

1. **Input Validation** - All user inputs validated before processing
2. **Path Validation** - `security/path_validation._validate_file_path()` prevents path traversal (single source, 63 consumers)
3. **Secret Detection** - API keys, credentials, tokens detected and redacted
4. **Audit Logging** - All security-sensitive operations logged
5. **Encryption** - AES-256-GCM for long-term memory
6. **Rate Limiting** - Per-IP sliding window (100 req/min)
7. **HTTPS/TLS** - Optional SSL for API server

### HIPAA Compliance (Optional)

> **Status: Planned** — This wizard is not yet implemented. The section below describes the intended design.

For healthcare deployments:

```text
# PLANNED — not yet implemented; illustrative pseudocode only.
# A future `HealthcareWizard` would provide, for healthcare
# deployments:
#   - Automatic PHI detection and de-identification
#   - Encrypted storage with 90-day retention
#   - Comprehensive audit trail (HIPAA §164.312(b))
```

---

## Deployment Architecture

### Single Developer (Lightweight)

```
┌────────────────────────────────────┐
│  Developer Laptop                  │
│  ┌──────────────────────────────┐  │
│  │  attune-ai[developer]│  │
│  │  - CLI tools                 │  │
│  │  - VSCode extension          │  │
│  │  - Local telemetry           │  │
│  └──────────────────────────────┘  │
│                                    │
│  Optional:                         │
│  ┌──────────────────────────────┐  │
│  │  Redis (local)               │  │
│  │  Port: 6379                  │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

### Team Deployment (Backend + Auth)

```
┌────────────────────────────────────────────────┐
│  Application Server                            │
│  ┌──────────────────────────────────────────┐  │
│  │  Backend API (FastAPI)                   │  │
│  │  - JWT authentication                    │  │
│  │  - Rate limiting                         │  │
│  │  - HTTPS/TLS                             │  │
│  │  Port: 8000                              │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  Redis (shared)                          │  │
│  │  - Session storage                       │  │
│  │  - Cache                                 │  │
│  │  Port: 6379                              │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Client Machines (N developers)     │
│  - attune CLI client                │
│  - API key authentication           │
└─────────────────────────────────────┘
```

### Healthcare/Enterprise (Full Stack)

```
┌────────────────────────────────────────────────┐
│  Load Balancer (HTTPS)                        │
└────────────────┬───────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼────────────┐  ┌─────────▼──────────┐
│  App Server 1  │  │  App Server 2      │
│  - Backend API │  │  - Backend API     │
│  - Redis       │  │  - Redis           │
└────────────────┘  └────────────────────┘
    │                         │
    └────────────┬────────────┘
                 │
┌────────────────▼───────────────────────────────┐
│  Database Layer                                │
│  ┌──────────────┐  ┌─────────────────────────┐│
│  │  PostgreSQL  │  │  Compliance Database    ││
│  │  (metadata)  │  │  (append-only audit)    ││
│  └──────────────┘  └─────────────────────────┘│
└────────────────────────────────────────────────┘
```

---

## Performance Characteristics

### Benchmarks (January 2026)

**Workflow Execution Times:**
- Security Audit (1000 files): 45s → 15s (with cache, 67% faster)
- Test Generation (100 functions): 12s → 8s (multi-tier optimization)
- Code Review (500 LOC): 8s → 3s (CAPABLE → CHEAP tier)

**Cache Performance:**
- Hash-only lookup: ~5μs
- Semantic similarity: ~50ms
- Hit rate (development): 30-57%
- Cost reduction: 40% (test generation workflow)

**Memory Usage:**
- Base framework: ~50MB
- With Redis: ~120MB
- With full caching: ~180MB
- Per-workflow overhead: ~10-20MB

### Scaling Characteristics

| Metric | 1 User | 10 Users | 100 Users |
|--------|--------|----------|-----------|
| API Latency (p50) | 200ms | 250ms | 350ms |
| API Latency (p99) | 800ms | 1200ms | 2500ms |
| Redis Memory | 50MB | 200MB | 1.5GB |
| Monthly Cost (CAPABLE) | $15 | $120 | $1,000 |
| Monthly Cost (Hybrid) | $5 | $40 | $350 |

---

## Related Documentation

- **[Plugin System](./architecture/plugin-system.md)** - Building custom plugins

---

**Last Updated:** March 18, 2026
**Maintained By:** Engineering Team
**License:** Apache 2.0
