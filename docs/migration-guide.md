---
description: Migration Guide for Attune AI package consolidation and architectural changes
---

# Migration Guide: Attune AI

## Package Consolidation (v2.6.4+ → v3.0.0)

### Overview

Attune AI is consolidating from dual packages (`attune_llm/` and `src/attune/`) into a single unified `attune` package. Backward-compatible shims are provided until **v3.0.0**.

### Timeline

- **v2.6.4+**: Shims active, deprecation warnings issued
- **v3.0.0**: Shims removed, `attune_llm/` deleted

### Migration Steps

#### 1. Update Imports

**Before (deprecated):**

```python
from attune_llm.core import EmpathyLLM
from attune_llm.routing import ModelRouter
from attune_llm.hooks import HookRegistry
```

**After (recommended):**

```python
from attune.llm import EmpathyLLM
from attune.routing import ModelRouter
from attune.hooks import HookRegistry
```

#### 2. Update Workflow Imports

**Before:**

```python
from attune_llm.workflows import BugPredictionWorkflow
```

**After:**

```python
from attune.workflows import BugPredictionWorkflow
```

#### 3. Find and Replace

```bash
# Find all deprecated imports
grep -r "from attune_llm" . --include="*.py"
grep -r "import attune_llm" . --include="*.py"

# Replace with new imports
sed -i 's/from attune_llm\./from attune./g' **/*.py
sed -i 's/import attune_llm\./import attune./g' **/*.py
```

### Import Mapping

| Old Import | New Import |
|------------|------------|
| `attune_llm.core` | `attune.llm.core` |
| `attune_llm.providers` | `attune.llm.providers` |
| `attune_llm.state` | `attune.llm.state` |
| `attune_llm.levels` | `attune.llm.levels` |
| `attune_llm.routing` | `attune.routing` |
| `attune_llm.config` | `attune.config` |
| `attune_llm.hooks` | `attune.hooks` |
| `attune_llm.learning` | `attune.learning` |
| `attune_llm.context` | `attune.context` |
| `attune_llm.agents_md` | `attune.agents_md` |
| `attune_llm.commands` | `attune.commands` |
| `attune_llm.workflows` | `attune.workflows` |
| `attune_llm.agent_factory` | `attune.agent_factory` |

### Workflow Composition (v2.6.4+)

All workflows now support composition via `WorkflowContext`:

```python
from attune.workflows import SecurityAuditWorkflow

# Using default context (recommended)
workflow = SecurityAuditWorkflow()
context = SecurityAuditWorkflow.default_context()

# Access services
context.prompt  # PromptService
context.parsing  # ParsingService
```

### Deprecation Warnings

If you see warnings like:

```
DeprecationWarning: attune_llm.core is deprecated. Use attune.llm.core instead.
This module will be removed in attune-ai v3.0.0.
```

Update your imports following the mapping table above.

---

## Migration Guide: Attune AI 4.7.0 (Legacy)

> **Attribution**: Version 4.7.0 adds architectural patterns inspired by [everything-claude-code](https://github.com/affaan-m/everything-claude-code) by Affaan Mustafa (MIT License). These complement the Attune AI's existing learning capabilities.

## What's New in 4.7.0

| Feature | Description | Source |
|---------|-------------|--------|
| Hook System | Event-driven automation | everything-claude-code |
| Markdown Agents | Portable agent definitions | everything-claude-code |
| Context Management | State preservation through compaction | everything-claude-code |
| Session Learning | Pattern extraction from interactions | everything-claude-code |

**Existing features enhanced** (not replaced): Code inspection learning, memory system, empathy levels.

## Quick Start

### 1. Update

```bash
pip install --upgrade empathy-llm-toolkit>=4.7.0
```

### 2. Configuration (Optional Additions)

```yaml
# empathy.config.yaml - add to existing config
hooks:
  enabled: true

learning:
  enabled: true
  auto_evaluate: true
```

### 3. Verify

```python
from attune_llm.hooks import HookRegistry
from attune_llm.agents_md import AgentRegistry
from attune_llm.context import ContextManager
from attune_llm.learning import SessionEvaluator

print("Migration successful!")
```

## Learning Systems

### Code Inspection Learning (Existing)
- Extracts patterns from code analysis
- Storage: `patterns/inspection/`
- Unchanged in 4.7.0

### Session Learning (New)
- Extracts patterns from user interactions
- Storage: `.attune/learned_skills/`
- Complements existing system

## New Imports

```python
# Hooks
from attune_llm.hooks import HookRegistry
from attune_llm.hooks.config import HookEvent

# Markdown Agents
from attune_llm.agents_md import AgentRegistry

# Context Management
from attune_llm.context import ContextManager, CompactState

# Session Learning
from attune_llm.learning import SessionEvaluator, PatternExtractor
```

## Directory Structure

```
project/
├── .claude/commands/       # NEW: Slash commands
├── .attune/
│   ├── compact_states/     # NEW: Context preservation
│   └── learned_skills/     # NEW: Session patterns
├── agents_md/              # NEW: Markdown agents
├── patterns/inspection/    # EXISTING: Code patterns
└── empathy.config.yaml
```

## Backward Compatibility

All existing features continue to work unchanged. New features are additive.

## Full Documentation

- [Hooks](hooks.md)
- [Markdown Agents](markdown-agents.md)
- [Context Management](context-management.md)
- [Continuous Learning](continuous-learning.md)
