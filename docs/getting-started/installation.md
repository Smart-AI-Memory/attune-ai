---
description: Install Attune AI with pip in 2 minutes. The core install covers the CLI, workflows, and MCP server; add extras per surface (API agents, ops dashboard, Redis).
---

# Installation

Get Attune AI installed and configured in about 2 minutes.

---

## Step 1: Install the Package

The core install covers most users — the CLI, all workflows, the
MCP server, RAG, and the Agent SDK are core dependencies:

```bash
pip install attune-ai
```

Add extras only for the surfaces you use (they combine, e.g.
`'attune-ai[developer,ops]'` — keep the quotes; zsh and bash treat
square brackets as glob characters):

| You want | Install |
| -------- | ------- |
| Claude API mode + LangChain/LangGraph agent teams | `pip install 'attune-ai[developer]'` |
| The ops dashboard (`attune ops`) | `pip install 'attune-ai[ops]'` |
| Redis / Agent Memory Server memory backend | `pip install 'attune-ai[redis]'` |
| Help authoring (`.help/` templates) | `pip install 'attune-ai[author]'` |

### Verify Installation

```bash
python -c "import attune; print(f'Attune AI v{attune.__version__}')"
```

---

## Step 2: Configure an LLM Provider

Attune AI uses Anthropic Claude as its LLM provider.

### Option A: Environment Variable (Quick)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Option B: .env File (Persistent)

Create a `.env` file in your project root:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

The framework auto-detects `.env` files.

### Option C: Interactive Setup

```bash
python -m attune.models.cli provider --interactive
```

### Verify Provider

```bash
python -m attune.models.cli provider
```

Expected output:
```
Current provider: anthropic
Available models: claude-opus-4-8, claude-sonnet-5, claude-haiku-4-5
API key configured
```

---

## Step 3: Optional - Redis for Memory

Redis enables multi-agent coordination and session persistence. Skip this for now if you just want to try the framework.

=== "macOS (Homebrew)"

    ```bash
    brew install redis
    brew services start redis
    redis-cli ping  # Should return: PONG
    ```

=== "Docker"

    ```bash
    docker run -d -p 6379:6379 --name attune-redis redis:alpine
    ```

=== "Skip for Now"

    The framework works without Redis (falls back to in-memory storage).

    You can add Redis later when you need:

    - Multi-agent coordination
    - Session persistence
    - Pattern staging

See [Redis Setup](redis-setup.md) for production configuration.

---

## Troubleshooting

### "No API key configured"

```bash
# Check your environment
env | grep API_KEY

# Set it
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify
attune provider show
```

### "ModuleNotFoundError: attune"

```bash
# Reinstall
pip install --upgrade attune-ai

# Or for development
pip install -e '.[dev]'
```

### Python version too old

```bash
python --version  # Need 3.10+

# Use pyenv to manage versions
pyenv install 3.11
pyenv local 3.11
```

---

## See Also

- [Redis Setup](redis-setup.md) - Configure Redis for production use
- [MCP Integration](mcp-integration.md) - Connect to Claude Code
- [Configuration Reference](../reference/config.md) - Customize settings
- [First Steps](first-steps.md) - Run your first workflow

---

## Next Step

You're installed! Continue to [First Steps](first-steps.md) to run your first workflow.
