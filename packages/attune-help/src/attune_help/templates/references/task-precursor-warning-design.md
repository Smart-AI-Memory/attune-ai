---
type: reference
subtype: tabular
name: task-precursor-warning-design
category: task
tags: [precursor, warnings, help-system, patterns]
source: developer-guidance
---

# Precursor Warning Reference

Complete reference for the file-to-tag mapping system,
scoring rules, template prefixes, and tag conventions
used by the precursor warning engine.

## Extension map

Maps file extensions to tags. Defined in
`engine.py:precursor_warnings()`.

| Extension | Tags assigned | Example files |
|-----------|---------------|---------------|
| `.py` | `python`, `imports`, `testing`, `error-handling` | `main.py`, `test_auth.py` |
| `.yml` | `ci`, `github-actions` | `deploy.yml`, `tests.yml` |
| `.yaml` | `ci`, `github-actions` | `config.yaml` |
| `.json` | `packaging` | `package.json`, `tsconfig.json` |
| `.toml` | `packaging`, `python`, `publishing` | `pyproject.toml` |
| `.md` | `claude-code` | `SKILL.md`, `CLAUDE.md` |
| `.sql` | `database`, `migrations` | `001_init.sql` |
| `.env` | `config`, `secrets` | `.env`, `.env.local` |
| `.cfg` | `config` | `setup.cfg`, `mypy.cfg` |
| `.ini` | `config` | `pytest.ini`, `alembic.ini` |

## Filename map

Maps specific filenames (case-insensitive) to tags.
Fires in addition to the extension map.

| Filename | Tags assigned | Why |
|----------|---------------|-----|
| `pyproject.toml` | `deps`, `publishing`, `packaging` | Dependency and build config |
| `requirements.txt` | `deps` | Pinned dependencies |
| `setup.py` | `publishing`, `packaging` | Legacy packaging |
| `setup.cfg` | `publishing`, `packaging` | Legacy packaging metadata |
| `config.py` | `config` | Application configuration |
| `settings.py` | `config` | Application settings |
| `models.py` | `database` | ORM models |
| `alembic.ini` | `database`, `migrations` | Alembic migration config |
| `dockerfile` | `ci`, `cd` | Container build |
| `docker-compose.yml` | `ci`, `cd` | Multi-container setup |
| `.gitignore` | `git` | Git exclusion rules |
| `.env` | `config`, `secrets` | Local environment secrets |
| `.env.example` | `config`, `secrets` | Example env template |
| `manifest.in` | `publishing` | sdist inclusion rules |

## Adding new mappings

To add a new extension or filename trigger:

1. Edit `engine.py:precursor_warnings()`, adding to
   `ext_map` or `name_map`
2. Choose tags that already exist in `cross_links.json`
   when possible
3. If you need a new tag, add it to the template
   frontmatter and regenerate `cross_links.json`

**Tag naming conventions:**

| Convention | Example | Use |
|------------|---------|-----|
| Single word | `python`, `git`, `config` | Broad topic |
| Hyphenated | `error-handling`, `github-actions` | Multi-word topic |
| Noun, not verb | `testing` not `run-tests` | Describes the domain |
| Lowercase | `ci` not `CI` | Consistent casing |

Avoid overly specific tags like `ruff-b904` -- they
match too few templates to be useful. Prefer the broader
`python` or `error-handling`.

## Template prefix requirements

Only templates with these prefixes are eligible for
precursor warning results:

| Prefix | Type | Description | Verbosity |
|--------|------|-------------|-----------|
| `war-` | Warning | Lessons learned, gotcha advisories | Compact |
| `err-` | Error | Error diagnosis and recovery | Compact |
| `con-task-` | Concept | Why this topic matters | Normal |
| `tas-task-` | Task | Step-by-step how-to | Normal |
| `ref-task-` | Reference | Full pattern catalog | Normal |
| `qui-task-` | Quickstart | Minimal 5-step guide | Normal |

Templates without these prefixes (e.g., `con-` concept
templates, `tas-` plain tasks) are not returned by
`precursor_warnings()`. They are still reachable via
`lookup()` and `get()`.

