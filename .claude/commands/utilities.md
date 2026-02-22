---
name: utilities
description: Authentication and provider management
category: utility
aliases: [u, auth]
tags: [auth, provider, setup, utilities]
version: "1.0.0"
question:
  header: "Utility"
  question: "What do you need?"
  multiSelect: false
  options:
    - label: "Provider setup"
      description: "Configure API provider authentication"
    - label: "Provider status"
      description: "Check current authentication status"
    - label: "Provider recommend"
      description: "Get provider recommendation"
    - label: "Provider reset"
      description: "Reset provider configuration"
---

# utilities

Authentication and provider management utilities.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `auth-setup` | Configure API provider |
| `auth-status` | Check auth status |
| `auth-recommend` | Get provider recommendation |
| `auth-reset` | Reset provider config |

## Usage

```bash
/utilities                # Ask what to do
/utilities auth-setup     # Configure provider
/utilities auth-status    # Check status
```

Or use natural language: "auth", "auth-setup",
"auth-status", "auth-recommend", "auth-reset".

## Behavior

### auth-setup

Run the provider setup command:

```bash
uv run attune provider setup
```

Guide the user through provider configuration
if they need help choosing.

### auth-status

Run the provider status command:

```bash
uv run attune provider status
```

Display results and suggest fixes if
authentication is not configured.

### auth-recommend

Run the provider recommendation command:

```bash
uv run attune provider recommend
```

### auth-reset

Use `AskUserQuestion` to confirm:

- Are you sure you want to reset provider config?

Then run:

```bash
uv run attune provider reset
```
