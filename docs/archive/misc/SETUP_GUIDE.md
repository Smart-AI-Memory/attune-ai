# Attune AI Setup Guide

**Version:** 5.1.1
**Last Updated:** February 2026

This guide covers the interactive setup wizard and configuration commands for Attune AI.

---

## Quick Start

### Option 1: Interactive Setup Wizard (Recommended)

```bash
attune setup
```

The wizard guides you through 6 stages to configure Attune AI for your use case.

### Option 2: Quick Setup with Preset

```bash
attune setup --preset code-review
```

Skip the wizard and use a pre-configured setup optimized for code review workflows.

### Option 3: Create Default Config

```bash
attune init
```

Creates a default configuration file that you can edit manually.

---

## CLI Commands

### `attune setup`

Interactive configuration wizard with 6 stages.

**Options:**

| Flag | Description |
|------|-------------|
| `--preset NAME` | Skip wizard, use preset (code-review, test-gen, documentation, full-stack, custom) |
| `--quick` | Quick mode - minimal prompts with sensible defaults |
| `--output PATH` | Custom output path (default: `empathy.config.yml`) |

**Examples:**

```bash
# Full interactive wizard
attune setup

# Quick setup for test generation
attune setup --preset test-gen

# Quick mode with custom output
attune setup --quick --output ./config/empathy.yml
```

### `attune init`

Creates a default configuration file without the interactive wizard.

**Options:**

| Flag | Description |
|------|-------------|
| `--output PATH` | Custom output path (default: `empathy.config.yml`) |
| `--force` | Overwrite existing config file |

**Examples:**

```bash
# Create default config
attune init

# Overwrite existing config
attune init --force

# Custom location
attune init --output ~/.config/attune/config.yml
```

### `attune validate`

Validates an existing configuration file.

**Options:**

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to config file (default: `empathy.config.yml`) |

**Examples:**

```bash
# Validate default config
attune validate

# Validate specific file
attune validate --config ./my-config.yml
```

---

## Use Case Presets

Presets are pre-configured settings optimized for specific workflows. Use `--preset NAME` with the setup command.

### `code-review`

**Best for:** Teams focused on code quality and review automation.

| Setting | Value |
|---------|-------|
| Auth Strategy | subscription |
| Default Tier | capable |
| Complex Tasks | premium |
| Simple Tasks | cheap |
| Persistence | redis |
| Cache TTL | 1 hour |

### `test-gen`

**Best for:** Automated test generation.

| Setting | Value |
|---------|-------|
| Auth Strategy | api |
| Default Tier | capable |
| Complex Tasks | premium |
| Simple Tasks | capable |
| Persistence | redis |
| Cache TTL | 30 minutes |

### `documentation`

**Best for:** Documentation generation and maintenance workflows.

| Setting | Value |
|---------|-------|
| Auth Strategy | subscription |
| Default Tier | cheap |
| Complex Tasks | capable |
| Simple Tasks | cheap |
| Persistence | file |
| Cache TTL | 2 hours |

### `full-stack`

**Best for:** Comprehensive development with all features enabled.

| Setting | Value |
|---------|-------|
| Auth Strategy | hybrid |
| Default Tier | capable |
| Complex Tasks | premium |
| Simple Tasks | cheap |
| Persistence | redis |
| Cache TTL | 1 hour |

### `custom`

**Best for:** Manual configuration of all settings.

Starts the interactive wizard with no preset values, allowing full customization.

---

## Setup Wizard Stages

The interactive wizard guides you through 6 configuration stages:

### Stage 1: Use Case Selection

Choose your primary use case or start with a preset.

```text
=== Stage 1/6: Use Case Selection ===

Select your primary use case:
  1. code-review  - Code review and quality analysis
  2. test-gen     - Test generation workflows
  3. documentation - Documentation generation
  4. full-stack   - Full development workflow
  5. custom       - Configure everything manually

Enter choice [1-5]:
```

### Stage 2: Authentication

Configure how Attune AI authenticates with LLM providers.

```text
=== Stage 2/6: Authentication ===

Select authentication strategy:
  1. subscription - Use Claude subscription (free tier)
  2. api          - Use Anthropic API (pay-per-use)
  3. hybrid       - Smart routing between both

Enter choice [1-3]:
```

**Strategy Details:**

| Strategy | Description | Best For |
|----------|-------------|----------|
| subscription | Uses Claude subscription | Small/medium codebases, cost-conscious teams |
| api | Direct Anthropic API | Large codebases, high-volume usage |
| hybrid | Routes based on task size | Mixed workloads, cost optimization |

### Stage 3: Model Routing

Configure which AI models handle different task complexities.

```text
=== Stage 3/6: Model Routing ===

Configure model tiers for different task types:

Default tier for most tasks:
  1. cheap   - Claude Haiku (fastest, lowest cost)
  2. capable - Claude Sonnet (balanced)
  3. premium - Claude Opus (highest quality)

Enter choice [1-3]:
```

**Model Tiers:**

