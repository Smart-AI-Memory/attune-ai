---
description: Reference API reference: Information-oriented technical reference for Attune AI. This section provides detailed speci
---

# Reference

Information-oriented technical reference for Attune AI.

This section provides detailed specifications, API documentation, and
quick reference materials for when you need to look something up.

## CLI Reference

<div class="grid cards" markdown>

- :material-console: **[CLI Guide](CLI_GUIDE.md)**

    Complete guide to the `empathy` command

- :material-lightning-bolt: **[CLI Cheatsheet](CLI_CHEATSHEET.md)**

    Quick reference for common commands

</div>

## API Reference

<div class="grid cards" markdown>

- :material-api: **[API Overview](API_REFERENCE.md)**

    Complete API reference

- :material-cog: **[Configuration](configuration.md)**

    Configuration options and environment variables

- :material-memory: **[Short-Term Memory](SHORT_TERM_MEMORY.md)**

    Memory system technical reference

</div>

### Core Modules

- [EmpathyOS](empathy-os.md) - Main framework module
- [Core](core.md) - Core functionality
- [Config](config.md) - Configuration system
- [Persistence](persistence.md) - Data persistence layer
- [Pattern Library](pattern-library.md) - Pattern storage and retrieval
- [Multi-Agent](multi-agent.md) - Multi-agent coordination
- [LLM Toolkit](llm-toolkit.md) - LLM integration utilities

### Wizards

- [Getting Started](../guides/wizards-getting-started.md) - Run your first wizard in under 10 minutes
- [Architecture](../guides/wizard-architecture.md) - How the wizard system works internally
- [Custom Development](../guides/wizard-custom-development.md) - Build Python-based wizards

## Help

<div class="grid cards" markdown>

- :material-help-circle: **[FAQ](FAQ.md)**

    Frequently asked questions

- :material-bug: **[Troubleshooting](TROUBLESHOOTING.md)**

    Common issues and solutions

- :material-book-alphabet: **[Glossary](glossary.md)**

    Terms and definitions

- :material-file-document: **[User Guide](USER_GUIDE.md)**

    Comprehensive user documentation

</div>

---

## Quick Links

- [Getting Started Tutorial](../tutorials/quickstart.md)
- [How-to Guides](../how-to/index.md)
- [Explanation](../explanation/index.md)

## Installation

```bash
pip install attune-ai
```

For LLM support:
```bash
pip install attune-ai[llm]
```

For healthcare applications:
```bash
pip install attune-ai[healthcare]
```
