---
type: reference
subtype: procedural
name: skill-elicit
category: skill
tags: [skill, plugin]
source: plugin/skills/elicit/SKILL.md
---

# Reference: Skill: elicit

Gather missing, independent planning details in one validated form. Use for ordinary planning or scoping requests with multiple unknowns, explicit discovery forms, and multi-select questions.

**Usage:** `/elicit <what you're scoping, e.g. 'a new feature' or 'this session'>`

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

## Step 0 — check the template library first (V7)

Recurring fork classes are stored as named JSON templates in the
`attune_forms` package (`attune_forms/templates/` in the installed
wheel; new templates land in the attune-forms repo). **Reach for a
template before hand-building**: a reused template makes answers
comparable across sessions (joinable on `FormResponse.template_id`),
and from attune-forms 0.8.0 each cast is telemetry-tagged
`template:<name>` vs `dict` — the adoption signal is measured, so
hand-building a form a template already covers shows up in the log.
Check `list_templates()` first; only hand-build when nothing matches.

```python
from attune.elicitation import form_from_template, list_templates

form = form_from_template("session-contract", {"project": "attune-ai"})
# ... render, then collect with the join key:
response = collect_form_response(form, answers, template_id="session-contract")
```

Available templates:

| Name | Construct | Purpose | Slots |
|---|---|---|---|
| `session-contract` | intake-form | Session-start protocol: mode, outcome, done-when, effort cap | `project` |

Missing/extra slot values and malformed templates fail through the
same every-problem-listed `FormValidationError` a hand-built dict
gets. **Promote-on-repeat (R5):** a form earns templatehood on its
SECOND recurrence — no speculative templates.

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

## Infer first — the highest-value thing you can do

Before you build the form, check what the conversation already answered.
A three-field ask where two are inferable is a one-field ask plus a
confirmation. This is the main defence against ceremony: forms feel
heavy when they re-ask what you already said, not when they are rich.

Set `default` to the value and `inferred_from` to why:

```json
{"id": "scope", "type": "single_select", "text": "Which path?",
 "options": ["src", "tests"], "default": "src",
 "inferred_from": "you have been editing src/"}
```

`inferred_from` without `default` is a definition error. Both surfaces
mark the value as a guess — the widget badges it, `AskUserQuestion`
folds it into help text — so a wrong inference is catchable.

**Infer, then confirm — never infer and skip.** When you can infer every
field, still render the form; it comes back as a one-tap confirmation
with a `Confirm` button. A correct-looking wrong guess the user never
saw is the only failure a form cannot recover from. Do not "save them a
turn" by acting on inferences silently.

Only infer what the conversation actually supports. A guess with no
basis is worse than a question, because it costs the user a correction
instead of an answer.

## Choosing a surface



### Codex: use the verified server route (bounded D14 milestone)

For an ordinary planning or scoping request in Codex, first apply the
batching rule and existing preference scope. Do not re-ask settled fields
or manufacture a decision merely to demonstrate a form. An explicit
conversation preference or incompatible presentation requirement does not
authorize a native dialog; preserve that preference and explain any
unavailable presentation without claiming it is implemented.

When a form is appropriate and the connected attune-ai server exposes
`elicitation_route_form`, use that endpoint instead of the compatibility
surface selector below. Discover the actual connected tool; do not hard-code
a preview server name or infer readiness from a package version. The server
owns capability negotiation, evidence, and surface selection. Never send
caller-invented capability, session, evidence, or binding fields.

1. Build the form using steps 0–1. Call `elicitation_route_form` with
   `form` (or `template` plus its `slots`) and an optional `message`.
2. Wait for its same-call completion. Only an outer `success: true`
   **and** `completion.success: true` with `completion.action: accept`
   supplies accepted `completion.responses`. Summarize those values once
   and continue the same task within its existing authorization. Do not
   call `elicitation_collect_response` again or dispatch another form
   to collect the already validated answers.
3. An abort, timeout, or validation exhaustion supplies no accepted
   answers. Respect that outcome; do not treat outer success alone as
   acceptance or re-open the interaction automatically. The server owns
   validation retries within the call.
4. `no_supported_surface` means nothing was rendered. Report the unavailable
   route without cycling through compatibility renderers. Likewise,
   `render_failed`, `session_ended`, `challenge_invalidated`, or
   `challenge_consumed` ends this attempt; do not retry another renderer.
   A later presentation requires a separately established supported path.

