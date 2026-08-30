---
type: troubleshooting
name: elicitation-forms-troubleshooting
feature: elicitation-forms
depth: troubleshooting
generated_at: 2026-08-29T23:25:57.407014+00:00
source_hash: adc929d111b4cf4bf48479bf6b325ab34d6f63740017d7fc0df1383da12ed22e
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
