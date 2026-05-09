---
type: faq
name: getattrmodule-name-none-at-call-site-is-the-clean-degradation
tags: [imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about getattr(module, "name", None) at call site is the clean degradation pattern for optional SDK surface?

## Answer

in 6.2.0 we wired three features (`list_subagents`, `get_subagent_messages`, `TaskBudget`, `ThinkingConfigAdaptive`) that only exist in newer claude-agent-sdk versions but kept the dep floor at `>=0.1.60` rather than `>=0.1.63` so older installs degrade cleanly. Pattern: ```python list_fn = getattr(claude_agent_sdk, "list_subagents", None) if list_fn is None:     return {}  # older SDK — no-op gracefully return list_fn(session_id) ``` Superior to both module-level `from X import name` (older SDK → ImportError crashes the whole module) and try/except around every use (repetitive, scatters the fallback logic). Use `getattr` probes when the feature is optional and the SDK may not expose it; reserve try/except for when the feature is definitely available but the call itself may fail at runtime.

```
list_subagents
```

## Related Topics
- **Error**: Detailed error: `getattr(module, "name", None)` at call site is the
  clean degradation pattern for optional SDK surface
