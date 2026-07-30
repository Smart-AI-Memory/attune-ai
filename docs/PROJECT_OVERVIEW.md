# Attune AI — Project Overview

**License:** Apache 2.0 | **Python:** 3.10+ | **PyPI:** `attune-ai`

> For the current version, see the
> [PyPI page](https://pypi.org/project/attune-ai/) or the
> README badge. This overview is intentionally version-agnostic
> so it stays accurate across releases.

Attune AI is a production-ready AI workflow operating system
for Claude Code. It provides multi-agent workflows for
code review, security, testing, and release — each backed by
specialized Claude subagents with intelligent model routing,
budget controls, and structured output.

**Design philosophy:** "Simpler is better. Three clear lines
beat one clever abstraction."

---

## Installation

```bash
# Recommended — CLI, all workflows, MCP server, RAG, Agent SDK
pip install attune-ai

# Claude API mode + LangChain/LangGraph agent teams
pip install 'attune-ai[developer]'

# Ops dashboard (extras combine, e.g. 'attune-ai[developer,ops]')
# Redis memory needs no extra — the client ships as a core dependency.
pip install 'attune-ai[ops]'

# Development
git clone https://github.com/Smart-AI-Memory/attune-ai.git
cd attune-ai && pip install -e '.[dev]'
```

Zero-config, ready to use. Subscription-first routing with
automatic API fallback when `ANTHROPIC_API_KEY` is set. Run
`python -m attune.models.auth_cli setup` to customize.

---

## Architecture

### Package Structure

```text
src/attune/
├── workflows/         # Multi-agent workflows (BaseWorkflow)
├── agents/            # Agent SDK integration + state persistence
│   ├── release/       # ReleaseAgent, ReleasePrepTeam
│   └── state/         # AgentStateStore, AgentRecoveryManager
├── wizards/           # Interactive guided workflows
├── mcp/               # MCP server (tools for Claude Code)
├── models/            # LLM provider abstraction + auth strategy
├── memory/            # Two-tier memory (Redis + MemDocs)
├── orchestration/     # Dynamic teams, workflow composition
├── plugins/           # BasePlugin + register_mcp_tools() hook
├── agent_factory/     # Built-in agent templates
├── cli_commands/      # CLI subcommands (cost, telemetry, auth)
├── meta_workflows/    # Intent detection + NL routing
├── telemetry/         # FeedbackLoop, UsageTracker, cost reports
├── monitoring/        # Alerts, OpenTelemetry backend
├── security/          # Path validation, secrets scanning
├── cache/             # Hybrid semantic caching
├── config/            # EmpathyConfig, WorkflowConfig
├── project_index/     # Codebase scanning + file analysis
├── socratic/          # Socratic discovery interactions
├── hooks/             # Claude Code stop hooks, session lifecycle
└── cli_router.py      # Natural language command routing

plugin/                # Claude Code plugin
├── commands/          # Slash commands (attune, review, test, security)
├── skills/            # Skill groups (MCP-exposed tasks)
└── agents/            # Agent definitions

attune_redis/          # Redis plugin (bundled — ships with attune-ai)
attune_software/       # Software plugin (bundled)
```

### Key Classes

| Class | Location | Purpose |
| --- | --- | --- |
| BaseWorkflow | `workflows/base.py` | Abstract base for all workflows |
| WorkflowResult | `workflows/data_classes.py` | Execution result (success, stages, cost) |
| ModelTier | `workflows/compat.py` | Enum: CHEAP / CAPABLE / PREMIUM |
| EmpathyMCPServer | `mcp/server.py` | MCP server for Claude Code |
| EmpathyConfig | `config/config.py` | Runtime configuration |
| UnifiedMemory | `memory/__init__.py` | Two-tier memory interface |
| BaseWizard | `wizards/base.py` | Wizard abstract base |
| WizardRegistry | `wizards/registry.py` | Wizard auto-discovery |
| AgentStateStore | `agents/state/store.py` | Agent state persistence |
| RateLimiter | `mcp/rate_limiter.py` | 60 calls/min per tool |

---

## Workflows

Workflows inherit from `BaseWorkflow` and use the Agent SDK
for multi-agent execution. Run `attune workflow list` for the
canonical, always-current set — the table below is
representative.

| Workflow | Agents | Description |
| --- | --- | --- |
| **code-review** | security, quality, perf, architect | 4-perspective code review |
| **security-audit** | vuln-scanner, secret-detector, auth-reviewer, remediation-planner | Find vulnerabilities, secrets, auth issues |
| **bug-predict** | pattern-scanner, risk-correlator, prevention-advisor | Predict bug-prone patterns |
| **discovery-sweep** | pattern scanners | Sweep a codebase for review candidates |
| **perf-audit** | complexity-analyzer, bottleneck-finder, optimization-advisor | Find bottlenecks and O(n²) patterns |
| **test-gen** | function-identifier, test-designer, test-writer | Generate pytest code |
| **test-audit** | coverage-auditor, gap-analyzer, test-planner | Audit test coverage |
| **doc-gen** | outline-planner, content-writer, polish-reviewer | Generate docs from source |
| **doc-audit** | staleness-checker, accuracy-reviewer, gap-finder | Check docs for staleness |
| **doc-orchestrator** | doc planners | Coordinate multi-doc generation/update |
| **rag-code-gen** | retriever, code-writer | RAG-grounded code generation |
| **refactor-plan** | debt-scanner, impact-analyzer, plan-generator | Plan tech debt refactors |
| **dependency-check** | inventory-assessor, update-advisor | Audit dependencies |
| **simplify-code** | complexity-scanner, simplification-designer, safety-reviewer | Reduce over-engineered code |
| **release-prep** | health-checker, security-scanner, changelog-gen, release-assessor | Pre-release readiness |
| **research-synthesis** | source-summarizer, pattern-analyst, synthesis-writer | Multi-source research synthesis |
| **deep-review** | security, quality, test-gap reviewers | Multi-pass analysis |
| **health-check** | test, dep, lint, ci, doc, security checkers | Dynamic team (2-6 agents) |

### Running Workflows

```bash
attune workflow list                         # List all
attune workflow run code-review --path ./src # Run one
attune workflow info security-audit          # Show details
```

---

## Model Routing and Cost Optimization

### Tier System

| Tier | Model | Use Case | Approx Cost |
| --- | --- | --- | --- |
| CHEAP | Haiku | Scanning, classification | ~$0.005/call |
| CAPABLE | Sonnet | Analysis, synthesis | ~$0.08/call |
| PREMIUM | Opus | Architecture, complex reasoning | ~$0.45/call |

Each workflow maps its stages to tiers so that cheap stages
(scanning, linting) use Haiku while expensive stages
(architecture review, security analysis) use Opus.

### Budget Controls

| Depth | Budget | Use Case |
| --- | --- | --- |
| quick | $0.50 | Fast checks, smoke tests |
| standard | $2.00 | Normal analysis (default) |
| deep | $5.00 | Thorough multi-pass review |

Set via `ATTUNE_MAX_BUDGET_USD` environment variable.

### Per-Agent Model Override

Each subagent is matched against a set of role-keyword env vars to
determine which model it runs on. Setting any of the keywords to
a tier name overrides the built-in default for subagents whose
name contains that keyword.

```bash
# Examples
export ATTUNE_AGENT_MODEL_SECURITY=sonnet   # security-reviewer → sonnet
export ATTUNE_AGENT_MODEL_DEFAULT=opus      # any unmatched agent → opus
```

**Available keywords and built-in defaults** (ordered — first match wins):

| Keyword | Default | Matches subagents like |
| --- | --- | --- |
| `security` | opus | security-reviewer, security-scanner |
| `vuln` | opus | vuln-scanner |
| `architect` | opus | architect-reviewer |
| `quality` | sonnet | quality-reviewer |
| `plan` | sonnet | remediation-planner, plan-generator, test-planner |
| `research` | sonnet | research-* |
| `complexity` | haiku | complexity-analyzer, complexity-scanner |
| `lint` | haiku | lint-checker |
| `coverage` | haiku | coverage-analyzer |
| `dep` | haiku | dep-checker, dependency-* |
| `scanner` | haiku | pattern-scanner, debt-scanner |
| `finder` | haiku | bottleneck-finder, gap-finder |
| `detector` | haiku | secret-detector |
| `reviewer` | inherit | auth-reviewer, perf-reviewer, safety-reviewer, test-gap-reviewer, accuracy-reviewer, polish-reviewer |

Ordering matters: `security` and `vuln` are listed before `scanner`
so `security-scanner` and `vuln-scanner` keep their opus default
rather than dropping to haiku via the broader `scanner` keyword.

The `inherit`-default keyword (`reviewer`) exists primarily as an
override hook — without an env var it falls through to the
orchestrator's model or `ATTUNE_AGENT_MODEL_DEFAULT`.

**Cheap mode in one flag.** For a one-off cost-saving run:

```bash
attune workflow run bug-predict --cheap
```

`--cheap` sets `ATTUNE_AGENT_MODEL_DEFAULT=haiku` for that single
invocation. Subagents pinned to opus/sonnet by the keywords above
are unaffected — security-critical work still gets the right
model. Good for `bug-predict`, `refactor-plan`, `test-audit`,
`doc-audit` (pattern-matching subagents); over-aggressive for
`security-audit` or `code-review` where the opus subagents are
load-bearing.

**Subscription users hitting rate limits** on subagent-heavy
workflows (security-audit fans out to 4 subagents, deep-review
to 4-5, all Opus by default) can rebalance with:

```bash
# Lighten security-audit by routing 3 of 4 subagents to Sonnet.
# The orchestrator stays on Opus for cross-finding synthesis.
export ATTUNE_AGENT_MODEL_VULN=sonnet
export ATTUNE_AGENT_MODEL_DETECTOR=sonnet
export ATTUNE_AGENT_MODEL_REVIEWER=sonnet
attune workflow run security-audit
```

Trade-off: small accuracy reduction on pattern-finding work
(Sonnet 4.6 closes most of the gap with Opus 4.7 for vuln /
secret / auth pattern matching) in exchange for substantially
lower rate-limit pressure and (for API-billed users) ~70% lower
per-run cost.

---

## Wizards

Interactive guided workflows using Socratic discovery
(run `attune wizard list` for the current set):

| Wizard | Purpose |
| --- | --- |
| **debug** | Debug an issue step-by-step |
| **test-gen** | Generate tests interactively |
| **refactor** | Plan refactoring safely |
| **security** | Security audit with guided questions |
| **release-prep** | Release readiness walkthrough |

```bash
attune wizard list
attune wizard run debug
```

---

## Claude Code Plugin

### Commands

| Command | Description |
| --- | --- |
| `/attune` | Main hub — Socratic discovery routing |
| `/attune-review` | Code review shortcut |
| `/attune-test` | Testing hub |
| `/attune-security` | Security audit shortcut |

### Skill Groups

| Skill Group | Purpose |
| --- | --- |
| code-quality | Code review, simplification |
| memory-and-context | Memory operations |
| planning | Feature and architecture planning |
| refactor-plan | Refactoring workflows |
| release-prep | Release preparation |
| security-audit | Vulnerability detection |
| workflow-orchestration | Meta-routing, batch processing |

### MCP Server

Tools exposed via Model Context Protocol (stdio
transport). Configured in `.mcp.json`. Rate-limited to 60
calls/min per tool.

---

## CLI Reference

### Command Hubs

| Hub | Key Routes | Description |
| --- | --- | --- |
| `/attune` | Socratic discovery | Natural language routing |
| `/dev` | debug, review, commit, pr | Developer tools |
| `/testing` | run, coverage, generate | Test runner + generation |
| `/workflows` | security, bugs, perf | Automated analysis |
| `/plan` | feature, refactor, architecture | Planning |
| `/docs` | generate, readme, changelog | Documentation |
| `/release` | prep, security, publish | Release preparation |
| `/agent` | create, list, run | Agent management |
| `/bulk` | submit, status, results | Batch API (50% savings) |
| `/wizard` | run, create, list | Multi-step wizards |
| `/brainstorm` | topic, plan | Guided ideation |
| `/pipeline` | full, dev, eval, release | Spec-driven lifecycle |

### Cost Tracking

```bash
attune costs                  # 7-day report
attune costs --days 30        # Custom range
attune costs today            # Today only
attune costs export -o FILE   # Export
```

### Auth Management

```bash
attune auth status            # Subscription status
attune auth setup             # Interactive setup
attune auth reset --confirm   # Clear config
```

---

## Installation Extras

| Extra | Purpose | Key Dependencies |
| --- | --- | --- |
| `[developer]` | Recommended for devs | agents, memory, caching, memdocs |
| `[memory]` | Redis-backed memory | redis>=5.0.0 |
| `[agents]` | LangChain support | langchain, langgraph |
| `[cache]` | Semantic caching (70% savings) | sentence-transformers, torch |
| `[redis]` | Redis plugin | agent-memory-client, redis |
| `[memdocs]` | Long-term memory | memdocs>=1.0.0 |
| `[backend]` | FastAPI REST server | fastapi, uvicorn |
| `[otel]` | OpenTelemetry export | opentelemetry-* |
| `[docs]` | Doc generation | mkdocs, mkdocs-material |
| `[dev]` | Development tools | pytest, black, ruff, bandit |
| `[enterprise]` | Teams/orgs | developer + backend + otel |
| `[all]` | Everything | All optional packages |

---

## Security

### Security Controls

| Feature | Description |
| --- | --- |
| Path validation | `_validate_file_path()` on all file I/O — blocks traversal, null bytes, system dirs |
| Memory ownership | `created_by` field checked on retrieve/delete |
| Workspace isolation | INTERNAL classification enforces project boundaries |
| MCP rate limiter | 60 calls/min per tool |
| Hook import guard | Only `attune.*` modules loadable via hooks |

### Critical Rules

- Never use `eval()` or `exec()`
- Always validate file paths with `_validate_file_path()`
- Never use bare `except:` — catch specific exceptions
- Always log exceptions before handling
- Type hints and docstrings required on all public APIs

---

## Testing

**Comprehensive test suite** | **85%+ coverage** | **pytest + pytest-cov**

```bash
pytest tests/                              # Full suite
pytest --cov=attune --cov-report=html      # With coverage
pytest tests/unit/workflows/               # Specific module
pytest -n auto                             # Parallel (4-8x faster)
```

### Test Organization

| Directory | Purpose |
| --- | --- |
| tests/unit/ | Unit tests |
| tests/integration/ | End-to-end workflow tests |
| `tests/agent_factory/` | Agent template tests |
| tests/memory/ | Memory system tests |

---

## Configuration

### Config Files

| Location | Scope |
| --- | --- |
| `attune.config.yml` (repo root) | Project-level |
| `~/.attune/config.yml` | User-level |
| Environment variables | Override all |

### Key Environment Variables

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Claude API key |
| `ATTUNE_MAX_BUDGET_USD` | Budget cap per workflow |
| `ATTUNE_AGENT_MODEL_DEFAULT` | Default model tier |
| `REDIS_URL` | Redis connection for memory |

---

## Agent Templates

Built-in templates in
`src/attune/orchestration/agent_templates/builtin_templates.py`:

| Template | Role |
| --- | --- |
| test_coverage_analyzer | Test Coverage Expert |
| security_auditor | Security Auditor |
| code_reviewer | Code Reviewer |
| documentation_writer | Documentation Writer |
| performance_optimizer | Performance Optimizer |
| architecture_analyst | Architecture Analyst |
| refactoring_specialist | Refactoring Specialist |
| test_generator | Test Generator |
| test_validator | Test Validator |
| report_generator | Report Generator |
| documentation_analyst | Documentation Analyst |
| synthesizer | Synthesizer |
| code_simplifier | Code Simplifier |
| generic_agent | General Purpose |

---

## Entry Points

Registered in `pyproject.toml`:

```ini
[project.entry-points."attune.workflows"]
code-review = "attune.workflows.code_review:CodeReviewWorkflow"
security-audit = "attune.workflows.security_audit:SecurityAuditWorkflow"
# ... 13 more

[project.entry-points."attune.wizards"]
debug = "attune.wizards.builtin.debug_wizard:DebugWizard"
# ... 4 more

[project.entry-points."attune.plugins"]
software = "attune_software.plugin:SoftwarePlugin"
redis = "attune_redis.plugin:RedisPlugin"

[project.entry-points."attune.memory_backends"]
file = "attune.memory.file_session:FileSessionMemory"
redis = "attune_redis.memory:AMSMemoryBackend"
```

---

## Related Documentation

| Document | Description |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and component interactions |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | Code style, security rules, testing |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Contributing guidelines |
| [ORCHESTRATION_API.md](ORCHESTRATION_API.md) | Workflow composition API |
| [SECURITY_REVIEW.md](SECURITY_REVIEW.md) | Security analysis |
| [REDIS_SETUP.md](REDIS_SETUP.md) | Redis configuration |
| [SKILLS_REFERENCE.md](SKILLS_REFERENCE.md) | Pointer to the live skills registry (`/catalog`, `plugin/skills/`) |
| [CHANGELOG.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CHANGELOG.md) | Version history |
| [SECURITY.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/SECURITY.md) | Vulnerability reporting |

---

**Repository:** https://github.com/Smart-AI-Memory/attune-ai
| **PyPI:** https://pypi.org/project/attune-ai/
| **Docs:** https://smartaimemory.com/framework-docs/
