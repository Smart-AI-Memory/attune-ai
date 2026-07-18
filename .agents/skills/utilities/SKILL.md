---
name: utilities
description: Authentication and provider management
---
# utilities

Authentication, subscription, and provider management utilities.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `subscription` | Show subscription/auth strategy status |
| `show` | Show current provider configuration |
| `set` | Set the active LLM provider |
| `setup` | Configure auth strategy interactively |

## Usage

```bash
/utilities                   # Ask what to do
/utilities subscription      # Show subscription status
/utilities show              # Show current provider
/utilities set               # Set provider
/utilities setup             # Configure auth strategy
```

Or use natural language: "subscription status", "auth", "provider",
"show provider", "set provider", "what is my subscription".

## Behavior

### subscription

Run the auth status command to show subscription tier and strategy:

```bash
uv run attune auth status
```

Display the subscription tier (FREE/PRO/MAX/ENTERPRISE), default auth
mode, and module size thresholds.

### show

Run the provider show command:

```bash
uv run attune provider show
```

Display the current provider mode, primary provider,
and available providers.

### set

Use `AskUserQuestion` to confirm:

- Which provider? (anthropic, openai, hybrid)

Then run:

```bash
uv run attune provider set <provider>
```

### setup

Run the interactive auth strategy setup:

```bash
uv run attune auth setup
```
