---
type: task
feature: agents
depth: task
generated_at: 2026-05-04T02:33:05.990938+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Work with agents

Use Attune's agent system when you need to integrate AI agents across multiple frameworks (AutoGen, Haystack, LangChain) or implement agent state persistence and recovery.

## Prerequisites

- Access to the project source code
- Familiarity with the agent framework you want to integrate (AutoGen, Haystack, LangChain, or LangGraph)
- Understanding of your agent's configuration requirements

## Steps

1. **Choose your framework adapter.**
   Select the adapter that matches your AI framework:
   - Call `get_autogen_adapter()` for Microsoft AutoGen agents
   - Call `get_haystack_adapter()` for deepset Haystack pipelines
   - Call `get_langchain_adapter()` for LangChain chains
   - Call `get_langgraph_adapter()` for LangGraph nodes
   - Call `wrap_wizard()` to convert an existing wizard into an agent

2. **Configure your agent.**
   Create an `AgentConfig` object with your agent's role, capabilities, and model settings. Set the provider (like 'anthropic') and any required API keys when initializing the adapter.

3. **Create the agent instance.**
   Use your adapter's `create_agent()` method with your configuration. The adapter handles framework-specific initialization and wraps the underlying agent with Attune's standard interface.

4. **Implement agent operations.**
   Use the agent's `invoke()` method for single requests or `stream()` for real-time responses. Both methods accept string or dictionary input and optional context parameters.

5. **Add error handling and monitoring.**
   Wrap your agent operations with the provided decorators:
   - Use `@safe_agent_operation()` for error logging and recovery
   - Use `@retry_on_failure()` for automatic retries with exponential backoff
   - Use `@log_performance()` to monitor slow operations
   - Use `@with_cost_tracking()` to track API usage costs

6. **Test your integration.**
   Run tests with `pytest -k "agents"` to verify your agent works correctly with the Attune framework and doesn't break existing functionality.

## Verify success

Your agent integration is working when:
- The adapter's `is_available()` method returns `True`
- Your agent responds correctly to `invoke()` calls
- Error handling decorators catch and log exceptions appropriately
- Tests pass without regressions
