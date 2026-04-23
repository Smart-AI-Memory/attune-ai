---
type: task
feature: plugin
depth: task
generated_at: 2026-04-23T03:32:46.578539+00:00
source_hash: 45eadb2e7f205941c8bfaceec972a8cbf3a780ce8b0ca2ce66b2868c4058b340
status: generated
---

# Work with plugin

Use the plugin system when you need to customize Claude Code's behavior with automatic hooks, security validation, or session initialization.

## Prerequisites

- Access to the project source code
- Familiarity with the plugin architecture and hook system
- Understanding of which hook triggers when (session start, post-tool use, etc.)

## Steps

1. **Identify the hook you need to modify**

   Determine which hook handles your use case:
   - **format_on_save.py** — Auto-format Python files after Write/Edit operations
   - **help_freshness_check.py** — Check template freshness when sessions start
   - **help_on_error.py** — Suggest help content when Bash commands fail
   - **help_post_commit.py** — Maintain help templates after git commits
   - **security_guard.py** — Validate commands and file paths against security policies
   - **welcome.py** — Display session startup messages

2. **Examine the current implementation**

   Open the relevant hook file and review:
   - The `main()` function's parameters and return type
   - How it processes input (stdin, context dict, etc.)
   - What security validations apply
   - How errors are handled

3. **Modify the hook behavior**

   Edit the function following the existing code patterns:
   - Use the same parameter validation style
   - Match the error handling approach (return tuples for validation functions)
   - Preserve the expected return format
   - Keep security checks intact

4. **Test your changes**

   Run the plugin-specific tests to verify functionality:
   ```bash
   pytest -k "plugin"
   ```

## Verify success

- Your hook triggers at the expected time (session start, post-tool use, etc.)
- Security validations still block prohibited operations
- Error messages appear correctly when commands fail
- The plugin integrates seamlessly with Claude Code's workflow

## Key plugin files

- `plugin/hooks/format_on_save.py` — Python file formatting
- `plugin/hooks/help_freshness_check.py` — Template freshness validation
- `plugin/hooks/help_on_error.py` — Context-aware help suggestions
- `plugin/hooks/help_post_commit.py` — Help maintenance automation
- `plugin/hooks/security_guard.py` — Command and path validation
- `plugin/hooks/welcome.py` — Session initialization
