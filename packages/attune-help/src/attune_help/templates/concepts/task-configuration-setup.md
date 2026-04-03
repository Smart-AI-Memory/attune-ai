---
type: concept
name: task-configuration-setup
tags: [config, python, patterns, secrets]
source: developer-guidance
---

# Configuration Setup

Configuration is the bridge between your code and the
environment it runs in. A well-structured configuration
system follows a clear hierarchy: environment variables
override config files, which override hardcoded defaults.
This lets the same code run in development, staging, and
production without changes.

## The config hierarchy

Values resolve top-down. The first source that provides
a value wins:

| Priority | Source | Security | Use case |
|----------|--------|----------|----------|
| **1 (highest)** | Environment variables | Safe for secrets | API URLs, feature flags, secrets |
| **2** | CLI arguments | Safe (ephemeral) | One-off overrides, scripts |
| **3** | `.env` file (local only) | Safe if gitignored | Local development defaults |
| **4** | YAML / TOML config file | Never store secrets | Shared team settings, structure |
| **5** | Pydantic BaseSettings | N/A (code) | Type-safe defaults with validation |
| **6 (lowest)** | Hardcoded defaults | N/A (code) | Sensible fallbacks |

This follows the 12-factor app principle: configuration
that changes between deploys belongs in the environment,
not in code.

## Secrets management

Secrets deserve special attention because a single leaked
credential can compromise an entire system.

| Rule | Why |
|------|-----|
| **Never commit secrets to source control** | Git history is permanent; rotating leaked keys is expensive |
| **Use environment variables for all secrets** | They stay out of version control by design |
| **Add `.env` to `.gitignore` immediately** | Before you put anything in it |
| **Use different secrets per environment** | A leaked dev key shouldn't open production |
| **Validate secrets exist at startup** | Fail fast with a clear error, not halfway through a request |

## 12-factor principles that matter

1. **Config in the environment** -- No config values
   baked into built artifacts
2. **One codebase, many deploys** -- Same code runs
   everywhere; config is the only difference
3. **Fail fast** -- If required config is missing, crash
   at startup with a clear message, not at runtime with
   a cryptic `None` error
4. **Typed config** -- Parse and validate config values
   at the boundary (startup), not at the point of use

## What makes config go wrong

Most config bugs come from the same few mistakes:
secrets committed to git, missing validation that
surfaces as a `None` error deep in the call stack, or
config files that diverge silently between environments.
A settings module with Pydantic BaseSettings eliminates
all three.

## Want to learn more?

- Say **"how do I set up configuration?"** for a
  step-by-step guide
- Say **"show me config patterns"** for code examples
  of every approach
- Say **"I need to add config to my project"** for a
  5-minute quickstart
- Ask **"/security-audit"** to check your project for
  leaked secrets
- Ask **"/code-quality"** to review your config module
  for common patterns