This milestone implements native MCP elicitation, not every rich widget
layout or every host. Returned HTML, tool availability, and a successful
tool return do not prove visible controls. Keep user-observed display,
validated completion, and request-to-visible timing as separate evidence.
Selection time is not display latency; process reuse is not policy warmth.

If the endpoint is absent, the compatibility guidance below remains
available subject to the host's actual support and the user's preferences.
Do not claim that path has the new route's session-bound guarantees. Other
hosts retain their existing guidance until independently verified.

### Compatibility surfaces

**The widget is the default. `AskUserQuestion` is the fallback.**
(D21 — this reverses the earlier cheapest-surface-that-fits rule.)
Don't route on what the surface can technically express; route on how
much of the option space the user can see at once. Folding three
options and their tradeoffs into prose above a single-select turns a
scan into a serial read the user has to hold in their head — that loss
is real even though a control-type check can't see it.

`select_form_surface(form, widget_capable=…, keyboard_mode=…)` in
`attune.elicitation` is this rule in code. Call it instead of deciding
by hand. Precedence, highest first:

1. **Client can't render widgets** → `AskUserQuestion`. A constraint,
   not a preference.
2. **A `number` / `date` / `textarea` field** → widget, always. These
   have no `AskUserQuestion` control at all, so this outranks the
   opt-out and the user can never silently lose a field.
3. **Keyboard mode on** → `AskUserQuestion`. The user's opt-out, set
   with `attune config set keyboard_mode true` and persisted per project
   in `attune.config.json`, with `ATTUNE_KEYBOARD_MODE` as a session
   override. If a user says forms feel like too much, point them at that
   command rather than arguing the default.
4. **Trivial form** → `AskUserQuestion`. Trivial is narrow and
   mechanical: exactly one `single_select`/`boolean`, ≤3 options, and
   no option label over 120 chars. A long label means tradeoffs got
   folded into the text — that form wanted a card.
5. **Otherwise** → widget.

### Scoped preferences (adaptive-session-interactions, ASI-2)

Two preference scopes sit ABOVE the router's precedence, and both change
presentation only — never validation, never action authority:

- **One-interaction override** — the user's words for this ask ("just
  tell me in text", "show me the widget this once"). Honor it for this
  interaction only; it does not rewrite anything stored.
- **Session-wide preference** — "just talk to me" / "stop with the
  forms". Store it with the attune-ai MCP context tools: `context_set`
  key `interaction_preference`, value `conversation`; read it back with
  `context_get` once per session (again only when the user changes it),
  not before every render. It lives for the MCP server instance — one
  per stdio server process in the shipped plugin — and survives phase
  changes until the user changes it. `conversation`
  means: render the form on the text lane and transcribe the answer.
  Keyboard mode is NOT this preference — it is a project-scoped,
  file-persisted opt-out that still asks, via a flatter control.

Precedence: explicit override for this interaction → explicit session
preference → the router's default. A missing preference is not an
opt-out and not consent.

**The text lane keeps every field.** From a Claude Code session the
text lane IS steps 2–4 below (`elicitation_render_form` →
`AskUserQuestion` → `elicitation_collect_response`); a field a lane
cannot represent is disclosed and asked, never dropped. For hosts with
no `AskUserQuestion` and for library consumers, attune-forms ships a
markdown surface — `form_to_markdown(form)` renders every field into one
skeleton, `markdown_to_answers` parses the typed reply deterministically
(a stray line is a named problem, never a guess), and
`problems_to_markdown` re-asks only the failing fields. It is a Python
library surface: no MCP tool exposes it yet and the router's range is
`widget` / `ask` only, so do not try to call it as a tool.

**Latency is not a reason to downgrade a form.** The extra tool call is
a real cost but it is not the axis; if a form is worth asking, it is
worth asking legibly. `needs_widget` still exists as the low-level
"does this lose fidelity on AskUserQuestion" check, but it no longer
owns the decision — don't route on it directly.

**After the answer comes back,** collapse the form rather than leaving
the rendered markup in the transcript: `form_response_summary(form,
response)` returns a few lines of markdown (title + one bullet per
answer). Use it in your narration so a long session accumulates
summaries, not screenfuls of HTML.

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

For the Codex server-routed path, follow its same-call procedure above
instead of steps 2–4. The following steps are the compatibility path.

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

## Related Topics
- **Reference**: Tool: Context Set (`context_set`)
- **Reference**: Tool: Context Get (`context_get`)
