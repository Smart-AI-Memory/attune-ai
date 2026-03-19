---
description: Attune AI - Architecture Overview: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Attune AI - Architecture Overview

**Version:** 3.1.0
**Last Updated:** February 21, 2026
**Status:** Living Document

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Module Dependency Map](#module-dependency-map)
3. [Core Components](#core-components)
4. [Meta-Orchestration System (v4.0)](#meta-orchestration-system-v40)
5. [Claude-Native LLM System](#claude-native-llm-system)
6. [Memory Architecture](#memory-architecture)
7. [Workflow System](#workflow-system)
8. [Agent State & Dynamic Teams (v2.5.0)](#agent-state--dynamic-teams-v250)
9. [Caching Strategy](#caching-strategy)
10. [Security Model](#security-model)
11. [Deployment Architecture](#deployment-architecture)
12. [Performance Characteristics](#performance-characteristics)

---

## System Overview

Attune AI is a meta-orchestration system for AI agent collaboration. The framework enables:

- **Dynamic agent team composition** - Automatically selects and coordinates optimal agents for tasks
- **Agent state persistence** - Execution history, checkpoints, and recovery across sessions
- **Workflow composition** - Compose workflows into multi-agent teams with quality gates
- **Cost optimization** - 34-86% savings through intelligent tier routing
- **Production-ready security** - Path validation, audit logging, HIPAA compliance options

### Design Principles

1. **Meta-orchestration over hard-coding** - Let AI analyze tasks and compose agent teams
2. **Cost-awareness by default** - Route to cheapest model that meets quality requirements
3. **Privacy-first** - Local telemetry, encrypted long-term memory, user data stays local
4. **Fail gracefully** - Degrade functionality rather than crash
5. **Learn from outcomes** - Save successful compositions and improve over time

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
  orchestration/              Dynamic teams, composition
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
   meta_workflows    telemetry      agent_factory
          ↑                               ↑
          │                               │
     cli_router ←── commands ──→ wizards
```

### Key Coupling Metrics (v3.1.0)

| Module | Dependents | Role |
|--------|-----------|------|
| security/path_validation | 63 | Path traversal guard |
| config | 6 | Legacy config (decoupled) |
| models | 14 | Model registry, tiers |
| memory | 23 | Unified storage API |
| meta_workflows | 25 | Orchestration hub |
| workflows | 16 | Workflow engine |

**v3.1.0 change:** `_validate_file_path` extracted from
`config` (59 dependents) into `security/path_validation`
(zero internal deps), eliminating the config bottleneck.

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
│              Meta-Orchestration Engine (v4.0)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Task Analyzer → Agent Selector → Strategy Picker   │   │
│  │       ↓               ↓                  ↓            │   │
│  │  Complexity       Agent Templates    6 Composition   │   │
│  │  Assessment       (13 pre-built)     Patterns        │   │
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

## Meta-Orchestration System (v4.0)

The meta-orchestration system is the framework's breakthrough feature - it analyzes tasks and composes optimal agent teams automatically.

### Architecture

```python
┌────────────────────────────────────────────────────────┐
│              MetaOrchestrator                          │
│                                                        │
│  1. analyze_task(description) → TaskAnalysis          │
│     - Complexity: SIMPLE/MODERATE/COMPLEX             │
│     - Domain: security/testing/docs/etc.              │
│     - Required capabilities                           │
│                                                        │
│  2. select_agents(analysis) → List[AgentTemplate]     │
│     - Match capabilities to requirements              │
│     - Apply quality gates                             │
│     - Consider cost constraints                       │
│                                                        │
│  3. choose_strategy(agents, analysis) → Strategy      │
│     - Sequential: Pipeline processing                 │
│     - Parallel: Independent validation                │
│     - Debate: Consensus building                      │
│     - Teaching: Junior → Expert escalation            │
│     - Refinement: Draft → Review → Polish             │
│     - Adaptive: Classifier → Specialist               │
│                                                        │
│  4. execute(strategy, agents, task) → Result          │
│     - Run composition pattern                         │
│     - Enforce quality gates                           │
│     - Collect outcomes                                │
│                                                        │
│  5. learn(outcome) → Store to ConfigurationStore      │
│     - Save successful compositions                    │
│     - Track success rates                             │
│     - Improve future selections                       │
└────────────────────────────────────────────────────────┘
```

### Pre-Built Agent Templates

The framework includes 13 specialized agent templates:

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

### Composition Patterns

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
├── graph/
│   └── relationships.db  # SQLite graph database
└── keys/
    └── master.key  # AES-256-GCM encryption key
```

**Encryption**: AES-256-GCM with authenticated encryption
**Format**: JSON serialized, then encrypted
**Access**: Only via Memory Graph API (validates permissions)

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

## Agent State & Dynamic Teams (v2.5.0)

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

### Dynamic Team Composition

```text
attune.orchestration/
├── dynamic_team.py           # DynamicTeam - 4 execution strategies
├── team_builder.py           # DynamicTeamBuilder - build from specs/plans/configs
├── team_store.py             # TeamStore - persistent team configurations
├── workflow_agent_adapter.py # Wrap workflows as agents
├── workflow_composer.py      # Compose workflows into teams
└── ...existing modules...
```

**Execution flow:**

```text
MetaOrchestrator.compose_team(task)
  → DynamicTeamBuilder.build_from_plan(plan)
    → DynamicTeam(agents, strategy, quality_gates)
      → team.execute(input_data) → DynamicTeamResult
```

**Strategies:** parallel, sequential, two_phase, delegation

### Workflow Integration Mixins

```text
BaseWorkflow MRO (v2.5.0):
  BaseWorkflow
  ├── ExecutionMixin        # Core execute() loop
  ├── TierMixin             # CHEAP → CAPABLE → PREMIUM escalation
  ├── CoordinationMixin     # Heartbeat & signal coordination
  ├── StatePersistenceMixin # NEW: Stage-level checkpoints
  ├── MultiAgentStageMixin  # NEW: Delegate stages to DynamicTeam
  ├── PromptMixin           # Prompt building
  └── CacheMixin            # Response caching
```

**Opt-in via constructor parameters:**

- `state_store=AgentStateStore(...)` enables state persistence
- `multi_agent_configs={...}` enables multi-agent stage delegation

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

```python
from attune.wizards import HealthcareWizard

wizard = HealthcareWizard()
# Automatic PHI detection and de-identification
# Encrypted storage with 90-day retention
# Comprehensive audit trail (HIPAA §164.312(b))
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

- **[Security Architecture](./architecture/SECURE_MEMORY_ARCHITECTURE.md)** - Memory encryption, audit logging
- **[Plugin System](./architecture/PLUGIN_SYSTEM_README.md)** - Building custom plugins
- **[XML Enhancement](./architecture/xml-enhancement-summary.md)** - Structured prompting

---

**Last Updated:** February 21, 2026
**Maintained By:** Engineering Team
**License:** Apache 2.0
