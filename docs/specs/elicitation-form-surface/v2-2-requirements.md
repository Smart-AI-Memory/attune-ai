# Elicitation v2 — Phase 2.2 (V2.2): the MCP elicitation renderer

Requirements for rendering the declarative artifact as a real MCP
`elicitation/create` request on the lead surface (D8), and validating the
structured response back through the v1 seam.

## Context

- D8 chose **MCP native elicitation** as the v2 lead surface — structured
  keyed return, native/portable, reuses `collect_form_response`.
- V2.1 extended the artifact with rich controls (number/date/textarea).
- The V2.0 PoC proved the transform; this phase productionizes it and
  wires the live emit path.

## Grounding (verify-first, confirmed against the installed SDK)

- `ServerSession.elicit_form(message, requestedSchema, related_request_id)
  -> ElicitResult` sends form-mode `elicitation/create`. `requestedSchema`
  is `dict[str, Any]`; `ElicitResult` is `{action: accept|decline|cancel,
  content: {field: value} | None}`.
- A tool handler reaches the live session via
  `Server.request_context` (`.session`, `.request_id`) — both available
  inside an in-flight `call_tool`.

## Goals

- **G1** `form_to_elicitation_schema(form)` — map every `QuestionType` to
  a valid elicitation `requestedSchema` (flat object of primitives).
- **G2** An `elicitation_ask` MCP tool that does the full server-side
  round-trip: build schema → `session.elicit_form(...)` → on `accept`,
  validate `content` via `collect_form_response`; on `decline`/`cancel`,
  return that cleanly. Graceful fallback when the client lacks the
  elicitation capability.
- **G3** Unit-tested transform (all 7 types) + handler (accept/decline/
  cancel + capability-error paths) with a mocked session. Live round-trip
  documented as needing an elicitation-capable client + a server restart.

## Type → schema mapping

| QuestionType | elicitation schema |
|---|---|
| single_select | `{type: string, enum: options}` |
| multi_select | `{type: array, items: {type: string, enum: options}, minItems if required}` |
| boolean | `{type: boolean}` |
| number | `{type: number, minimum?, maximum?}` |
| date | `{type: string, format: "date"}` |
| textarea / text_input | `{type: string, maxLength?}` |

Every property carries `title` (the question text), plus `description`
(help_text) and `default` when present. `required` lists the required
field ids.

## End state (acceptance)

- `form_to_elicitation_schema` in `attune.elicitation`, exported, covering
  all 7 types + constraints; 100% line+branch.
- `elicitation_ask` MCP tool (schema + handler + dispatch + count test);
  handler validated with a mocked session across accept/decline/cancel +
  capability-error.
- Tool count bumped; `test_mcp_memory_tools.py` updated.
- Findings/decisions note the renderer is live-pending a restart (R5
  caveat), as in V2.0.

## Out of scope

- The `show_widget` escape-hatch renderer (S1) for slider/color.
- V2.3 (designer / data-binding).
- Changing the v1 AskUserQuestion tools (`render_form`/`collect_response`)
  — they stay; `elicitation_ask` is the elicitation-surface sibling.

## Tasks

<task id="v2.2-1" name="form-to-elicitation-schema">
  <objective>
    Productionize form_to_elicitation_schema(form) in attune.elicitation:
    all 7 QuestionTypes → a valid elicitation requestedSchema.
  </objective>
  <validation>
    <check>multi_select → array+items.enum; number → number+min/max; date
    → string+format:date; textarea/text → string+maxLength.</check>
    <check>title/description/default threaded; required list correct.</check>
  </validation>
</task>

<task id="v2.2-2" name="elicitation-ask-tool">
  <objective>
    Add the elicitation_ask MCP tool: schema + handler that builds the
    schema, awaits session.elicit_form, and on accept validates content via
    collect_form_response; handles decline/cancel + capability error.
  </objective>
  <files-to-modify>
    <file path="src/attune/mcp/tool_schemas.py">add elicitation_ask schema</file>
    <file path="src/attune/mcp/server.py">handler + dispatch + register</file>
    <file path="tests/unit/test_mcp_memory_tools.py">bump tool count</file>
  </files-to-modify>
  <validation>
    <check>handler builds the right requestedSchema and returns validated
    responses on accept; clean status on decline/cancel; graceful error
    when the session can't elicit.</check>
  </validation>
  <risks>
    <risk severity="medium">Live round-trip needs an elicitation-capable
    client + server restart — prove the path with a mocked session, defer
    the true live R5 (document it, as V2.0 did).</risk>
  </risks>
</task>

<task id="v2.2-3" name="tests-and-decision">
  <objective>
    Unit tests for the transform (all types) and the handler (mocked
    session: accept/decline/cancel/capability-error). Record D9 (renderer
    shipped; live-pending restart).
  </objective>
</task>
