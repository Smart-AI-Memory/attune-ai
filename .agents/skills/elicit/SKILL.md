---
name: elicit
description: "Form-driven Socratic discovery — batch independent decision dimensions into one multi-select-capable form instead of N button-turns. Triggers on: scope this, discovery form, ask me everything at once, multi-select question, gather requirements as a form."
---
# Elicit — form-driven Socratic discovery

**IMPORTANT: Start your response by telling the user:**

> **Elicit** — Gathering the independent dimensions of your decision
> as one form (multi-select where it fits), instead of asking one
> button at a time.

This skill turns a **declarative form** (data, not code) into a real
`AskUserQuestion` turn and validates the answers. It is the live wiring
of `attune.elicitation` via two MCP tools:

- `elicitation_render_form` — validate the form, get batched payloads.
- `elicitation_collect_response` — validate the answers (R4).

## When to render a multi-field form (the batching rule)

Batch 2–4 fields into **one** form-turn only when ALL hold:

- the fields are **independent dimensions of one decision** the user
  makes together (e.g. spec kickoff: goal + scope + focus), AND
- answers **don't branch** on each other (if a field's relevance
  depends on another's answer, stay sequential), AND
- each field is **genuinely ambiguous** — a dimension the user already
  specified is omitted, not asked.

**Stay single-question** when only one dimension is unknown, a later
question depends on an earlier answer, or batching would feel like a
bureaucratic intake for a simple ask. The form never adds fields the
ordinary Socratic-ambiguity judgement wouldn't already ask.

## Step 1 — build the declarative form (D3)

A form is plain serializable data:

```json
{
  "title": "Scope this work",
  "description": "Optional one-liner",
  "fields": [
    {"id": "goal", "text": "What are you trying to accomplish?",
     "type": "single_select",
     "options": ["Fix a bug", "Add a feature", "Refactor", "Investigate"]},
    {"id": "focus", "text": "Which areas matter here?",
     "type": "multi_select",
     "options": ["correctness", "security", "performance", "tests"]}
  ]
}
```

Field `type` is one of `single_select`, `multi_select`, `boolean`,
`text_input`. `id` is the stable key the answer comes back under.

## Step 2 — render it

Call `elicitation_render_form` with `{ "form": <the form> }`.

- Success → `{ "success": true, "batches": [[ <payload>, … ]] }`. Each
  batch is one `AskUserQuestion` call (≤4 questions).
- Failure → `{ "success": false, "problems": [ … ] }`. Fix the form
  definition and re-render; do not hand-roll the questions.

## Step 3 — ask, mapping each payload to AskUserQuestion

For each payload in a batch, build one `AskUserQuestion` entry:

| Payload field | AskUserQuestion |
| ------------- | --------------- |
| `question` | `question` |
| `type: "multi_select"` | `multiSelect: true` |
| `type: "single_select"` / `"boolean"` | `multiSelect: false` |
| `options` (list of strings) | `options: [{label, description}]` |
| `question_id` | track it — it keys the answer in step 4 |

Also:

- **header** — a short tag (≤12 chars) derived from the question.
- **recommendation-first** — if there's a sensible default, make it the
  first option and end its label with " (Recommended)".
- **free text** — for a `text_input` field, offer any curated
  suggestions as options; the user types anything via the built-in
  **"Other"** escape `AskUserQuestion` always provides.
- **>4 options** — use the two-tier picker (category → item), don't
  overflow a single question.

Then call `AskUserQuestion` with all the batch's entries at once.

## Step 4 — collect and validate (R4)

Assemble the answers into `{ field_id: value }` (a string for
single-select/boolean/text, a list of strings for multi-select), then
call `elicitation_collect_response` with `{ "form": <the form>,
"answers": <that map> }`.

- Success → `{ "success": true, "responses": { … } }`. Use those
  values — they are validated against the form.
- Failure → `{ "success": false, "problems": [ … ] }` names exactly
  which fields are missing-required or out-of-option. **Re-ask only
  those fields** (a one-field form) — never silently proceed.

## Worked example — `/attune` discovery in one turn

The headline use: the `/attune` scoping turn that today asks goal, then
scope, then focus as three sequential buttons. Gather them as one form
when each is genuinely open (drop any the user already stated):

```json
{
  "title": "What do you want to do?",
  "fields": [
    {"id": "goal", "text": "What are you trying to accomplish?",
     "type": "single_select",
     "options": ["Run a workflow", "Manage memory", "Configure settings",
                 "Learn what attune does"]},
    {"id": "scope", "text": "Where should it focus?",
     "type": "text_input", "options": ["src/", "tests/", "whole project"]},
    {"id": "concerns", "text": "Which concerns matter?",
     "type": "multi_select", "required": false,
     "options": ["security", "quality", "performance", "tests"]}
  ]
}
```

Render → ask (one `AskUserQuestion`, `concerns` as multi-select) →
collect → route on `responses["goal"]` (see the attune-hub skill's
routing table) scoped by `responses["scope"]` and `responses["concerns"]`.
