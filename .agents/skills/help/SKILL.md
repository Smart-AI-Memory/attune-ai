---
name: help
description: Help and navigation
---
# help

Help navigating Attune AI workflows.

## Behavior

When invoked, show the user the available command
hubs and how to access them:

| Hub | What It Does | Try |
| --- | ------------ | --- |
| `/attune` | Socratic discovery — guides you to the right workflow | `/attune` |
| `/dev` | Debug, review, commit, PR, refactor | `/dev` |
| `/testing` | Run tests, coverage, generate tests | `/testing` |
| `/plan` | Plan features, refactoring, architecture | `/plan` |
| `/workflows` | Security audit, bug predict, perf audit | `/workflows` |
| `/docs` | Generate docs, README, changelog | `/docs` |
| `/release` | Release prep, security scan, publish | `/release` |
| `/brainstorm` | Guided brainstorming sessions | `/brainstorm` |
| `/agent` | Create and manage custom agents | `/agent` |
| `/bulk` | Batch API processing (50% cost savings) | `/bulk` |
| `/wizard` | Guided multi-step wizards | `/wizard` |
| `/utilities` | Auth and provider management | `/utilities` |

**Tip:** Not sure where to start? Try `/attune` —
it will ask what you're trying to do and route you
to the right place.

For CLI usage, run:

```bash
uv run attune --help
```
