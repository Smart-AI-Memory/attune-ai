---
type: reference
name: task-code-migration
tags: [migration, python, upgrade, compatibility]
source: developer-guidance
---

# Reference: Code migration patterns

Complete reference for Python version migrations, framework
upgrades, codemod tools, deprecation handling, and common
migration problems.

## Python version changes

Key changes per version that affect migrations. Focus on
breaking changes and removed features.

### 3.9 to 3.10

| Change | Impact | Migration action |
|---|---|---|
| `match`/`case` syntax added | New feature, no breaking change | Optional: use structural pattern matching |
| `typing.Union` can use `X \| Y` | Syntax sugar | Optional: replace `Union[X, Y]` with `X \| Y` |
| Parenthesized context managers | Syntax sugar | Optional: use `with (open(a), open(b)):` |
| `distutils` deprecated | Build tools | Switch to `setuptools` or `pyproject.toml` |
| `int.bit_count()` added | New method | Optional: replace `bin(x).count("1")` |

### 3.10 to 3.11

| Change | Impact | Migration action |
|---|---|---|
| `tomllib` added to stdlib | New module | Replace `tomli` with `tomllib` (or keep for <3.11 support) |
| Exception groups and `except*` | New feature | Optional: use for concurrent error handling |
| Fine-grained error locations | Better tracebacks | No action needed |
| `datetime.fromisoformat()` stricter | Behavioral | Test any ISO date parsing code |
| `asyncio.TaskGroup` added | New API | Optional: replace `gather()` for structured concurrency |

### 3.11 to 3.12

| Change | Impact | Migration action |
|---|---|---|
| `datetime.utcnow()` deprecated | **Breaking in spirit** | Replace with `datetime.now(timezone.utc)` everywhere |
| `datetime.utcfromtimestamp()` deprecated | **Breaking in spirit** | Replace with `datetime.fromtimestamp(ts, tz=timezone.utc)` |
| `imp` module removed | **Breaking** | Replace with `importlib` |
| `distutils` removed | **Breaking** | Switch to `setuptools` |
| `typing.TypedDict` supports inheritance | New feature | Optional: simplify TypedDict hierarchies |
| f-string grammar relaxed | Syntax | Optional: use nested f-strings |
| `pathlib.Path.walk()` added | New method | Optional: replace `os.walk()` usage |

### 3.12 to 3.13

| Change | Impact | Migration action |
|---|---|---|
| `cgi` module removed | **Breaking** | Replace with `email.message` or `multipart` |
| `aifc`, `chunk`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib` removed | **Breaking** | Find PyPI replacements |
| `PurePath.match()` supports `**` | Behavioral change | Test glob patterns that use `**` |
| `typing` deprecated aliases scheduled for removal | Future breaking | Replace `typing.List` with `list`, etc. |
| Free-threaded mode (experimental) | New feature | No action unless opting in |

## Codemod tools

Automated tools for mechanical migration changes:

| Tool | What it does | Install | Usage |
|---|---|---|---|
| **pyupgrade** | Rewrites syntax to target Python version | `pip install pyupgrade` | `pyupgrade --py312-plus src/**/*.py` |
| **ruff** (UP rules) | Pyupgrade-compatible rules, much faster | `pip install ruff` | `ruff check --select UP --fix src/` |
| **lib2to3** | Python 2 to 3 conversion (legacy) | Built into CPython | `2to3 -w src/` |
| **com2ann** | Converts type comments to annotations | `pip install com2ann` | `com2ann src/` |
| **isort** / **ruff I** | Fixes import ordering after stdlib changes | `pip install isort` or `ruff` | `ruff check --select I --fix src/` |
| **autoflake** | Removes unused imports (post-migration cleanup) | `pip install autoflake` | `autoflake --in-place --remove-all-unused-imports src/**/*.py` |

### Which tool for which migration

| Migration | Primary tool | Supplementary |
|---|---|---|
| Python version syntax | `pyupgrade` or `ruff --select UP` | `ruff --select I` for imports |
| Type hint modernization | `pyupgrade` with `--py310-plus` | Manual review for complex types |
| Removed module replacement | Manual | `grep` to find usages |
| Framework upgrade | Framework-specific codemods if available | Manual for API changes |

## Deprecation handling

### The warnings module

Python signals deprecations through warnings before
removing features:

```python
import warnings

# Check for deprecation warnings in tests
pytest -W error::DeprecationWarning

