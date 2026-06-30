---
type: troubleshooting
name: elicitation-forms-troubleshooting
feature: elicitation-forms
depth: troubleshooting
generated_at: 2026-06-30T10:46:49.824408+00:00
source_hash: a92a686cbf5ee20f00434eb8333649a9fe60ca3b10acaec689f66904730ce1c4
status: generated
---

# Dynamic forms and the agent-to-user communication grammar

## Failure modes

### Rendering on a surface that has none

If a form is rendered to the widget surface but the client cannot post
back (`sendPrompt` unavailable), the submit button reports it and the
caller should fall back to `form_to_askuserquestion`. A rich widget needs
a widget-capable client; a plain terminal degrades to the menu fallback
by design.

### "Registered ≠ working until the server reboots"

A newly added construct or field reaches the live MCP server only after
the server restarts on the new version — the tool schema is loaded at
startup. Verify the live `elicitation_render_widget` schema actually
carries a new enum value before asserting the construct works end-to-end.

### A `progress` form whose blocked items disagree with its options

The bridge enforces `set(blocked labels) == set(options)`; a mismatch
raises `FormValidationError`. The picker can never offer a non-existent
blocker or omit a real one.
