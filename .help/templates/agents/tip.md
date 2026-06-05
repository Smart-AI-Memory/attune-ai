---
type: tip
name: agents-tip
feature: agents
depth: tip
generated_at: 2026-06-04T23:45:26.764952+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Tip: Working effectively with agents

Use the lazy-import getter functions — `get_langchain_adapter()`, `get_autogen_adapter()`, `get_haystack_adapter()`, and `get_langgraph_adapter()` — instead of importing adapter classes directly. These functions defer the underlying framework import until the moment you need it, so frameworks you don't use don't slow down startup or pollute your environment.

**Why it's worth it:** Each adapter's framework dependency (LangChain, AutoGen, Haystack, LangGraph) is heavy. Importing them eagerly at module load couples your code to every framework at once, even when you're only using one.

**Tradeoff:** The getter functions return a framework-specific adapter instance, not a raw class, so you can't subclass the result directly. If you need a custom adapter subclass, instantiate the class (for example, `LangChainAdapter`) explicitly — but accept that you then own the import.

If you need to wrap an existing wizard quickly without building a full adapter, `wrap_wizard()` is the fastest path: it returns a `WizardAgent` ready for `invoke()` or `stream()` calls without any framework configuration.

## Source files

- `src/attune/agent_factory/adapters/__init__.py`
- `src/attune/agent_factory/adapters/wizard_adapter.py`

**Tags:** `agents`, `ai`, `release`
