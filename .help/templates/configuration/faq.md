---
type: faq
feature: configuration
depth: faq
generated_at: 2026-04-14T15:31:12.559339+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration FAQ

## What is configuration?

The configuration system manages settings for Attune AI agents, workflows, and integrations. It handles both file-based configuration and environment variables, with support for different model providers and runtime environments.

## When should I use it?

Use the configuration system when you need to:
- Set up agent parameters (model, temperature, token limits)
- Configure workflow execution modes
- Manage environment-specific settings
- Switch between different LLM providers
- Store persistent configuration for book production or other workflows

## How do I load configuration?

Use `load_unified_config()` to load configuration from the default locations, or `ConfigLoader` for custom paths:

```python
from attune.config import load_unified_config

# Load from default paths
config = load_unified_config()

# Or specify a custom path
config = load_unified_config("./my-config.json")
```

## How do I work with environment variables?

Use `get_attune_env()` to read environment variables with fallback support:

```python
from attune.config import get_attune_env

# Checks ATTUNE_MODEL first, then EMPATHY_MODEL
model = get_attune_env("MODEL", default="gpt-4")
```

## What configuration formats are supported?

The system supports JSON configuration files. It searches these default locations:
- `./attune.config.json`
- `~/.attune/config.json`
- `~/.config/attune/config.json`

## How do I configure different agents?

Use `UnifiedAgentConfig` for general agents or `BookProductionConfig` for book production workflows:

```python
# General agent configuration
agent_config = config.for_book_production()

# Access model settings
model_id = agent_config.get_model_id()
```

## How do I debug configuration issues?

Run the configuration tests first:
```bash
pytest -k "config" -v
```

If tests pass but your code fails, check that:
- Your configuration file exists and is valid JSON
- Environment variables use the correct `ATTUNE_` prefix
- Required configuration sections are present

## Where are the source files?

- `src/attune/config/**`

**Tags:** `config`, `settings`