| Tier | Model | Use Cases |
|------|-------|-----------|
| cheap | Claude Haiku | Simple tasks, high-volume operations |
| capable | Claude Sonnet | Most development tasks, balanced performance |
| premium | Claude Opus | Complex analysis, critical decisions |

### Stage 4: Persistence

Configure how Attune AI stores session data and cache.

```text
=== Stage 4/6: Persistence ===

Select persistence backend:
  1. redis  - Redis (recommended for teams)
  2. file   - Local file system
  3. memory - In-memory only (no persistence)

Enter choice [1-3]:
```

**Persistence Options:**

| Backend | Description | Requirements |
|---------|-------------|--------------|
| redis | Distributed cache, team collaboration | Redis server |
| file | Local JSON files | Write access to filesystem |
| memory | No persistence between sessions | None |

If you select Redis, you'll be prompted for connection details:

```text
Redis host [localhost]:
Redis port [6379]:
Redis database [0]:
```

### Stage 5: Environment

Configure environment-specific settings.

```text
=== Stage 5/6: Environment ===

Select environment:
  1. development - Local development
  2. staging     - Pre-production testing
  3. production  - Production deployment

Enter choice [1-3]:
```

Additional options:

- **Debug mode**: Enable verbose logging
- **Telemetry**: Enable usage analytics

### Stage 6: Review & Save

Review all settings and save the configuration.

```text
=== Stage 6/6: Review & Save ===

Configuration Summary:
─────────────────────
Use Case:      code-review
Auth Strategy: subscription
Default Tier:  capable
Persistence:   redis
Environment:   development

Save configuration? [Y/n]:
Output path [empathy.config.yml]:
```

---

## Configuration File Reference

The setup wizard generates an `empathy.config.yml` file:

```yaml
# Attune AI Configuration
# Generated by setup wizard

version: "1.0"

# Authentication settings
auth:
  strategy: hybrid          # subscription | api | hybrid
  api_key_env: ANTHROPIC_API_KEY
  subscription_fallback: true

# Model routing settings
routing:
  default_tier: capable     # cheap | capable | premium
  complex_tasks: premium
  simple_tasks: cheap
  auto_upgrade: true        # Upgrade tier for complex tasks

# Persistence settings
persistence:
  backend: redis            # redis | file | memory
  redis:
    host: localhost
    port: 6379
    db: 0
  cache_ttl: 3600           # seconds

# Environment settings
environment:
  name: development         # development | staging | production
  debug: false
  telemetry: true
```

### Configuration Sections

#### `auth` - Authentication

| Key | Type | Description |
|-----|------|-------------|
| `strategy` | string | Authentication method (subscription, api, hybrid) |
| `api_key_env` | string | Environment variable for API key |
| `subscription_fallback` | boolean | Fall back to subscription if API fails |

#### `routing` - Model Routing

| Key | Type | Description |
|-----|------|-------------|
| `default_tier` | string | Default model tier (cheap, capable, premium) |
| `complex_tasks` | string | Tier for complex operations |
| `simple_tasks` | string | Tier for simple operations |
| `auto_upgrade` | boolean | Automatically upgrade tier for complexity |

#### `persistence` - Data Storage

| Key | Type | Description |
|-----|------|-------------|
| `backend` | string | Storage backend (redis, file, memory) |
| `redis.host` | string | Redis server hostname |
| `redis.port` | integer | Redis server port |
| `redis.db` | integer | Redis database number |
| `cache_ttl` | integer | Cache time-to-live in seconds |

#### `environment` - Environment Settings

| Key | Type | Description |
|-----|------|-------------|
| `name` | string | Environment name |
| `debug` | boolean | Enable debug logging |
| `telemetry` | boolean | Enable usage telemetry |

---

## Validation

After creating or editing a configuration file, validate it:

```bash
attune validate
```

The validator checks:

- YAML syntax correctness
- Required fields present
- Valid enum values (tiers, strategies, backends)
- Redis connection (if configured)
- File permissions (if file persistence)

**Example output:**

```text
Validating empathy.config.yml...

✅ YAML syntax: valid
✅ Required fields: present
✅ Auth strategy: hybrid (valid)
✅ Model tiers: valid
✅ Redis connection: connected
✅ Permissions: writable

Configuration is valid!
```

---

## Troubleshooting

### "Config file already exists"

Use `--force` to overwrite:

```bash
attune init --force
```

### "Redis connection failed"

Check Redis is running:

```bash
redis-cli ping
# Should respond: PONG
```

### "Invalid tier value"

Valid tiers are: `cheap`, `capable`, `premium`

### "Permission denied"

Ensure write permissions to the output directory:

```bash
chmod 755 ./config/
attune setup --output ./config/empathy.yml
```

---

## Related Documentation

- [AUTH_STRATEGY_GUIDE.md](AUTH_STRATEGY_GUIDE.md) - Detailed authentication configuration
- [AUTH_CLI_IMPLEMENTATION.md](AUTH_CLI_IMPLEMENTATION.md) - CLI command reference
- [CODING_STANDARDS.md](CODING_STANDARDS.md) - Project coding standards

---

## Support

- **Issues:** [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions)
