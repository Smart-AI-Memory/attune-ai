---
type: reference
subtype: procedural
name: task-configuration-setup
category: task
tags: [config, python, patterns, secrets]
source: developer-guidance
---

# Configuration Patterns Reference

Complete reference for Python configuration approaches
-- every pattern with code, tradeoffs, and security
notes.

## Pattern comparison

| Pattern | Best for | Secrets safe? | Type validation | Complexity |
|---------|----------|---------------|-----------------|------------|
| `os.environ` | Simple scripts | Yes (env only) | No (all strings) | Minimal |
| `python-dotenv` | Local dev | Yes if gitignored | No | Low |
| **Pydantic BaseSettings** | **Production apps** | **Yes** | **Yes** | **Low** |
| YAML config | Complex structure | No (file-based) | Manual | Medium |
| TOML config | pyproject.toml | No (file-based) | Manual | Medium |
| CLI arguments | Scripts, tools | Yes (ephemeral) | Yes (argparse) | Medium |

## os.environ

The simplest approach. Good for one or two values in a
script, not for applications:

```python
import os

database_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
debug = os.environ.get("DEBUG", "false").lower() == "true"
port = int(os.environ.get("PORT", "8000"))
```

**Tradeoffs:** No type validation. No defaults file.
Every value is a string -- manual parsing required.
Scattered `os.environ.get()` calls make it hard to see
what config your app needs.

## python-dotenv

Loads a `.env` file into `os.environ` at startup:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # reads .env into os.environ

database_url = os.environ["DATABASE_URL"]
debug = os.environ.get("DEBUG", "false").lower() == "true"
```

```bash
# .env
DATABASE_URL=postgresql://localhost:5432/myapp
DEBUG=true
```

**Tradeoffs:** Still no type validation. Still string
parsing. But `.env` files make local development easier.
Always gitignore `.env`.

## Pydantic BaseSettings (recommended)

Type-safe configuration with automatic environment
variable loading, `.env` support, and validation:

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    # Required -- no default, must come from environment
    database_url: str
    secret_key: str

    # Optional with defaults
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8000
    allowed_hosts: list[str] = ["localhost"]
    max_connections: int = Field(default=10, ge=1, le=100)

    model_config = {
        "env_prefix": "MYAPP_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Single instance, imported everywhere
settings = Settings()
```

**What you get:**

| Feature | Detail |
|---------|--------|
| Type coercion | `"true"` becomes `True`, `"8000"` becomes `8000` |
| Validation | `max_connections=200` raises `ValidationError` |
| Required fields | Missing `SECRET_KEY` fails at import time |
| Prefix support | `env_prefix="MYAPP_"` namespaces all vars |
| `.env` loading | Built-in, no extra `load_dotenv()` call |
| Nested models | Supports `__` separator for nested fields |

## YAML config

Good for complex, nested configuration that teams share:

```python
from pathlib import Path
import yaml

def load_config(path: str = "config.yml") -> dict:
    """Load YAML configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        return {}

    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
```

```yaml
# config.yml -- committed to git
database:
  pool_size: 10
  timeout: 30

logging:
  level: INFO
  format: json
```

**Security note:** Never put secrets in YAML files. Use
environment variables for secrets and YAML for structure.

**Tradeoffs:** No type validation without extra code.
File must be distributed with the app. Risk of secrets
creeping in over time.

## TOML config

Native support in Python 3.11+ via `tomllib`. Often used
alongside `pyproject.toml`:

```python
import tomllib
from pathlib import Path

def load_config(path: str = "config.toml") -> dict:
    """Load TOML configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        return {}

    with config_path.open("rb") as f:
        return tomllib.load(f)
```

```toml
# config.toml
[database]
pool_size = 10
timeout = 30

[logging]
level = "INFO"
format = "json"
```

**Tradeoffs:** Read-only in stdlib (no `tomllib.dump`).
Same secrets risk as YAML. Better type preservation than
YAML (integers stay integers).

## CLI arguments

For scripts and tools where users pass values at
invocation:

```python
import argparse

def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Server port"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()
```

**Tradeoffs:** Good type validation and help text. Not
suitable for secrets (visible in `ps` output). Best
combined with BaseSettings for the full hierarchy.

## Secrets handling

Secrets require special care regardless of which config
pattern you use:

| Do | Do not |
|----|--------|
| Store secrets in environment variables | Put secrets in config files |
| Add `.env` to `.gitignore` immediately | Commit `.env` to git |
| Use different secrets per environment | Share secrets across dev/staging/prod |
| Validate secrets exist at startup | Let missing secrets surface at runtime |
| Rotate secrets on a schedule | Treat secrets as permanent |

**Validating secrets at startup:**

```python
class Settings(BaseSettings):
    secret_key: str  # No default = required

    model_config = {"env_prefix": "MYAPP_"}

# If MYAPP_SECRET_KEY is not set, this line raises
# ValidationError with a clear message
settings = Settings()
```

## Environment-specific configs

Use a single settings class with an environment field:

```python
class Settings(BaseSettings):
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    model_config = {"env_prefix": "MYAPP_"}
```

| Environment | Set via | Typical values |
|-------------|---------|----------------|
| Development | `.env` file | `DEBUG=true`, local DB |
| Staging | Deploy pipeline | Production-like, test secrets |
| Production | Deploy pipeline | `DEBUG=false`, real secrets |

Avoid separate config files per environment (like
`config_dev.yml`, `config_prod.yml`). They drift.
One settings class with environment overrides is
simpler and safer.

## Default values strategy

| Field type | Default strategy | Example |
|------------|-----------------|---------|
| Secrets | No default (required) | `secret_key: str` |
| URLs / hosts | Development default | `db_url: str = "sqlite:///local.db"` |
| Feature flags | Conservative default | `debug: bool = False` |
| Numeric limits | Safe default | `max_retries: int = 3` |
| Lists | Empty or localhost | `allowed_hosts: list[str] = ["localhost"]` |

The principle: defaults should make local development
work out of the box while being safe if accidentally
used in production.

## Want to learn more?

- Say **"what is configuration setup?"** for the
  concepts and 12-factor principles
- Say **"how do I set up configuration?"** for the
  step-by-step task guide
- Say **"I need to add config to my project"** for a
  5-minute quickstart
- Ask **"/security-audit"** to scan for hardcoded
  secrets in your codebase
- Ask **"/code-quality"** to review config module
  patterns and anti-patterns
