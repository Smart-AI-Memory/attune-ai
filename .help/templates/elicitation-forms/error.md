---
type: error
name: elicitation-forms-error
feature: elicitation-forms
depth: error
generated_at: 2026-09-06T00:35:04.869548+00:00
source_hash: 9162a67905eb555cfdd3b260da2b35f34972ceed46c693d35319d40e7370db18
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

### A template cast fails on a slot, not on the form

`form_from_template` validates the declaration and the values in both
directions before it substitutes anything: a missing value, an extra
name, a declared-but-unused slot, or an undeclared `{placeholder}` in a
field each surface as their own problem line. Read the slot problems
first — the form-level validation only runs on a successfully cast
definition. An unknown template name lists every available template, so
a typo is a one-look fix.

### A `progress` form whose blocked items disagree with its options

The bridge enforces `set(blocked labels) == set(options)`; a mismatch
raises `FormValidationError`. The picker can never offer a non-existent
blocker or omit a real one.
