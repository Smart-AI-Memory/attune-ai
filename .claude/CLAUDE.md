# Attune AI Framework v2.7.0

AI-powered developer workflows with cost optimization and multi-agent orchestration.

@./python-standards.md

---

## Quick Start

```bash
python -m attune.models.auth_cli setup    # Configure authentication
python examples/dashboard_demo.py         # Agent dashboard at localhost:8000
```

---

## Command Hubs

Use `/hub-name` to access organized workflows:

| Hub | Key Routes | Description |
| --- | ---------- | ----------- |
| `/attune` | Socratic discovery | Natural language routing to all workflows |
| `/dev` | debug, review, commit, pr, refactor, quality | Developer tools |
| `/testing` | run, coverage, generate, tdd | Test runner and generation |
| `/workflows` | security, bugs, perf, review, list | Automated analysis |
| `/plan` | feature, tdd, refactor, architecture | Planning and strategy |
| `/docs` | generate, readme, changelog, explain | Documentation |
| `/release` | prep, security, health, publish | Release preparation |
| `/agent` | create, list, run, release-prep | Agent management |

---

## Critical Rules

- NEVER use eval() or exec()
- ALWAYS validate file paths with _validate_file_path()
- NEVER use bare except: - catch specific exceptions
- ALWAYS log exceptions before handling
- Type hints and docstrings required on all public APIs
- Minimum 80% test coverage
- Security tests required for file operations

---

## Project Structure

```text
src/attune/
├── agents/            # Agent SDK, state persistence, recovery
│   ├── sdk/           # SDKAgent, SDKAgentTeam, adapters
│   └── state/         # AgentStateStore, AgentRecoveryManager
├── workflows/         # AI-powered workflows with state & multi-agent mixins
├── models/            # Authentication strategy and LLM providers
├── dashboard/         # Agent Coordination Dashboard (6 patterns)
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, pattern learning
├── telemetry/         # Cost tracking and cache monitoring
└── cli_router.py      # Natural language command routing
```

---

**Version:** 2.7.0 | **License:** Apache 2.0 | **Repo:** [attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
