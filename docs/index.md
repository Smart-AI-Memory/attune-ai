---
description: AI-powered developer workflows for Claude Code — spec-driven development, cost optimization, and multi-agent orchestration.
---

# Attune AI

**AI-powered developer workflows for Claude Code — spec-driven
development, cost optimization, and multi-agent orchestration.**

[![PyPI version](https://badge.fury.io/py/attune-ai.svg)](https://pypi.org/project/attune-ai/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

!!! tip "Start here"

    New to Attune AI? Begin with a guided, hands-on walkthrough:

    - **[Tutorials](tutorials/index.md)** — learn by building, start to
      finish (try [Build a Workflow](tutorials/build-a-workflow.md))
    - **[Getting Started](getting-started/index.md)** — install and run
      your first workflow in a few minutes
    - **[How-to guides](how-to/index.md)** — task recipes for specific
      goals once you know your way around

---

## What is Attune AI?

Attune AI is a developer-workflow toolkit for
[Claude Code](https://claude.com/claude-code). It turns requirements
into reliable software through spec-driven development, routes each
step to the most cost-effective model tier, and coordinates
multi-agent teams — with a living help system generated from the code
itself.

It ships two ways, which work together:

- a **Claude Code plugin** (commands, skills, hooks, and MCP tools), and
- the **`attune` CLI** plus a Python API for scripting and CI.

---

## Install

```bash
pip install attune-ai
```

Or add the plugin to Claude Code:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
```

Then explore the command hubs — `/spec`, `/attune`, `/security`,
`/smart-test`, `/release`, `/help` — or run `attune --help`. The
[Getting Started](getting-started/index.md) guide walks through a first
end-to-end workflow.

---

## Documentation

Organized with the [Diátaxis framework](https://diataxis.fr/) so each
need has an obvious home:

| Section | Purpose | Start here |
|---------|---------|------------|
| **[Tutorials](tutorials/index.md)** | Learn by doing | [Build a Workflow](tutorials/build-a-workflow.md) |
| **[How-to](how-to/index.md)** | Solve a specific task | [Agent Factory](how-to/agent-factory.md) |
| **[Reference](reference/index.md)** | Look up details | [API Reference](reference/API_REFERENCE.md) |

---

## License

**Apache License 2.0** — free and open source.

- ✅ Free for everyone, including commercial use
- ✅ No team-size, seat, or revenue restrictions
- ✅ Modify, distribute, and build on it freely

[Read the full license](https://github.com/Smart-AI-Memory/attune-ai/blob/main/LICENSE)

---

## Next Steps

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **Get Started**

    ---

    Install and run your first workflow in a few minutes

    [:octicons-arrow-right-24: Getting Started](getting-started/index.md)

-   :material-school:{ .lg .middle } **Tutorials**

    ---

    Guided, start-to-finish walkthroughs

    [:octicons-arrow-right-24: Browse tutorials](tutorials/index.md)

-   :material-wrench:{ .lg .middle } **How-to Guides**

    ---

    Task recipes for specific goals

    [:octicons-arrow-right-24: Browse how-tos](how-to/index.md)

-   :material-book-open-variant:{ .lg .middle } **API Reference**

    ---

    Complete API documentation

    [:octicons-arrow-right-24: API Docs](reference/index.md)

</div>

---

## Community

- **GitHub**: [Smart-AI-Memory/attune-ai](https://github.com/Smart-AI-Memory/attune-ai)
- **PyPI**: [attune-ai](https://pypi.org/project/attune-ai/)
- **Issues**: [Report bugs or request features](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **Discussions**: [Ask questions](https://github.com/Smart-AI-Memory/attune-ai/discussions)

---

<!-- markdownlint-disable MD036 -->
**Built by Patrick Roebuck in collaboration with Claude**
<!-- markdownlint-enable MD036 -->