# Filter specific warnings you've acknowledged
warnings.filterwarnings(
    "ignore",
    message="datetime.utcnow.*",
    category=DeprecationWarning,
)
```

### `__future__` imports

These bring future Python behavior into the current
version, letting you migrate gradually:

| Import | Effect | Available since |
|---|---|---|
| `from __future__ import annotations` | Defers annotation evaluation (PEP 563) | 3.7+ |
| `from __future__ import generator_stop` | `StopIteration` in generators becomes `RuntimeError` | 3.5+ (default in 3.7) |

`from __future__ import annotations` is the most useful
for migrations. It lets you use `X | Y` syntax in
annotations on Python 3.9 without runtime errors.

### Compatibility shims

When you need to support both old and new:

```python
# Import shim -- new location, fall back to old
try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files

# Version-conditional behavior
import sys
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Polyfill pattern
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
```

Remove shims once you drop support for the old version.
They are temporary by design.

## Feature flags for gradual rollout

For high-risk migrations where you want to deploy before
fully activating:

```python
import os

USE_NEW_DATETIME = os.getenv(
    "USE_NEW_DATETIME", "false"
).lower() == "true"


def get_current_time():
    if USE_NEW_DATETIME:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)
    else:
        from datetime import datetime
        return datetime.utcnow()
```

Toggle with environment variables, config files, or a
feature flag service. This lets you roll back instantly
without redeploying.

## Common migration problems

| Problem | Symptom | Root cause | Fix |
|---|---|---|---|
| Naive vs aware datetimes | `TypeError: can't compare offset-naive and offset-aware` | Mixed `utcnow()` and `now(timezone.utc)` | Migrate all datetime creation in one pass; update `_parse_timestamp()` helpers too |
| Removed stdlib module | `ModuleNotFoundError: No module named 'cgi'` | Module removed in target version | Install PyPI replacement or rewrite using alternatives |
| Changed default behavior | Tests pass but output differs | Function default changed between versions | Read What's New docs; update assertions |
| Type hint syntax error | `TypeError: unsupported operand type(s) for \|` | Using `X \| Y` on Python <3.10 without `from __future__ import annotations` | Add the future import or use `Union[X, Y]` |
| C extension build failure | `error: command 'gcc' failed` during pip install | Dependency has no wheel for new Python | Wait for upstream to release a wheel, or pin to a compatible version |
| `PurePosixPath.match()` behavior | Glob `**` patterns silently fail | `match()` doesn't support `**` on <3.13 | Use `fnmatch.fnmatch()` instead |
| `fromisoformat()` strictness | `ValueError` on timestamps that previously parsed | 3.11 tightened ISO format validation | Normalize timestamps before parsing |
| `DeprecationWarning` now `TypeError` | Code that "worked" now raises at runtime | Deprecated feature removed in new version | Replace with the recommended alternative |
| Encoding defaults | `UnicodeDecodeError` on CI | `Path.read_text()` uses platform default encoding | Always pass `encoding="utf-8"` explicitly |

## Framework upgrade patterns

### Django major version upgrade

| Step | Action |
|---|---|
| 1 | Fix all deprecation warnings on current version first |
| 2 | Read the release notes for every version between current and target |
| 3 | Upgrade one minor version at a time (4.1 to 4.2, then 4.2 to 5.0) |
| 4 | Run `python manage.py check --deploy` after each step |
| 5 | Test migrations: `python manage.py migrate --plan` |

### Pydantic v1 to v2

| Change | v1 | v2 |
|---|---|---|
| Base class | `BaseModel` | `BaseModel` (same name, new internals) |
| Validators | `@validator` | `@field_validator` |
| Config | Inner `class Config` | `model_config = ConfigDict(...)` |
| `.dict()` | `model.dict()` | `model.model_dump()` |
| `.json()` | `model.json()` | `model.model_dump_json()` |

Pydantic provides a migration guide and a `bump-pydantic`
codemod: `pip install bump-pydantic && bump-pydantic src/`.

### Flask 2 to 3

| Change | Action |
|---|---|
| `@app.before_first_request` removed | Move to app factory or `with app.app_context()` |
| JSON handling changes | Use `flask.json.provider` instead of encoder/decoder |
| Async support changes | Review `async def` route behavior |

## Want to learn more?

- Say **"what are migration strategies?"** for the concept
  overview -- incremental vs big-bang, risk assessment,
  and when each approach works
- Say **"walk me through a Python version upgrade"** for
  the step-by-step task guide
- Say **"I need to upgrade Python"** for a 5-minute
  quickstart
- Run `/code-quality` to scan for deprecated patterns and
  style issues in migrated code
- Run `/smart-test` to verify test coverage before and
  after migration
- Run `/refactor` to plan large-scale structural changes
  that accompany a migration

## Related Topics

- **Concept**: Code migration -- strategies, risk
  assessment, compatibility layers, feature flags
- **Task**: Code migration -- step-by-step Python
  version upgrade guide
- **Quickstart**: Code migration -- 5-step guide to
  upgrading your Python version
