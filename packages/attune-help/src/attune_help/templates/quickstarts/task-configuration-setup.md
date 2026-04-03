---
type: quickstart
name: task-configuration-setup
tags: [config, python, patterns, secrets]
source: developer-guidance
---

# Quickstart: Add Configuration to Your Project

Set up a typed, validated configuration system in
5 minutes using Pydantic BaseSettings.

## Step 1: Install the dependency

```bash
pip install pydantic-settings
```

## Step 2: Create your settings module

```python
# src/myapp/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App configuration. Environment variables override
    defaults."""

    database_url: str = "sqlite:///local.db"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str  # Required -- no default

    model_config = {
        "env_prefix": "MYAPP_",
        "env_file": ".env",
    }


settings = Settings()
```

## Step 3: Create a local `.env` file

```bash
# .env
MYAPP_DATABASE_URL=postgresql://localhost:5432/myapp
MYAPP_DEBUG=true
MYAPP_SECRET_KEY=local-dev-only-not-a-real-secret
```

Then immediately gitignore it:

```bash
echo ".env" >> .gitignore
```

## Step 4: Use settings in your code

```python
from myapp.settings import settings

if settings.debug:
    print(f"Connecting to {settings.database_url}")
```

## Step 5: Validate on startup

```python
# src/myapp/main.py
from pydantic import ValidationError

try:
    from myapp.settings import settings
except ValidationError as e:
    print(f"Bad config:\n{e}")
    raise SystemExit(1)
```

If `MYAPP_SECRET_KEY` is not set, you get a clear
error at startup instead of a crash at runtime.

**Done.** Your app has typed config, environment
overrides, and secrets validation.

## What you get

| Feature | How it works |
|---------|-------------|
| Type safety | `"true"` auto-converts to `True` |
| Required secrets | Missing `SECRET_KEY` fails at import |
| Env override | `MYAPP_DEBUG=false` overrides any default |
| Local `.env` | Loaded automatically, never committed |

## Want to learn more?

- Say **"how do I set up configuration?"** for the
  full step-by-step guide with environment-specific
  overrides
- Say **"show me config patterns"** for every approach
  (YAML, TOML, dotenv, CLI args)
- Say **"what is configuration setup?"** for 12-factor
  principles and config hierarchy
- Ask **"/security-audit"** to verify no secrets leaked
  into your source
