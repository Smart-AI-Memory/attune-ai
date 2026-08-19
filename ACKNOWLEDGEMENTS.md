# Acknowledgements

The Attune AI stands on the shoulders of giants. This project would not be possible without the incredible work of the open source community. We are deeply grateful to all the developers, maintainers, and contributors of the projects listed below.

---

## Design & Workflow Inspiration

### Hook System & Markdown Agent Format

The hook system and markdown-based agent definition patterns in this framework were **inspired by** the excellent work in [everything-claude-code](https://github.com/affaan-m/everything-claude-code) by **Affaan Mustafa** (@affaan-m).

Affaan's repository represents 10+ months of battle-tested Claude Code configurations, and we learned valuable architectural patterns from studying his approach:

- **Event-driven hooks** (PreToolUse, PostToolUse, SessionStart, etc.)
- **Markdown agents with YAML frontmatter** for portable, human-readable definitions
- **Strategic context compaction** for managing token windows
- **Continuous learning patterns** for extracting reusable knowledge

#### What We Learned vs. What We Built

| Pattern Learned | Empathy Implementation |
|-----------------|------------------------|
| Hook event types | Python/Pydantic-based HookConfig with async execution |
| Markdown agent format | MarkdownAgentParser integrated with UnifiedAgentConfig |
| Markdown commands | CommandRegistry with YAML frontmatter parsing and alias resolution |
| Session persistence | Integration with Empathy's state management and trust levels |
| Continuous learning | SessionEvaluator and PatternExtractor for knowledge retention |

Our implementation is original Python code designed to integrate with Attune AI's existing architecture (LangGraph, Pydantic, multi-tier model routing), but the conceptual patterns we learned from Affaan's work were invaluable.

**License:** everything-claude-code is released under the MIT License, which permits derivative works with attribution. We provide this attribution in good faith and gratitude.

**Links:**

- **everything-claude-code**: https://github.com/affaan-m/everything-claude-code
- **Affaan's Guides**:
  - [The Shorthand Guide](https://x.com/affaanmustafa/status/2012378465664745795)
  - [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352)
- **Affaan on X/Twitter**: [@affaanmustafa](https://x.com/affaanmustafa)

### Claude Code & Workflow Philosophy

**Boris Cherny** (@bcherny), the creator of
[Claude Code](https://github.com/anthropics/claude-code),
was also a significant inspiration for this project. His
candid posts about how he personally uses Claude Code
offered practical insights that shaped how Attune AI
approaches agentic workflows:

- **Plan Mode first** — Boris advocates using Plan Mode
  for every non-trivial task, iterating on the plan before
  switching to execution. This directly influenced Attune's
  Socratic discovery pattern and our emphasis on scoping
  before running.
- **Parallel sessions** — Running multiple Claude Code
  sessions concurrently (5+ in terminal, 5-10 on
  claude.ai/code) demonstrated that orchestrating many
  agents in parallel is not just possible but productive.
  This validated Attune's multi-agent architecture.
- **Verification loops** — Boris stresses giving Claude a
  way to verify its own work, noting it can 2-3x the
  quality of results. This principle is embedded in
  Attune's validation-first workflow design.
- **Shared CLAUDE.md** — His team checks CLAUDE.md into
  git and collaboratively maintains it as a living
  document. Attune adopted this pattern directly for
  project-level instructions.

Boris created Claude Code and then generously shared how
he actually uses it — the hard-won, non-obvious workflow
patterns that only come from building something and living
with it. His detailed posts about plan-first execution,
verification loops, and parallel agent sessions represent
months of real-world refinement. Studying that work
significantly influenced Attune's design, and in several
cases taught us lessons that led to meaningful changes in
our approach.

Similarly, Affaan's 10+ months of battle-tested Claude
Code configurations represent a depth of practical
experience that can't be shortcut. The patterns we learned
from his hook system, markdown agent format, and context
compaction strategies shaped core parts of Attune's
architecture.

One of Attune AI's goals is to make the kind of best
practices that Boris and Affaan discovered through months
of independent work accessible to a wider audience.
Without a framework to codify them, each team would have
to discover and implement them on their own. Attune
packages these proven workflows into reusable, structured
tools so that any developer can benefit from them out of
the box.

**Links:**

- **Boris on X/Twitter**:
  [@bcherny](https://x.com/bcherny)
- **Original thread**: [How I use Claude Code](https://x.com/bcherny/status/2007179832300581177)
- **Detailed writeup**: [How the Creator of Claude Code Uses Claude Code](https://howborisusesclaudecode.com/)

Thank you, Affaan and Boris, for sharing your knowledge
with the community.

---

## Core Framework Dependencies

### Python Type System & Validation

- **[Pydantic](https://github.com/pydantic/pydantic)** - Data validation using Python type annotations. The foundation of our configuration and model validation system.
- **[typing-extensions](https://github.com/python/typing_extensions)** - Backported and experimental type hints for Python.

### Configuration & Environment

- **[python-dotenv](https://github.com/theskumar/python-dotenv)** - Reads key-value pairs from `.env` files and sets them as environment variables.
- **[PyYAML](https://github.com/yaml/pyyaml)** - YAML parser and emitter for Python. Used for workflow configuration.
- **[defusedxml](https://github.com/tiran/defusedxml)** - XML bomb protection for Python stdlib modules.

### Logging & CLI

- **[structlog](https://github.com/hynek/structlog)** - Structured logging for Python. Makes logs readable, parseable, and debuggable.
- **[rich](https://github.com/Textualize/rich)** - Beautiful formatting in the terminal. Powers our progress bars and formatted output.
- **[typer](https://github.com/tiangolo/typer)** - Modern CLI framework based on Python type hints. Makes our CLI intuitive and self-documenting.

---

## AI & LLM Integration

### LLM Providers

- **[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)** - Official Python SDK for Claude AI. Our primary LLM provider integration.
- **[OpenAI Python SDK](https://github.com/openai/openai-python)** - Official Python SDK for OpenAI's GPT models.
- **[Google Generative AI](https://github.com/google/generative-ai-python)** - Official Python SDK for Google's Gemini models.

### Agent Frameworks

- **[LangChain](https://github.com/langchain-ai/langchain)** - Framework for developing applications powered by language models. Used for our agent workflows.
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - Library for building stateful, multi-actor applications with LLMs. Powers our meta-orchestration.
- **[LangChain Core](https://github.com/langchain-ai/langchain)** - Core abstractions and runtime for LangChain.
- **[LangChain Text Splitters](https://github.com/langchain-ai/langchain)** - Text splitting utilities for LangChain.

### Semantic Search & Embeddings

- **[Sentence Transformers](https://github.com/UKPLab/sentence-transformers)** - Multilingual sentence embeddings. Powers our semantic caching and similarity search.
- **[PyTorch](https://github.com/pytorch/pytorch)** - Deep learning framework. Required for sentence transformers.
- **[NumPy](https://github.com/numpy/numpy)** - Fundamental package for scientific computing with Python.

---

## Memory & Storage

- **[MemDocs](https://pypi.org/project/memdocs/)** - Long-term memory system for AI agents. Provides persistent context across sessions.
- **[Redis Server](https://github.com/redis/redis)** - Open source in-memory data structure store. Redis 8.4+ provides the foundation for our memory subsystem with built-in modules:
  - **RediSearch** - Full-text search and secondary indexing
  - **RedisJSON** - Native JSON data type support
  - **RedisTimeSeries** - Time series data management
  - **RedisBloom** - Probabilistic data structures
  - **VectorSet** - Vector similarity search
- **[redis-py](https://github.com/redis/redis-py)** - Official Python client for Redis. Connects our application to Redis Server.

---

## Web Framework & API

- **[FastAPI](https://github.com/tiangolo/fastapi)** - Modern, fast web framework for building APIs with Python. Powers our backend API.
- **[Uvicorn](https://github.com/encode/uvicorn)** - Lightning-fast ASGI server. Runs our FastAPI applications.
- **[Starlette](https://github.com/encode/starlette)** - Lightweight ASGI framework/toolkit. Foundation of FastAPI.
- **[HTTPX](https://github.com/encode/httpx)** - Next generation HTTP client for Python. Used in our test suite.

---

## Security & Authentication

- **[bcrypt](https://github.com/pyca/bcrypt/)** - Modern password hashing for your software and your servers.
- **[PyJWT](https://github.com/jpadilla/pyjwt)** - JSON Web Token implementation in Python. Used for authentication tokens.
- **[cryptography](https://github.com/pyca/cryptography)** - Python cryptography library. Required by PyJWT for advanced algorithms.
- **[marshmallow](https://github.com/marshmallow-code/marshmallow)** - Object serialization/deserialization library. Used for secure data validation.

---

## Observability & Telemetry

- **[OpenTelemetry API](https://github.com/open-telemetry/opentelemetry-python)** - OpenTelemetry Python API. Provides vendor-agnostic telemetry.
- **[OpenTelemetry SDK](https://github.com/open-telemetry/opentelemetry-python)** - OpenTelemetry Python SDK. Core implementation of telemetry.
- **[OpenTelemetry OTLP Exporter](https://github.com/open-telemetry/opentelemetry-python)** - OTLP protocol exporter for OpenTelemetry.

---

## Developer Tools

### Code Quality

- **[Black](https://github.com/psf/black)** - The uncompromising Python code formatter. Keeps our code consistent.
- **[Ruff](https://github.com/astral-sh/ruff)** - An extremely fast Python linter, written in Rust. Replaces dozens of linting tools.
- **[mypy](https://github.com/python/mypy)** - Static type checker for Python. Catches type errors before runtime.
- **[Bandit](https://github.com/PyCQA/bandit)** - Security linter for Python. Finds common security issues.
- **[pre-commit](https://github.com/pre-commit/pre-commit)** - Framework for managing git pre-commit hooks. Enforces quality standards.

### Testing

- **[pytest](https://github.com/pytest-dev/pytest)** - Python testing framework. Makes writing tests simple and scalable.
- **[pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)** - Pytest plugin for testing asyncio code.
- **[pytest-cov](https://github.com/pytest-dev/pytest-cov)** - Coverage plugin for pytest. Tracks test coverage.
- **[pytest-xdist](https://github.com/pytest-dev/pytest-xdist)** - Parallel test execution for pytest. Makes test runs 4-8x faster.
- **[pytest-testmon](https://github.com/tarpas/pytest-testmon)** - Selects tests affected by recent changes. Speeds up development.
- **[pytest-picked](https://github.com/anapaulagomes/pytest-picked)** - Runs tests related to unstaged files. Perfect for rapid iteration.
- **[coverage.py](https://github.com/nedbat/coveragepy)** - Code coverage measurement for Python.

---

## Documentation

- **[MkDocs](https://github.com/mkdocs/mkdocs)** - Static site generator for project documentation. Powers our docs site.
- **[Material for MkDocs](https://github.com/squidfunk/mkdocs-material)** - Beautiful, modern theme for MkDocs.
- **[mkdocstrings](https://github.com/mkdocstrings/mkdocstrings)** - Automatic documentation from docstrings.
- **[mkdocs-with-pdf](https://github.com/orzih/mkdocs-with-pdf)** - Generates PDF and ePub from MkDocs documentation.
- **[PyMdown Extensions](https://github.com/facelessuser/pymdown-extensions)** - Extensions for Python Markdown.

---

## Editor Integration

- **[pygls](https://github.com/openlawlibrary/pygls)** - Pythonic Language Server Protocol implementation. Powers our LSP server.
- **[lsprotocol](https://github.com/microsoft/lsprotocol)** - Types and classes for Language Server Protocol.

---

## Platform Compatibility

- **[colorama](https://github.com/tartley/colorama)** - Cross-platform colored terminal text. Makes Windows terminals beautiful.

---

## Document Processing

- **[python-docx](https://github.com/python-openxml/python-docx)** - Creates and updates Microsoft Word (.docx) files. Used in document generation workflows.

---

## Special Thanks

We extend our deepest gratitude to:

### Major Frameworks & Standards

- **[Python Software Foundation](https://www.python.org/)** - For creating and maintaining the Python programming language.
- **[Anthropic](https://www.anthropic.com/)** - For Claude AI and the Model Context Protocol (MCP) specification.
- **[Redis Ltd.](https://redis.io/)** - For Redis 8.4 Open Source with RediSearch, RedisJSON, RedisTimeSeries, RedisBloom, and VectorSet modules.
- **[OpenAI](https://openai.com/)** - For pioneering work in large language models and API standards.
- **[The Rust Foundation](https://foundation.rust-lang.org/)** - For Rust, which powers Ruff and many performance-critical tools.

### Community Projects

- **[PyPI](https://pypi.org/)** - The Python Package Index, making package distribution effortless.
- **[GitHub](https://github.com/)** - For hosting our repository and enabling collaboration.
- **[Read the Docs](https://readthedocs.org/)** - For free documentation hosting for open source projects.

### Individual Contributors

We are grateful to all contributors who have submitted issues, pull requests, documentation improvements, and bug reports. Your contributions make this project better every day.

- See [CONTRIBUTORS.md](CONTRIBUTORS.md) for a full list of project contributors.

---

## Contributing Acknowledgements

If you contribute to this project and use open source libraries, please update this file to include proper attribution. Follow these guidelines:

1. **Add the library** to the appropriate section above
2. **Include a link** to the project's homepage or GitHub repository
3. **Provide a brief description** (1-2 sentences) of what the library does and how we use it
4. **Verify the license** is compatible with Apache 2.0 (see [LICENSE](LICENSE))

### How to Add an Acknowledgement

When adding a new dependency:

```bash
# 1. Add to pyproject.toml (already done when you installed it)

# 2. Add to this ACKNOWLEDGEMENTS.md file
# Format:
# - **[Project Name](https://github.com/org/repo)** - Brief description of what it does and how we use it.

# 3. Verify license compatibility
pip-licenses --from=mixed --format=markdown > licenses.md
```

---

## License Compatibility

All dependencies listed here are compatible with the Apache License 2.0 under which Attune AI is distributed. Common compatible licenses include:

- MIT License
- Apache License 2.0
- BSD Licenses (2-Clause, 3-Clause)
- Python Software Foundation License
- ISC License

For detailed license information on each dependency, run:

```bash
pip install pip-licenses
pip-licenses --from=mixed --format=markdown
```

---

## Questions?

If you notice a missing attribution or have questions about licensing:

- **Open an issue:** [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
- **Email us:** admin@smartaimemory.com

---

**Last Updated:** February 5, 2026
**Attune AI Version:** 2.3.4

---

*"If I have seen further, it is by standing on the shoulders of giants."* — Isaac Newton

Thank you to everyone who contributes to open source software. Your generosity makes projects like this possible.
