# Elicitation v2 — Phase 2.1 (V2.1): rich controls on the artifact

Requirements for extending the declarative form artifact with the rich
controls the **lead surface (MCP elicitation, D8)** supports natively.
Model + validation only — the elicitation renderer is V2.2.

## Context

- D8 chose MCP elicitation as the v2 lead surface. Its schema supports
  string (with `format`, `pattern`, `min/maxLength`), number/integer
  (`min/max`), boolean, and enums (single + multi) —
  [findings](v2-phase0-findings.md).
- The artifact today (`QuestionType` in `meta_workflows/models.py`)
  supports `text_input`, `single_select`, `multi_select`, `boolean`.
- The v1 bridge (`attune.elicitation`) is the locked validation seam
  (`form_from_dict`, `collect_form_response`) — V2.1 extends it, reuses
  its shape.

## Problem

The artifact can't yet express numeric, date, or multi-line-text fields,
so a v2 form is stuck with selects/booleans/short text. These are the
rich controls elicitation can host — the first concrete payoff of D8.

## Goals

- **G1** Add `number`, `date`, `textarea` to `QuestionType` plus the
  constraints elicitation honours (`minimum`/`maximum` for number,
  `max_length` for text/textarea).
- **G2** Validate them on both sides: `form_from_dict` rejects malformed
  *definitions*; `collect_form_response` rejects malformed *answers*
  (R4 — never silently accept).
- **G3** Pure model + validation, fully unit-tested (like the v1 bridge,
  100% line+branch on new logic). No renderer.

## Scope

In: `number` (optional `minimum`/`maximum`), `date` (ISO-8601 `YYYY-MM-DD`
string), `textarea` (optional `max_length`).

Deferred (no native elicitation control → the `show_widget` escape hatch,
a later sub-phase): `slider`, `color`. v1's `AskUserQuestion` renderer is
left as-is — rich-typed forms target the elicitation surface (V2.2); their
`AskUserQuestion` rendering is best-effort, out of scope here.

## End state (acceptance)

- `QuestionType` has `NUMBER`, `DATE`, `TEXTAREA`; `FormQuestion` carries
  optional `minimum`, `maximum`, `max_length` (backward-compatible —
  trailing defaulted fields).
- `form_from_dict` parses the new fields and rejects a bad definition
  (e.g. `minimum > maximum`, non-numeric bound, negative `max_length`).
- `collect_form_response` validates answers: number is numeric and in
  range; date parses as `YYYY-MM-DD`; textarea is a string within
  `max_length`.
- Tests cover every new type + every new failure path.

## Out of scope

V2.2 (elicitation renderer + live round-trip), slider/color, V2.3.

## Tasks

<task id="v2.1-1" name="extend-artifact-model">
  <objective>
    Add NUMBER/DATE/TEXTAREA to QuestionType and optional minimum/maximum/
    max_length to FormQuestion (trailing defaulted fields — backward
    compatible).
  </objective>
  <files-to-modify>
    <file path="src/attune/meta_workflows/models.py">
      <change location="QuestionType + FormQuestion">Add enum members and
      constraint fields; keep to_ask_user_format non-crashing.</change>
    </file>
  </files-to-modify>
  <validation>
    <check>Existing FormQuestion construction sites still work (new fields
    default to None).</check>
  </validation>
</task>

<task id="v2.1-2" name="extend-bridge-validation">
  <objective>
    Teach form_from_dict to parse + validate the new fields, and
    _validate_answer to validate number/date/textarea answers (R4).
  </objective>
  <files-to-modify>
    <file path="src/attune/elicitation/bridge.py">
      <change location="form_from_dict, _validate_answer">Parse
      constraints, reject bad definitions and bad answers with named
      problems.</change>
    </file>
  </files-to-modify>
  <validation>
    <check>minimum>maximum, non-numeric bound, negative max_length → defn
    error.</check>
    <check>out-of-range number, unparseable date, over-length text,
    wrong-type → answer problem.</check>
  </validation>
</task>

<task id="v2.1-3" name="tests">
  <objective>
    Unit tests for every new type and failure path; keep 100% line+branch
    on the new bridge logic.
  </objective>
  <files-to-modify>
    <file path="tests/unit/elicitation/">Add cases for number/date/
    textarea definition + answer validation.</file>
  </files-to-modify>
  <validation>
    <check>All new paths covered; suite green.</check>
  </validation>
</task>
