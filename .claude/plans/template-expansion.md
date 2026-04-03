# Template Expansion: 12 New Task Categories

**Created:** 2026-04-02
**Source:** Brainstorm session — gaps beyond 42 skill
templates
**Status:** Planning

## Problem

The 42 skill templates (14 skills x 3 levels) cover
Attune's built-in capabilities but miss common developer
tasks identifiable from code patterns. A developer
adding a dependency, writing error handlers, or
configuring CI gets no help from the current template
set — even though those activities are detectable from
the files they're editing.

## Goals

- Add concept + task + reference templates for 12 new
  task categories (36 templates)
- Each set follows the quality bar established by
  security-audit and code-quality rewrites: enhanced
  tables, Socratic flow callouts, natural language
  prompts, example output
- Templates are code-pattern-triggered — the help
  engine can surface them via precursor warnings when
  the user edits relevant files
- Update summaries.json with one-liners for each new
  category

## The 12 Categories

### Tier 1 — Daily tasks (highest impact)

**1. Dependency Management**

- Trigger patterns: `pyproject.toml`, `requirements.txt`,
  `import` statements for new packages
- Concept: What to check when adding/updating deps
  (compatibility, license, security advisories, pinning)
- Task: How to add, audit, and update dependencies
- Reference: Version constraint syntax, lockfile
  management, `pip-audit`, license checkers

**2. Error Handling Design**

- Trigger patterns: `try/except`, `raise`, custom
  exception class definitions
- Concept: When to catch vs propagate, exception
  hierarchies, logging before handling
- Task: How to design error handling for a module
- Reference: All patterns (specific catch, re-raise,
  chaining with `from`, broad catch justification,
  cleanup/finally), anti-patterns with examples

**3. Configuration Setup**

- Trigger patterns: `.env`, `config.py`, `settings.py`,
  `os.environ`, `pydantic.BaseSettings`
- Concept: Config hierarchy (env vars > config file >
  defaults), secrets management, 12-factor principles
- Task: How to set up configuration for a project
- Reference: Patterns (env vars, YAML/TOML config,
  Pydantic settings), validation, environment-specific
  overrides, secrets handling

**4. Debugging Sessions**

- Trigger patterns: `breakpoint()`, `pdb.set_trace()`,
  `print()` statements, `import pdb`
- Concept: Debugging strategies beyond print statements
  (tracing, logging, binary search, rubber duck)
- Task: How to systematically debug a problem
- Reference: Tools (pdb, debugpy, VSCode debugger,
  logging levels), techniques (bisect, trace, profile)

### Tier 2 — Weekly tasks

**5. API Endpoint Design**

- Trigger patterns: `@app.route`, `@router.get`,
  `FastAPI`, `Flask`, handler functions
- Concept: REST conventions, request validation,
  error responses, versioning
- Task: How to design and implement an API endpoint
- Reference: Status codes, validation patterns,
  pagination, authentication middleware, OpenAPI

**6. Database & Migrations**

- Trigger patterns: `alembic/`, `models.py`,
  `migrations/`, ORM imports (`sqlalchemy`, `django.db`)
- Concept: Schema design, migration safety, data
  integrity
- Task: How to create and run migrations safely
- Reference: Alembic/Django commands, rollback
  patterns, data migrations vs schema migrations,
  zero-downtime strategies

**7. Git Workflow**

- Trigger patterns: `.git/MERGE_HEAD`, conflict markers
  (`<<<<<<<`), `.gitignore` edits
- Concept: Branch strategies, merge vs rebase, conflict
  resolution philosophy
- Task: How to resolve merge conflicts, manage branches
- Reference: Commands for common scenarios, interactive
  rebase, cherry-pick, stash, reflog recovery

**8. Logging & Observability**

- Trigger patterns: `logging.getLogger`, `structlog`,
  `logger.info`, metrics libraries
- Concept: Structured logging, log levels, what to log
  vs what to metric
- Task: How to set up logging for a module
- Reference: stdlib logging config, structlog setup,
  log formatting, correlation IDs, metric patterns

### Tier 3 — Periodic tasks

**9. Authentication Patterns**

- Trigger patterns: `@login_required`, `jwt`,
  `oauth`, session middleware, token handling
- Concept: Auth approaches (session, token, OAuth),
  when to use each, security considerations
- Task: How to add authentication to an endpoint
- Reference: JWT patterns, session management, OAuth
  flows, password hashing, CSRF protection