## Scoring and ranking

When multiple templates match, scores determine order.

| Factor | Points | Rationale |
|--------|--------|-----------|
| Each matching tag | +1 | More overlap = more relevant |
| Template ID contains `task-` | +10 | Task-category templates are guidance, not error history |

**Example:** Editing `pyproject.toml` assigns tags
`packaging`, `python`, `publishing` (from extension)
plus `deps`, `publishing`, `packaging` (from filename).

A template with tags `[packaging, publishing, deps]`
scores:

- `packaging`: matched twice in file tags = +2
- `publishing`: matched twice in file tags = +2
- `deps`: matched once in file tags = +1
- Contains `task-` in ID: +10
- **Total: 15**

A `war-` template with tags `[packaging]` scores:

- `packaging`: matched twice = +2
- No `task-` boost
- **Total: 2**

The task-category template surfaces first.

## Lessons Learned to warning pipeline

Many entries in CLAUDE.md's Lessons Learned section are
strong candidates for precursor warnings. The conversion
pattern:

| Lesson pattern | Warning trigger | Tags |
|----------------|-----------------|------|
| "X breaks when editing Y files" | Y file extension or name | Domain tags from the lesson |
| "Always do X before Y" | Y file or action | Process tags |
| "Z is a common mistake with W" | W file type | W domain tags |

**Examples from the codebase:**

| Lesson | Trigger | Template |
|--------|---------|----------|
| "ruff parses pytest.ini as Python" | `pytest.ini` filename | `war-ruff-pytest-ini` |
| "dist/ can contain stale artifacts" | `pyproject.toml` filename | `war-dist-stale-artifacts` |
| "`.env` committed to git" | `.env` extension | `war-env-secrets` |
| "Pre-commit stash conflict" | `.py` extension | `war-pre-commit-stash` |

To convert a lesson to a warning:

1. Identify the file type that triggers the problem
2. Check if that file type already has mapped tags
3. Write a warning template with overlapping tags
4. Test with `precursor_warnings("filename")`

## Testing precursor surfacing

```python
from attune_help import HelpEngine

engine = HelpEngine()

# Test that .env files surface secrets warnings
results = engine.precursor_warnings(".env")
assert len(results) > 0
assert any("secret" in r.lower() for r in results)

# Test that .py files surface Python guidance
results = engine.precursor_warnings("main.py")
assert len(results) > 0

# Test that unknown extensions return nothing
results = engine.precursor_warnings("data.xyz")
assert len(results) == 0
```

## Common tag to template connections

| Tag | Triggers from | Typical templates |
|-----|---------------|-------------------|
| `python` | `.py`, `.toml` | Error handling, imports, testing patterns |
| `config` | `.env`, `.cfg`, `.ini`, `config.py`, `settings.py` | Configuration setup, secrets management |
| `secrets` | `.env`, `.env.example` | Secrets in source control, gitignore |
| `ci` | `.yml`, `.yaml`, `dockerfile`, `docker-compose.yml` | CI/CD pipeline, GitHub Actions |
| `packaging` | `.json`, `.toml`, `pyproject.toml`, `setup.py` | Package publishing, dependency management |
| `database` | `.sql`, `models.py`, `alembic.ini` | Database migrations, ORM patterns |
| `git` | `.gitignore` | Git workflow, gitignore patterns |
| `publishing` | `.toml`, `pyproject.toml`, `setup.py`, `manifest.in` | Package publishing, PyPI |

## Want to learn more?

- Say **"what are precursor warnings?"** for the design
  principles and why proactive beats reactive
- Say **"how do I add a precursor warning?"** for the
  step-by-step guide
- Say **"I need to add a proactive warning"** for a
  5-step quickstart
- Read `engine.py:precursor_warnings()` for the
  implementation source

## Related Topics

- **Concept**: Precursor warning design -- why proactive
  warnings beat reactive errors, and how the trigger
  chain works
- **Task**: Precursor warning design -- step-by-step
  guide for adding a new precursor warning
- **Quickstart**: Precursor warning design -- 5-step
  guide to add a proactive warning
