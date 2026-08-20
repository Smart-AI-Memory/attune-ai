---
description: Markdown Agents: Define agents using simple markdown files with YAML frontmatter.
---

# Markdown Agents

Define agents using simple markdown files with YAML frontmatter.

## Overview

The Attune AI supports defining agents as markdown files, making them:

- **Human-readable**: Easy to understand and review
- **Portable**: Share agents as simple text files
- **Version-controlled**: Track changes with git
- **Customizable**: Override any configuration option

## Quick Start

### 1. Create an Agent File

```markdown
---
name: code-reviewer
description: Expert code review specialist
role: reviewer
model: capable
tools: Read, Grep, Glob
empathy_level: 4
pattern_learning: true
---

# Code Review Agent

You are an expert code reviewer focused on:

1. **Code Quality**: Identify bugs, anti-patterns, and improvements
2. **Security**: Flag potential vulnerabilities
3. **Performance**: Suggest optimizations
4. **Maintainability**: Ensure readable, documented code

## Review Process

1. Read the file(s) to review
2. Analyze structure and patterns
3. Check for issues
4. Provide actionable feedback
```

### 2. Load the Agent

```python
from attune.agents_md import AgentRegistry

registry = AgentRegistry.get_instance()
registry.load_from_directory("agents/")

reviewer = registry.get("code-reviewer")
print(reviewer.description)
```

## File Format

### YAML Frontmatter

Required and optional fields:

```yaml
---
# Required
name: agent-name  # Unique identifier

# Recommended
description: What this agent does
role: architect|reviewer|security|empathy|utility
model: cheap|capable|premium  # or haiku|sonnet|opus

# Optional
tools: Read, Grep, Glob, Bash  # Comma-separated or list
empathy_level: 1-5  # Default: 4
pattern_learning: true|false  # Default: true
memory_enabled: true|false  # Default: true
temperature: 0.7  # 0.0-1.0
max_tokens: 4096
timeout: 120  # seconds
interaction_mode: standard|socratic
---
```

### Markdown Body

The body becomes the agent's system prompt:

```markdown
# Agent Title

Introduction paragraph explaining the agent's role.

## Capabilities

- Capability 1
- Capability 2

## Guidelines

1. First guideline
2. Second guideline

## Examples

```python
# Example code
```
```

## Model Tiers

| Tier | Aliases | Use Case |
|------|---------|----------|
| `cheap` | `haiku` | Fast, simple tasks |
| `capable` | `sonnet` | Balanced performance |
| `premium` | `opus` | Complex reasoning |

## Agent Roles

| Role | Description |
|------|-------------|
| `architect` | System design and planning |
| `reviewer` | Code review and analysis |
| `security` | Security analysis |
| `empathy` | User interaction specialist |
| `utility` | General-purpose tasks |

## Built-in Agents

The framework includes these agents in `agents_md/`:

| Agent | Role | Description |
|-------|------|-------------|
| `architect` | architect | Software architecture specialist |
| `code-reviewer` | reviewer | Code quality review |
| `security-reviewer` | security | Security vulnerability analysis |
| `empathy-specialist` | empathy | User empathy calibration |
| `socratic-architect` | architect | Questioning-based design |
| `socratic-reviewer` | reviewer | Questioning-based review |

## Loading Agents

### From Directory

```python
from attune.agents_md import AgentRegistry

registry = AgentRegistry.get_instance()
count = registry.load_from_directory("agents/", recursive=True)
print(f"Loaded {count} agents")
```

### From Single File

```python
config = registry.load_from_file("agents/custom-agent.md")
```

### Programmatic Registration

```python
from attune.config.agent_config import UnifiedAgentConfig

config = UnifiedAgentConfig(
    name="my-agent",
    description="Custom agent",
    system_prompt="You are a helpful assistant.",
)
registry.register(config)
```

## Querying Agents

```python
# Get by name
agent = registry.get("architect")

# Get by role
reviewers = registry.get_by_role("reviewer")

# Get by empathy level
empathetic = registry.get_by_empathy_level(min_level=4)

# List all
for name in registry.list_agents():
    print(name)
```

## Validation

Validate agent files before loading:

```python
from attune.agents_md import AgentLoader

loader = AgentLoader()
errors = loader.validate_directory("agents/")

for file_path, file_errors in errors.items():
    print(f"{file_path}:")
    for error in file_errors:
        print(f"  - {error}")
```

## Socratic Agents

Enable questioning-based interaction:

```yaml
---
name: socratic-agent
interaction_mode: socratic
socratic_config:
  max_questions: 3
  question_style: clarifying
---
```

Socratic patterns:
- **Sequential Funnel**: Broad → narrow questions
- **Conditional Branching**: Different paths based on answers
- **Guided Discovery**: Lead user to insights
- **Confirmation**: Verify understanding

## Integration

### With Hooks

A `SessionStart` hook **script** under `attune/hooks/scripts/` can look
up an agent from the registry (Claude Code invokes it over the stdin /
exit-code contract — see [Hooks](hooks.md)):

```python
import json
import sys

payload = json.load(sys.stdin)
registry = AgentRegistry.get_instance()
agent = registry.get(payload.get("agent_name", "default"))
sys.exit(0)
```

## API Reference

### AgentRegistry

```python
class AgentRegistry:
    @classmethod
    def get_instance() -> AgentRegistry

    def register(config, overwrite=False) -> None
    def unregister(name) -> bool
    def get(name) -> UnifiedAgentConfig | None
    def get_required(name) -> UnifiedAgentConfig  # raises KeyError
    def has(name) -> bool
    def list_agents() -> list[str]
    def load_from_directory(directory, recursive=False) -> int
    def load_from_file(file_path) -> UnifiedAgentConfig
    def get_by_role(role) -> list[UnifiedAgentConfig]
    def get_by_empathy_level(min_level, max_level) -> list[UnifiedAgentConfig]
```

### AgentLoader

```python
class AgentLoader:
    def load(file_path) -> UnifiedAgentConfig
    def load_directory(directory, recursive=False) -> dict[str, UnifiedAgentConfig]
    def discover(directory, recursive=False) -> Iterator[UnifiedAgentConfig]
    def validate_directory(directory) -> dict[str, list[str]]
```

## See Also

- [Hooks](hooks.md) - Event-driven extensibility
- [CLI Reference](reference/cli-reference.md#slash-command-system) - Slash command system
