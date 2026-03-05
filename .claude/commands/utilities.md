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
    - label: "Show provider"
      description: "Show current provider configuration"
    - label: "Set provider"
      description: "Change the active LLM provider"
---

# utilities

Authentication and provider management utilities.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `show` | Show current provider configuration |
| `set` | Set the active LLM provider |

## Usage

```bash
/utilities                # Ask what to do
/utilities show           # Show current provider
/utilities set            # Set provider
```

Or use natural language: "auth", "provider",
"show provider", "set provider".

## Behavior

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
