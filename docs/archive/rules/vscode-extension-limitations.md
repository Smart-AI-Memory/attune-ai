# VSCode Extension Limitations

> **Archived 2026-07-04** (rules-corpus-jit): was already marked
> archived in-body; `vscode-extension/` no longer exists.

**Version:** 1.0
**Created:** January 24, 2026
**Status:** Archived — `vscode-extension/` directory no longer
exists in this repo. Kept for historical reference.
**Source:** Session evaluation - debugging dashboard button behavior

---

## Claude Code Extension: No API for Existing Conversations

### The Limitation

The Claude Code VSCode extension does not expose an API to send messages to an existing conversation from external code (e.g., webview panels, other extensions).

### Impact

**Dashboard buttons will always create new conversations** when they try to open Claude Code and send a command.

This affects any command that relies on conversation context:
- `/learning` - Needs current session history to evaluate
- `/context` - May need current session state
- Any command that references "this conversation" or "above"

### Technical Details

```typescript
// These commands all create NEW conversations:
await vscode.commands.executeCommand('claude-vscode.editor.open');   // New tab
await vscode.commands.executeCommand('claude-vscode.sidebar.open');  // New sidebar chat

// There is NO command like:
// await vscode.commands.executeCommand('claude-vscode.sendMessage', message);
// await vscode.commands.executeCommand('claude-vscode.appendToCurrentChat', text);
```

### Affected Code

- `vscode-extension/src/extension.ts` - `openHubInClaudeCode()` function
- `vscode-extension/src/panels/EmpathyDashboardPanel.ts` - `_openClaudeCodeWithCommand()` method

### Resolution

**For context-dependent commands:**
1. Remove dashboard buttons that require conversation context
2. Instruct users to type commands directly in their Claude Code chat
3. Use session-end hooks for automatic evaluation (e.g., `evaluate_session.py`)

**For context-independent commands:**
Dashboard buttons can still work for commands that don't need conversation history:
- `/testing "run tests"` - Standalone action
- `/dev "commit"` - Standalone action
- `/release "prep"` - Standalone action

### Commands Removed from Dashboard

| Command | Reason | Alternative |
|---------|--------|-------------|
| `/learning` | Requires session history | Type directly in chat |

### User Guidance

When users need to use context-dependent commands:

> "Type `/learning` directly in your Claude Code chat to evaluate this session.
> Dashboard buttons open new conversations and cannot access your current chat history."

### Future Considerations

If Anthropic adds an API to send messages to existing conversations, this limitation can be revisited. Monitor:
- [Claude Code VSCode Extension docs](https://code.claude.com/docs/en/vs-code)
- [Claude Code GitHub issues](https://github.com/anthropics/claude-code)

---

## Related Files

- [learning.md](../../commands/learning.md) - Learning hub command (works when typed)
- [EmpathyDashboardPanel.ts](../../../vscode-extension/src/panels/EmpathyDashboardPanel.ts) - Dashboard implementation
- [extension.ts](../../../vscode-extension/src/extension.ts) - Extension commands
