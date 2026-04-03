---
type: concept
name: task-code-migration
tags: [migration, python, upgrade, compatibility]
source: developer-guidance
---

# Code Migration

Code migration is the process of moving your codebase from
one version of a language, framework, or library to another.
Unlike feature work, migrations touch every file that depends
on the thing being upgraded. The risk is not in any single
change -- it is in the sheer number of changes and the
interactions between them.

## Migration types

| Migration type | What changes | Scope | Typical risk | Rollback possible? | Example |
|---|---|---|---|---|---|
| **Python version** | Syntax, stdlib, builtins | Entire codebase | Medium-High | Yes (keep old runtime) | 3.9 to 3.12 |
| **Framework major** | APIs, config, middleware, ORM | Framework-dependent code | High | Difficult | Django 4 to 5, Flask 2 to 3 |
| **Library upgrade** | Function signatures, defaults, behavior | Import sites | Low-Medium | Yes (pin old version) | pydantic v1 to v2 |
| **API version** | Endpoints, request/response shapes, auth | Client code | Medium | Yes (version header) | REST v2 to v3 |
| **Architecture** | Module boundaries, data flow, deployment | Full system | Very High | Partial at best | Monolith to services |
| **Build system** | Config files, scripts, CI pipelines | Build layer | Low | Yes (keep old config) | setup.py to pyproject.toml |

The key insight: risk scales with scope. A library upgrade
that touches 3 files is a different problem than a Python
version upgrade that touches 300.

## Incremental vs big-bang migration

Two fundamental strategies exist, and choosing the wrong
one is the most common migration mistake.

| Strategy | How it works | Best for | Worst for |
|---|---|---|---|
| **Incremental** | Migrate one module or feature at a time. Old and new coexist behind compatibility layers or feature flags. Ship each piece independently. | Large codebases, production systems, teams with limited migration experience | Tightly coupled systems where partial migration is impossible |
| **Big-bang** | Migrate everything at once. Switch over in a single deploy or merge. | Small codebases, non-production code, migrations where partial states are invalid | Anything with more than a few hundred files or external consumers |

Incremental migration is almost always safer. The cost is
maintaining compatibility layers during the transition. The
benefit is that you can ship, test, and roll back each piece
independently.

## Compatibility layers

A compatibility layer is code that lets old and new
implementations coexist. It absorbs the differences so that
callers don't need to change until you're ready.

Common patterns:

- **Shim functions** that wrap the new API to match the
  old signature
- **`__future__` imports** that bring new Python behavior
  into old versions
- **`try`/`except ImportError`** blocks that import from
  the new location and fall back to the old one
- **Type aliases** that map old names to new ones

Compatibility layers are temporary. They exist to make the
migration incremental. Once migration is complete, remove
them -- they are tech debt by design.

## Feature flags for migration

Feature flags let you deploy migrated code to production
without activating it for all users. This separates the
deploy from the rollout:

1. Deploy migrated code behind a flag (off by default)
2. Enable for internal users or a percentage of traffic
3. Monitor for errors, performance regressions, or
   behavior changes
4. Gradually increase the rollout
5. Remove the flag and the old code path

This is the safest approach for high-risk migrations where
rollback needs to be instant.

## Risk assessment

Before starting a migration, assess:

| Factor | Low risk | High risk |
|---|---|---|
| **Test coverage** | 80%+ coverage on migrated code | Under 50% or no tests |
| **Dependency count** | Few downstream consumers | Many packages depend on your code |
| **Runtime behavior** | Pure type/syntax changes | Changed defaults, removed features |
| **Rollback plan** | Pin old version and redeploy | No clear rollback path |
| **Timeline pressure** | Weeks of buffer | EOL deadline next week |

If more than two factors are "high risk," consider breaking
the migration into smaller phases or investing in test
coverage before starting.

## What makes migrations fail

Most migration failures share the same root causes:
starting without sufficient test coverage, skipping the
compatibility assessment, trying to migrate everything at
once, or underestimating the time required for edge cases.
The first 80% of a migration goes fast. The last 20% --
deprecation warnings, subtle behavior changes, CI
platform differences -- takes longer than the first 80%.

## Want to learn more?

- Say **"how do I migrate my Python version?"** for a
  step-by-step guide to planning and executing a version
  upgrade
- Say **"show me migration patterns"** for the full
  reference with per-version checklists, codemods, and
  common pitfalls
- Say **"I need to upgrade Python"** for a 5-minute
  quickstart
- Ask **"/code-quality"** to scan migrated code for style
  issues and deprecated patterns
- Ask **"/smart-test"** to find untested code before
  starting a migration
- Ask **"/refactor"** to plan large-scale structural
  changes as part of a migration
