---
type: task
name: task-configuration-setup
tags: [config, python, patterns, secrets]
source: developer-guidance
---

# How to Set Up Configuration

## Start with a settings module

Create a single file that owns all configuration for
your project. Every other module imports from here --
no `os.environ.get()` scattered through business logic.

```python
# src/myapp/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment overrides."""

    database_url: str = "sqlite:///local.db"
    debug: bool = False
    log_level: str = "INFO"
    allowed_hosts: list[str] = ["localhost"]

    model_config = {"env_prefix": "MYAPP_"}


settings = Settings()
```

Now `settings.database_url` pulls from `MYAPP_DATABASE_URL`
if set, falls back to `"sqlite:///local.db"` if not.

## Add a local `.env` file

For local development, create a `.env` at the project
root:

```bash
# .env -- local development only
MYAPP_DATABASE_URL=postgresql://localhost:5432/myapp_dev
MYAPP_DEBUG=true
MYAPP_LOG_LEVEL=DEBUG
```

Pydantic BaseSettings reads `.env` automatically when
you add `env_file`:

```python
class Settings(BaseSettings):
    # ... fields ...

    model_config = {
        "env_prefix": "MYAPP_",
        "env_file": ".env",
    }
```

**Immediately add `.env` to `.gitignore`.** Before you
put anything in it.

## Handle secrets correctly

Secrets go in environment variables only. Never in
config files, never in defaults:

```python
class Settings(BaseSettings):
    # Has a default -- not a secret
    debug: bool = False

    # No default -- required, must come from environment
    database_url: str
    secret_key: str

    model_config = {"env_prefix": "MYAPP_"}
```

If `MYAPP_SECRET_KEY` is not set, Pydantic raises a
`ValidationError` at import time with a clear message.
Your app fails fast instead of crashing later with a
`None` reference.

## Add environment-specific overrides

Use a single `Settings` class with an `environment`
field to control behavior:

```python
class Settings(BaseSettings):
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    model_config = {"env_prefix": "MYAPP_"}

    def model_post_init(self, __context):
        """Apply environment-specific defaults."""
        if self.environment == "development":
            self.debug = True
            self.log_level = "DEBUG"
        elif self.environment == "production":
            self.debug = False
            self.log_level = "WARNING"
```

Set `MYAPP_ENVIRONMENT=production` in your deploy
pipeline. Explicit overrides (like `MYAPP_DEBUG=true`)
still win over the environment defaults.

## Validate at startup

Add a validation step in your application entry point
to catch problems before they surface at runtime:

```python
# src/myapp/main.py
from myapp.settings import Settings


def create_app():
    """Create application with validated config."""
    try:
        settings = Settings()
    except ValidationError as e:
        print(f"Configuration error:\n{e}")
        raise SystemExit(1)

    if settings.environment == "production":
        assert settings.secret_key, "SECRET_KEY required"
        assert not settings.debug, "DEBUG must be off"

    return build_app(settings)
```

## Checklist

- [ ] Single settings module, not scattered `os.environ`
- [ ] `.env` file in `.gitignore`
- [ ] Secrets have no defaults (required from environment)
- [ ] Non-secrets have sensible defaults
- [ ] Config validated at startup
- [ ] Environment-specific behavior via `environment` field

## Want to learn more?

- Say **"show me config patterns"** for code examples
  of every approach (dotenv, YAML, TOML, CLI args)
- Say **"what is configuration setup?"** for the
  underlying concepts and 12-factor principles
- Ask **"/security-audit"** to scan your project for
  hardcoded secrets or leaked credentials
- Ask **"/code-quality"** to review your settings module
  for anti-patterns
