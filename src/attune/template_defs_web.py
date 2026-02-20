"""Web and agent template definitions for Attune AI.

Contains the python-fastapi and python-agent template definitions
used by the template engine to scaffold new projects.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

PYTHON_FASTAPI_TEMPLATE: dict[str, Any] = {
    "name": "Python FastAPI",
    "description": "FastAPI web service with Empathy integration",
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
    cheap: "claude-3-haiku-20240307"
    capable: "claude-sonnet-4-20250514"
    premium: "claude-opus-4-20250514"

claude_sync:
  enabled: true
  output_dir: ".claude/rules/empathy"

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
from attune import EmpathyOS, load_config

app = FastAPI(
    title="{{project_name}}",
    description="FastAPI service powered by Attune AI",
    version="0.1.0"
)

# Initialize Empathy (optional - for AI features)
try:
    config = load_config()
    empathy = EmpathyOS(config)
except Exception:
    empathy = None


@app.get("/")
async def root():
    return {
        "message": "Welcome to {{project_name}}",
        "empathy_enabled": empathy is not None
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
    "empathy-framework>=2.3",
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
# Start-of-day briefing
empathy morning

# Pre-commit checks
empathy ship

# Run health checks
empathy health
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

- `empathy morning` - Daily briefing
- `empathy ship` - Pre-commit checks
- `empathy health` - Code health

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
    "description": "AI agent project with Empathy for pattern learning",
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
    cheap: "claude-3-haiku-20240307"
    capable: "claude-sonnet-4-20250514"
    premium: "claude-opus-4-20250514"
  task_overrides:
    summarize: "cheap"
    classify: "cheap"
    generate_code: "capable"
    architectural_decision: "premium"
    coordinate: "premium"

claude_sync:
  enabled: true
  output_dir: ".claude/rules/empathy"
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

from attune import EmpathyOS, load_config
from attune.llm.core import EmpathyLLM
import os


class {{project_name_class}}Agent:
    """
    AI Agent with Empathy-powered learning and memory.
    """

    def __init__(self):
        self.config = load_config()
        self.empathy = EmpathyOS(self.config)

        # Initialize LLM with model routing
        self.llm = EmpathyLLM(
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
        return self.empathy.pattern_library.list_patterns()


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
    "empathy-framework>=2.3",
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
# Learn patterns from git history
empathy learn --analyze 50

# Sync patterns to Claude Code
empathy sync-claude

# Morning briefing
empathy morning
```
""",
        ".claude/CLAUDE.md": """# {{project_name}} - AI Agent Rules

## Project Context

AI agent with Attune AI for pattern learning and memory.

## Agent Architecture

- `agent.py` - Main agent class with Empathy integration
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
