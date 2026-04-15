---
type: quickstart
feature: plugin
depth: quickstart
generated_at: 2026-04-14T15:23:44.852061+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Quickstart: plugin

Run a Claude Code plugin hook to see the system in action.

```bash
echo '{"tool": "write", "path": "test.py", "content": "def hello():\nprint(\"world\")"}' | python plugin/hooks/format_on_save.py
```

This triggers the post-tool-use Python formatting hook, which automatically formats any Python file after a Write or Edit operation.

## Set up and test a hook

1. **Run the format hook manually** using the command above. You'll see the hook process the JSON input and apply Python formatting rules to the file content.

2. **Check the security validator** by running a validation test:
   ```bash
   python -c "
   import sys
   sys.path.append('plugin')
   from hooks.security import main
   result = main({'tool': 'bash', 'command': 'ls -la'})
   print(result)
   "
   ```
   Expected output: `{'allowed': True}`

3. **Test the help system** by triggering the help-on-error hook:
   ```bash
   echo '{"tool": "bash", "command": "nonexistent-command", "exit_code": 127}' | python plugin/hooks/help_on_error.py
   ```
   The hook analyzes failed commands and suggests relevant help topics.

## Next steps

Configure the hooks in your MCP client to run automatically during Claude Code sessions.
