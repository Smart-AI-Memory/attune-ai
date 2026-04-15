---
type: comparison
feature: configuration
depth: comparison
generated_at: 2026-04-14T15:31:47.065970+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration: UnifiedAgentConfig vs BookProductionConfig

## Context

Attune AI offers two primary configuration approaches for different use cases. UnifiedAgentConfig serves as the central configuration system for all agents, while BookProductionConfig provides specialized settings for book production workflows with backward compatibility.

## Feature comparison

| Feature | UnifiedAgentConfig | BookProductionConfig |
|---------|-------------------|---------------------|
| **Scope** | All agent types and workflows | Book production workflows only |
| **Role normalization** | Built-in role string validation | Inherits from UnifiedAgentConfig |
| **Model configuration** | Direct model_id access | Backward-compatible model property |
| **Parameter access** | Native dataclass fields | Legacy property wrappers |
| **Environment integration** | Full ATTUNE_/EMPATHY_ prefix support | Standard env override support |
| **Workflow modes** | All WorkflowMode options | Optimized for book production |
| **Configuration loading** | ConfigLoader with path discovery | Created via for_book_production() |

## Performance characteristics

UnifiedAgentConfig loads ~2x faster for general workflows because it avoids the property wrapper overhead that BookProductionConfig uses for backward compatibility. However, BookProductionConfig provides seamless migration for existing book production code that expects legacy field names like `model` instead of `model_id`.

## Use UnifiedAgentConfig when...

- Building new agents or workflows from scratch
- You need the full range of WorkflowMode options
- Performance is critical and you don't need legacy compatibility
- You're integrating with multiple agent types beyond book production
- You want direct access to configuration fields without property wrappers

## Use BookProductionConfig when...

- Migrating existing book production code that expects legacy field names
- You specifically work with book production workflows
- You need the `model`, `max_tokens`, `temperature` properties for compatibility
- Your codebase already references BookProductionConfig patterns

## Configuration loading patterns

Both configurations use the same underlying ConfigLoader system:

```python
# For general use
config = load_unified_config()
agent_config = UnifiedAgentConfig(...)

# For book production
config = load_unified_config()
book_config = config.for_book_production()
```

Environment variables work identically for both, with `ATTUNE_` prefix taking precedence over `EMPATHY_` fallback.

## Recommendation

**Use UnifiedAgentConfig for new development.** It's the primary configuration system with better performance and cleaner API design. BookProductionConfig exists primarily for backward compatibility and should only be used when migrating legacy book production code or when you specifically need its compatibility properties.