**10. Package Publishing**

- Trigger patterns: `pyproject.toml` version changes,
  `setup.py`, `MANIFEST.in`, `dist/` directory
- Concept: The publish cycle (version, build, test,
  publish), semantic versioning
- Task: How to publish a Python package to PyPI
- Reference: `pyproject.toml` fields, build tools,
  twine/uv publish, TestPyPI, README rendering,
  classifiers

**11. CI/CD Pipeline**

- Trigger patterns: `.github/workflows/`, `.gitlab-ci`,
  `Dockerfile`, `docker-compose.yml`
- Concept: CI vs CD, pipeline stages, what to
  automate
- Task: How to set up a GitHub Actions CI pipeline
- Reference: Workflow syntax, matrix builds, caching,
  secrets management, status checks, deployment
  triggers

**12. Code Migration**

- Trigger patterns: `pyproject.toml` `requires-python`
  changes, deprecated import warnings, framework
  version bumps
- Concept: Migration strategies (incremental vs big
  bang), compatibility layers, feature flags
- Task: How to plan and execute a code migration
- Reference: Python version migration checklist,
  framework upgrade patterns, deprecation handling,
  codemods

## Approach

### Phase 1: Tier 1 — Dependencies, Error Handling, Config, Debugging

1. Write 12 templates (4 categories x 3 levels)
2. Add summaries to summaries.json
3. Update precursor extension-tag map for trigger
   patterns
4. Test progressive depth on each
5. Review for accuracy against real code patterns

### Phase 2: Tier 2 — API, Database, Git, Logging

1. Write 12 templates (4 categories x 3 levels)
2. Add summaries and trigger patterns
3. Test and review

### Phase 3: Tier 3 — Auth, Publishing, CI/CD, Migration

1. Write 12 templates (4 categories x 3 levels)
2. Add summaries and trigger patterns
3. Test and review

### Phase 4: Precursor wiring

1. Update `_EXTENSION_TAG_MAP` in feedback.py to
   trigger new templates from file patterns
2. Add new tags to cross_links.json tag index
3. Test precursor warnings surface correctly
4. Verify cross-links connect new templates to
   existing skill templates where relevant

## Template Counts After Expansion

| Category | Current | New | Total |
|----------|---------|-----|-------|
| Skill templates | 42 | 0 | 42 |
| Task-category templates | 0 | 36 | 36 |
| Task-category quickstarts | 0 | 12 | 12 |
| Other templates | 515 | 0 | 515 |
| **Total** | **557** | **48** | **605** |

## Precursor Trigger Map (New)

| File pattern | Tags | Templates surfaced |
|-------------|------|--------------------|
| `pyproject.toml`, `requirements.txt` | deps, packaging | dependency-management |
| `try/except`, custom exceptions | error-handling | error-handling-design |
| `.env`, `config.py`, `settings.py` | config | configuration-setup |
| `breakpoint()`, `pdb`, print debug | debugging | debugging-sessions |
| `@app.route`, `@router`, handlers | api | api-endpoint-design |
| `alembic/`, `models.py`, migrations | database | database-migrations |
| `.git/MERGE_HEAD`, conflict markers | git | git-workflow |
| `logging.getLogger`, `structlog` | logging | logging-observability |
| `@login_required`, `jwt`, `oauth` | auth | authentication-patterns |
| version bumps, `dist/`, `MANIFEST.in` | publishing | package-publishing |
| `.github/workflows/`, CI configs | ci | ci-cd-pipeline |
| `requires-python` changes, deprecations | migration | code-migration |

## Decisions

- **Naming convention:** `con-task-*`, `tas-task-*`,
  `ref-task-*` to distinguish from skill templates
  (`con-tool-*`). Clear and practical.
- **Skill cross-links:** Yes — concept templates link
  to relevant Attune skills via natural language prompts
  (e.g., dependency management links to security-audit
  and release-prep).
- **Quickstart templates:** Yes — add a quickstart for
  each category (12 more), bringing the total new
  templates to 48.

## Next Steps

- [ ] Write Tier 1 templates (4 categories x 3 levels)
- [ ] Add summaries to summaries.json
- [ ] Update precursor trigger map
- [ ] Write Tier 2 templates
- [ ] Write Tier 3 templates
- [ ] Wire precursor warnings
- [ ] Cross-link to existing skill templates
