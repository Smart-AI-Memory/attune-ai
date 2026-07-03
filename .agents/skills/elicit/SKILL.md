---
name: elicit
description: "Form-driven Socratic discovery — batch independent decision dimensions into one multi-select-capable form instead of N button-turns. Triggers on: scope this, discovery form, ask me everything at once, multi-select question."
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
`text_input`, `number` (with `minimum`/`maximum`), `date` (ISO
`YYYY-MM-DD`), `textarea` (with `max_length`), or `decision` (see "The
decision construct" below). `id` is the stable key the answer comes back
under. The rich controls — `number`/`date`/`textarea` — render on the
native elicitation (`elicitation_ask`) and widget
(`elicitation_render_widget`) surfaces below, but degrade to plain text
on AskUserQuestion.

**List render (`list_style`).** On a `single_select` or `multi_select`,
set `"list_style": "ordered"` (numbered) or `"unordered"` (bulleted) to
render the options as the familiar intro-sentence-plus-list shape —
each item pickable by mouse or the `1`/`2`/`3` reply vocab — instead of
the default dropdown/checkboxes. Presentation only: the answer and its
validation are unchanged (it is **not** a separate construct — see
decisions.md D19). Only valid on the two select types.

## The decision construct (v3)

A `decision` is a presentation-enriched single-select: the agent offers
a **recommended** option with a **rationale** and per-option
**tradeoffs**, and the user picks one. Use it to *offer a choice*, not to
*gather intake* — it is the agent-to-user half of the grammar (the
constructs above gather input). See
`.claude/rules/attune/communication-grammar.md`.

Extra field keys (all optional):

- `recommended` — the option to badge "Recommended" and order first
  (must be one of `options`).
- `rationale` — the "why this recommendation" callout shown beneath the
  cards.
- `option_notes` — `{option: one-line tradeoff}` shown under each card.

```json
{
  "title": "Focused session plan",
  "fields": [
    {"id": "approach", "text": "How should we spend this session?",
     "type": "decision",
     "options": ["Verifiable backlog loop", "Behind a verify gate",
                 "Non-LLM backlog"],
     "recommended": "Verifiable backlog loop",
     "rationale": "Building LLM features blind manufactures unverified work.",
     "option_notes": {"Verifiable backlog loop": "Real progress now",
                      "Behind a verify gate": "Parked until the key returns",
                      "Non-LLM backlog": "Fully provable today"}}
  ]
}
```

**Surface:** the rich card layout (badge + tradeoffs + rationale) renders
on the **widget** surface (`elicitation_render_widget` → `show_widget`);
the answer is one selected option, validated like a single-select.

**AskUserQuestion fallback:** a `decision` maps to a `single_select` with
the recommended option ordered first and " (Recommended)" appended to its
label; fold each `option_notes` tradeoff into that option's
`description`, and use the `rationale` as the question's lead-in.

## The pushback construct (v4)

A `pushback` is a `decision` framed as **dissent**: the agent disagrees
with the user's stated approach and offers a concrete alternative. Use it
when a user-stated choice looks weaker than an alternative you can render
concretely — the decision-routine "pushback discipline". Same
single-select answer path as `decision`; only the framing differs. When
it fires is governed by
`.claude/rules/attune/decision-routine.md`.

Extra field keys (all optional; reuses the decision keys plus one):

- `user_position` — the option that is the user's stated approach; it is
  tagged "your approach" (must be one of `options`).
- `recommended` — the agent's alternative; badged "I'd suggest instead"
  and ordered first (must be one of `options`).
- `rationale` — the disagreement, shown beneath the cards under a "Why
  I'd push back" header.
- `option_notes` — `{option: one-line tradeoff}` shown under each card.

```json
{
  "title": "Retry strategy",
  "fields": [
    {"id": "retries", "text": "How should we handle transient failures?",
     "type": "pushback",
     "options": ["Fixed 3x retry", "Exponential backoff + jitter"],
     "user_position": "Fixed 3x retry",
     "recommended": "Exponential backoff + jitter",
     "rationale": "Fixed retries hammer a struggling service; backoff is gentler and avoids a thundering herd.",
     "option_notes": {"Exponential backoff + jitter": "Industry default"}}
  ]
}
```

**Surface:** the dissent card layout renders on the **widget** surface
(`elicitation_render_widget` → `show_widget`); the answer is one selected
option (overrule = the user's approach, switch = the alternative),
validated like a single-select.

**AskUserQuestion fallback:** a `pushback` maps to a `single_select` with
the agent's alternative ordered first; label the `user_position` option
clearly as the user's current approach, fold each `option_notes` tradeoff
into the matching option's `description`, and use the `rationale` (the
disagreement) as the question's lead-in.

## The progress construct (v5)

A `progress` is a **report**, not a fork: the agent reports a set of items
by status — `done` / `in_flight` / `blocked` — and surfaces the **blocked**
items as a single-select picker ("which blocker do you want to tackle?").
Use it to report where multi-step work stands while keeping the next move
one pick away. Same single-select answer path as `decision` (the answer is
one blocked item); when nothing is blocked it degrades to a pure status
display with no answer.

Extra field keys (all optional; reuses the decision keys plus one):

- `progress_items` — the reported items as `{label, status, detail?}` dicts,
  `status` ∈ `done` / `in_flight` / `blocked`. **The blocked subset's labels
  must equal `options`** (the picker offers exactly the actionable items);
  `done`/`in_flight` items are reported but not pickable.
- `recommended` — the blocked item to suggest tackling first; badged
  "suggested next" and ordered first (must be one of `options`).
- `rationale` — a one-line report summary, shown under a "Summary" header.
- `option_notes` — `{blocked-option: one-line detail}` shown under each card
  (a blocked item's `detail` is used as a fallback note when absent).

```json
{
  "title": "Spec execution",
  "fields": [
    {"id": "exec", "text": "Where execution stands", "type": "progress",
     "options": ["T6 consumer wiring"],
     "recommended": "T6 consumer wiring",
     "rationale": "1 of 8 tasks blocked on a quality gate.",
     "progress_items": [
       {"label": "T1 model", "status": "done"},
       {"label": "T3 widget", "status": "in_flight", "detail": "rendering cards"},
       {"label": "T6 consumer wiring", "status": "blocked", "detail": "gate failed: score 42"}
     ]}
  ]
}
```

When nothing is blocked, set `options: []` and `required: false` — the
report renders as a status display with no picker.

### The "report" style (v5.1)

`"progress_style": "report"` renders a **neutral digest** instead of a
task report: item `status` is a free-form category tag (e.g. a memory
node type — no done/blocked semantics, no strikethrough), and `options`
may be **any subset** of item labels, offered as a "Pick one to go
deeper" picker (items not in `options` render as static tagged rows).
Pure presentation — the answer is still one selected option, validated
as a single-select. Set `required: false` when a pick is optional.
First consumer: the curated-memory recall digest
(`python -m attune.memory.recall_digest` renders the live Redis digest
as this form).

```json
{"id": "digest", "text": "Pull more on a topic?", "type": "progress",
 "progress_style": "report", "required": false,
 "options": ["Memory architecture"],
 "progress_items": [
   {"label": "Memory architecture", "status": "project context", "detail": "git + Redis"},
   {"label": "Recall benchmarks", "status": "reference"}
 ]}
```

**Surface:** the three-bucket layout (static done/in_flight rows + the
blocked radiogroup picker) renders on the **widget** surface
(`elicitation_render_widget` → `show_widget`); the answer is the one
selected blocked item, validated like a single-select.

**AskUserQuestion fallback:** a `progress` folds the done/in_flight/blocked
summary into the question text and maps the **blocked** items to a
`single_select` with the `recommended` item ordered first. When there are
no blocked items there is nothing to ask — just narrate the report.

## Choosing a surface

- **Rich / native — one call:** `elicitation_ask` renders the form as a
  native MCP elicitation dialog (supports number/date/textarea +
  multi-select with a structured return) and returns the validated
  answers in a single call — no manual `AskUserQuestion` mapping. It
  returns `{success: false, action: "unsupported"}` when the client
  can't elicit. **Caveat (Claude Code, observed 2026-06-27, decisions
  D10):** some clients advertise elicitation but **auto-decline form
  requests without rendering** — you get `action: "decline"` and no
  dialog. Treat a `decline` you didn't see the user make as
  "surface unavailable" and fall back; don't report it as the user
  saying no.
- **Rich / widget — `show_widget`:** `elicitation_render_widget` returns
  inline HTML that renders ALL 7 controls richly (number spinner, date
  picker, multi-line textarea, multi-select checkboxes). Pass its `html`
  straight to `mcp__visualize__show_widget`; the user submits and the
  widget posts the answers back (see "Widget surface" below). Best
  rich surface on widget-capable clients (Cowork/claude.ai) when native
  elicitation doesn't render.
- **Portable — AskUserQuestion:** steps 2–4 below map the form onto
  `AskUserQuestion` (selects/booleans/short text only). Use this as the
  fallback, or when you want the recommendation-first button UX.

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

Then call `AskUserQuestion` with all the batch's entries at once. When a
batch has **more than one question**, set `metadata` to
`{"source": "elicit-form"}` — that marker is the deliberate opt-in the
one-question-per-turn guard requires for a §4 batched form. Without it,
a multi-question call is blocked (the default discipline). Multi-select
questions need no "(Recommended)" first option; single-select questions
still lead with the recommended choice.

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

## Widget surface — `show_widget` round-trip

Use this instead of steps 2–4 when you want the rich controls on a
widget-capable client:

1. Call `elicitation_render_widget` with `{ "form": <the form> }`. On
   success you get `{ "html", "title", "field_ids" }`; on a bad form,
   `{ "success": false, "problems": [...] }` — fix and re-render.
2. Pass `html` verbatim to `mcp__visualize__show_widget`.
3. The user fills the form and submits. The widget posts a chat message
   containing a fenced JSON block marked `__elicitation_response__`,
   e.g. `{"__elicitation_response__": true, "title": "...", "answers":
   {<field_id>: <value>}}` (multi-select → list, number → number,
   date → `YYYY-MM-DD`, boolean → `"Yes"`/`"No"`).
4. When that message arrives, parse the JSON block and call
   `elicitation_collect_response` with `{ "form": <the same form>,
   "answers": <the payload's answers> }` to validate (R4). Re-ask only
   the fields it flags as problems — never proceed on raw widget output.

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
