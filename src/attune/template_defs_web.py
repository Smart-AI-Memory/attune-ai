"""Web and agent template definitions for Attune AI.

Contains the python-fastapi and python-agent template definitions
used by the template engine to scaffold new projects.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

PYTHON_FASTAPI_TEMPLATE: dict[str, Any] = {
    "name": "Python FastAPI",
    "description": "FastAPI web service with Attune integration",
    "files": {
        "attune.config.yml": """# Attune AI Configuration
# Template: python-fastapi

user_id: "{{project_name}}"
target_level: 4
confidence_threshold: 0.75

model_routing:
  enabled: true
  provider: "anthropic"
  models:
    cheap: "claude-haiku-4-5"
    capable: "claude-sonnet-5"
    premium: "claude-fable-5"

claude_sync:
  enabled: true
  output_dir: ".claude/rules/attune"

persistence_enabled: true
persistence_backend: "sqlite"
persistence_path: ".attune"
metrics_enabled: true

health:
  checks:
    lint: true
    format: true
    types: true
    security: true
""",
        "{{project_name}}/__init__.py": '''"""
{{project_name}} - FastAPI service with Attune AI
"""

__version__ = "0.1.0"
''',
        "{{project_name}}/main.py": '''"""
FastAPI application for {{project_name}}
"""

from fastapi import FastAPI
from attune import AttuneOS, load_config

app = FastAPI(
    title="{{project_name}}",
    description="FastAPI service powered by Attune AI",
    version="0.1.0"
)

# Initialize Attune (optional - for AI features)
try:
    config = load_config()
    attune = AttuneOS(config)
except Exception:  # noqa: BLE001
    # INTENTIONAL: Attune is optional - app must start even if config fails
    import logging
    logging.getLogger(__name__).warning("Attune initialization failed, running without AI features")
    attune = None


@app.get("/")
async def root():
    return {
        "message": "Welcome to {{project_name}}",
        "attune_enabled": attune is not None
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
''',
        "pyproject.toml": """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{project_name}}"
version = "0.1.0"
description = "FastAPI service powered by Attune AI"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
    "attune-ai>=5.0",
]

[project.scripts]
{{project_name}} = "{{project_name}}.main:app"
""",
        "README.md": """# {{project_name}}

FastAPI service powered by Attune AI.

## Installation

```bash
pip install -e .
```

## Running

```bash
uvicorn {{project_name}}.main:app --reload
```

## Development

```bash
# Pre-commit checks
attune workflow run ship

# Run health checks
attune doctor

# Code review
attune workflow run code-review
```

## API

- `GET /` - Root endpoint
- `GET /health` - Health check
""",
        ".claude/CLAUDE.md": """# {{project_name}} - Claude Code Rules

## Project Context

FastAPI web service with Attune AI integration.

## API Structure

- `main.py` - FastAPI app definition
- Standard RESTful patterns

## Commands

- `attune workflow run ship` - Pre-commit checks
- `attune doctor` - Environment health check
- `attune workflow run code-review` - Code review

## Patterns

@patterns/debugging.json
@patterns/security.json
""",
        ".gitignore": """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Attune AI
.attune/
patterns/sensitive/

# Environment
.env
.venv/

# IDE
.vscode/
.idea/
""",
    },
}

PYTHON_AGENT_TEMPLATE: dict[str, Any] = {
    "name": "Python AI Agent",
    "description": "AI agent project with Attune for pattern learning",
    "files": {
        "attune.config.yml": """# Attune AI Configuration
# Template: python-agent

user_id: "{{project_name}}_agent"
target_level: 5  # Systems thinking for agents
confidence_threshold: 0.8

model_routing:
  enabled: true
  provider: "anthropic"
  models:
    cheap: "claude-haiku-4-5"
    capable: "claude-sonnet-5"
    premium: "claude-fable-5"
  task_overrides:
    summarize: "cheap"
    classify: "cheap"
    generate_code: "capable"
    architectural_decision: "premium"
    coordinate: "premium"

claude_sync:
  enabled: true
  output_dir: ".claude/rules/attune"
  sync_patterns:
    debugging: true
    security: true
    inspection: true

persistence_enabled: true
persistence_backend: "sqlite"
persistence_path: ".attune"
metrics_enabled: true

# Agent-specific settings
pattern_library_enabled: true
pattern_sharing: true
""",
        "{{project_name}}/__init__.py": '''"""
{{project_name}} - AI Agent powered by Attune AI
"""

__version__ = "0.1.0"
''',
        "{{project_name}}/agent.py": '''"""
AI Agent implementation for {{project_name}}
"""

from attune import AttuneOS, load_config
from attune.llm.core import AttuneLLM
import os


class {{project_name_class}}Agent:
    """
    AI Agent with Attune-powered learning and memory.
    """

    def __init__(self):
        self.config = load_config()
        self.attune = AttuneOS(self.config)

        # Initialize LLM with model routing
        self.llm = AttuneLLM(
            provider="anthropic",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    async def process(self, user_input: str, context: dict = None) -> str:
        """Process user input and return response."""
        response = await self.llm.interact(
            user_id=self.config.user_id,
            user_input=user_input,
            context=context or {}
        )
        return response.get("response", "")

    def get_patterns(self) -> list:
        """Get learned patterns."""
        return self.attune.pattern_library.list_patterns()


async def main():
    """Example usage."""
    agent = {{project_name_class}}Agent()
    response = await agent.process("Hello, what can you help me with?")
    print(response)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
''',
        "pyproject.toml": """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{project_name}}"
version = "0.1.0"
description = "AI Agent powered by Attune AI"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "attune-ai>=5.0",
    "anthropic>=0.18",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]
""",
        "README.md": """# {{project_name}}

AI Agent powered by Attune AI with pattern learning.

## Setup

1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Set API key:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   ```

3. Run agent:
   ```bash
   python -m {{project_name}}.agent
   ```

## Features

- Model routing for cost optimization
- Pattern learning from interactions
- Claude Code integration

## Development

```bash
# Pre-commit checks
attune workflow run ship

# Code review
attune workflow run code-review

# Environment health check
attune doctor
```
""",
        ".claude/CLAUDE.md": """# {{project_name}} - AI Agent Rules

## Project Context

AI agent with Attune AI for pattern learning and memory.

## Agent Architecture

- `agent.py` - Main agent class with Attune integration
- Model routing: Haiku for simple, Sonnet for code, Opus for decisions

## Pattern Storage

Patterns are stored in `patterns/` and synced to Claude Code.

@patterns/debugging.json
@patterns/security.json
@patterns/inspection.json
""",
        ".gitignore": """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Attune AI
.attune/
patterns/sensitive/

# Environment
.env
.venv/

# IDE
.vscode/
.idea/
""",
        "tests/__init__.py": "",
        "tests/test_agent.py": '''"""Tests for {{project_name}} agent."""

import pytest
from {{project_name}}.agent import {{project_name_class}}Agent


def test_agent_init():
    """Test agent initialization."""
    # Note: This will require config file
    # agent = {{project_name_class}}Agent()
    # assert agent is not None
    pass
''',
    },
}
