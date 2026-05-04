---
type: task
feature: memory
depth: task
generated_at: 2026-05-04T02:31:55.138987+00:00
source_hash: c45e8890bff96a3bad01adc0d5e2914aa9058b01f5e2914aa9058b01f5de8c8a1985c9b6fe4a7f0f
status: generated
---

# Work with memory

Use the memory module when you need to implement storage, retrieval, or security features for Attune AI's memory subsystem.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/memory/`
- Basic understanding of Redis configuration (if working with short-term memory)

## Steps

1. **Identify the memory component you need to modify.**
   The memory module has four main areas:
   - **Backends**: `MemoryBackend` and `SearchableMemoryBackend` protocols
   - **Claude integration**: Loading and managing CLAUDE.md files
   - **Redis configuration**: Short-term memory with Redis backends
   - **Control panel**: Web API for memory management

2. **Choose the appropriate entry point.**
   Based on your task, start with one of these functions:
   - `is_redis_available()` — Check Redis subsystem availability
   - `create_default_project_memory()` — Initialize CLAUDE.md files
   - `get_redis_memory()` — Create Redis memory instances
   - `run_api_server()` — Start the memory control panel

3. **Examine the existing implementation.**
   Read the function's docstring, parameters, and return type. Check how it handles errors and what patterns it follows for logging and configuration.

4. **Implement your changes.**
   Maintain consistency with the existing codebase:
   - Use the same error handling patterns
   - Follow established naming conventions
   - Preserve the function's single responsibility

5. **Verify your implementation.**
   Run targeted tests to ensure your changes work correctly:
   ```bash
   pytest -k "memory"
   ```

## Verify success

Your changes work correctly when:
- All memory-related tests pass
- The function returns the expected type and format
- Error conditions are handled gracefully
- No regressions appear in dependent functionality

## Key files to know

- `src/attune/memory/__init__.py` — Module entry points and Redis availability checking
- `src/attune/memory/claude_memory.py` — CLAUDE.md file management
- `src/attune/memory/config.py` — Redis configuration and connection handling
- `src/attune/memory/control_panel_api.py` — HTTP API for memory management
