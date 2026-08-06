---
paths:
  - "src/attune/elicitation/**"
  - "src/attune/meta_workflows/**"
  - "plugin/skills/elicit/**"
  - ".agents/skills/elicit/**"
---

# Communication Grammar

**Created:** 2026-06-29
**Spec:** [docs/specs/elicitation-form-surface/](../../../docs/specs/elicitation-form-surface/)
(V3 — decisions.md D14, v3-requirements.md)

---

## What this is

A small, growing **family of conversational constructs** the agent
composes to communicate with the user — structured shapes instead of
freeform prose. Every construct is **declarative**: the agent authors
a small spec, never renderer code, and a shared renderer turns it into
the same artifact on every surface.

Members divide into two classes by what the user does with them:

| Class | Substrate | User answers? | Members |
|---|---|---|---|
| **Interactive** | `FormSchema` (`meta_workflows.models`) | yes — validated | intake-form, decision, pushback, progress |
| **Display** | sealed widget kernel + JSON spec | no — it reports | chart |

Both classes are the grammar. They share the discipline (declarative
spec, one renderer, degrades legibly); they differ in whether there is
an answer to validate. Adding a display member does **not** add a
`QuestionType` — see "How to add the next member".

The grammar is **agent-to-user expression** (how the agent structures
what it offers). It is not user-to-agent command syntax, and it does not
replace the terse reply vocab (`y` / `go` / `1`) — those are the
*answers* to a construct.

Constructs fire **reactively**, in the live conversation — never on a
schedule. When a construct fires (e.g. the decision construct on a
non-trivial choice) is governed by
[decision-routine.md](decision-routine.md), not here; this file is the
*shape*, not the *when*.

---

## The interactive substrate (intake-form, decision, pushback, progress)

- **One artifact** — a `FormSchema` of `FormQuestion`s, built from plain
  data via `attune.elicitation.form_from_dict` (D3).
- **Renderers** — `form_to_widget_html` (the widget surface, the rich
  one that renders on Claude Code, D10/D11); the `AskUserQuestion`
  fallback (`form_to_askuserquestion`); native MCP elicitation
  (`form_to_elicitation_schema`, currently non-rendering on CC).
- **One validator** — `collect_form_response` (R4): never silently
  accept malformed input; re-ask only the offending fields.

A construct adds **meaning and presentation** on top of this substrate;
it almost never adds a new round-trip or validator.

---

## The display substrate — sealed widget kernels (chart, …)

Ratified as chartkit (#1941) and generalized by
[widget-kernel-family](../../../docs/specs/widget-kernel-family/):
**sealed kernel + declarative spec + RFC 7386 patch**.

- **One artifact** — a small JSON spec the model authors (~50–200
  tokens), validated against the kernel's `spec.schema.json`. The model
  never writes renderer code.
- **One renderer** — a sealed, size-budgeted JS kernel (chartkit: 6.7KB)
  that turns the spec into inline SVG/HTML. Kernel source imports
  nothing outside itself; nothing imports kernel internals. That seal is
  what keeps the bytes — and the blast radius — bounded.
- **Update by patch, not re-send** — a stable `<kind>_id` plus an RFC
  7386 merge patch (null deletes, objects merge, arrays/scalars replace)
  mutates the stored spec, so an update costs a patch instead of a whole
  widget. Persistence lives in session memory and **degrades legibly**:
  when it is unavailable the result says so and asks for a full spec.
- **No validator, because there is no answer** — a display member
  reports. Errors surface field-level at *author* time
  (`encodings.x.field: Field required`), which is the display analogue
  of the interactive substrate's re-ask-the-offending-field rule.

One kernel per widget type. `chartkit` ships; `formkit` and `infokit`
are specified (R1/R2) and slot in here as they land — a new widget type
is a new kernel plus a new MCP tool, not a new grammar mechanism.

---

## Members

### intake-form (v1 / v2 — shipped)

Gather the independent dimensions of one decision as a single
(multi-select-capable) form. Driven by the `elicit` skill; adopted into
`/spec`, `/attune`, `/planning` (D13). Question types: `single_select`,
`multi_select`, `boolean`, `text_input`, `number`, `date`, `textarea`.

### decision / opening-shape (v3)

The agent offers a **recommended** option with a **rationale** and
per-option **tradeoffs**; the user picks one. A `QuestionType.DECISION`
is a presentation-enriched single-select — the answer is one option,
validated exactly as a single-select. Extra `FormQuestion` slots:
`recommended`, `rationale`, `option_notes`. Renders as cards (badge +
tradeoffs + rationale) on the widget surface; falls back to a
recommendation-first single-select on `AskUserQuestion`.

### pushback (v4)

The agent **disagrees** with the user's stated approach and offers a
concrete alternative + a disagreement rationale; the user picks one
(overrule = keep their approach, or switch). A `QuestionType.PUSHBACK`
is — like `decision` — a presentation-enriched single-select; the
answer is one option, validated exactly as a single-select. It adds one
optional slot, `user_position` (the option that is the user's stated
approach), and reuses `recommended` (= the agent's alternative),
`rationale`, and `option_notes`. The dissent framing is what
distinguishes it from `decision`: the `user_position` card is tagged
"your approach", the `recommended` card is badged "I'd suggest instead"
(not "Recommended") and ordered first, and the rationale callout is
headed "Why I'd push back". Falls back to a recommendation-first
single-select on `AskUserQuestion`. When the pushback construct fires is
governed by [decision-routine.md](decision-routine.md)'s pushback
discipline — this is the shape, not the when.

### progress (v5)

The agent **reports** a set of items by status — `done` / `in_flight` /
`blocked` — and surfaces the **blocked** items as a single-select picker
("which blocker do you want to tackle?"); the user picks one. It is the
first member that is a *report* rather than a fork. A
`QuestionType.PROGRESS` is — like `decision` / `pushback` — a
presentation-enriched single-select whose answer is one blocked option,
validated exactly as a single-select. It adds one optional slot,
`progress_items` (the reported items as `{label, status, detail?}` dicts;
the `blocked` subset's labels must equal `options`), and reuses
`recommended` (= the blocked item to tackle first, badged "suggested
next"), `rationale` (= a "Summary" callout), and `option_notes`. The
widget renders three buckets: `done`/`in_flight` items as static rows,
`blocked` items as the radiogroup picker. When **nothing is blocked**
(`options` empty) it degrades to a pure status display with no answer —
so within the *interactive* substrate "pure display" is a sub-state of
one construct rather than a separate form member, and that substrate
stays answer-validated whenever there is something actionable. (Display
*members* — chart, v6 — are a different class on a different substrate;
they are display by design, not by degradation.) Falls back to a recommendation-first single-select over the
blocked items on `AskUserQuestion` (the done/in_flight summary folds into
the question text). First consumer: the `/spec` execute gate (done =
completed tasks, in_flight = current task, blocked = quality-gate
failures; the picker = "which blocked task to fix/retry").

### chart (v6 — first display member)

The agent **shows** quantitative shape — bar, line, scatter, area,
heatmap — as inline SVG, from a declarative spec instead of prose or a
markdown table. First member of the display class, so it carries no
`QuestionType`, no `FormSchema`, and no answer.

Tool: `chart_render_widget` (`chart_id` + `spec` to create/replace,
`chart_id` + `patch` to update); the returned `html` goes straight to
`mcp__visualize__show_widget`. Kernel: `src/attune/widgets/chartkit/`
(sealed, 6.7KB, `spec.schema.json` is the contract). Shipped in #1941.

**When it fires:** the user needs to *see* a distribution, a trend, or a
comparison — several series, a time axis, a magnitude ranking. A number
or two is prose; a handful of labelled rows is a markdown table; shape
across many points is a chart. Same reactive discipline as every other
member: it fires in the live conversation because the content calls for
it, never on a schedule, and never as decoration over a table that
already reads clearly.

**Pairs with, doesn't replace, the interactive members.** A chart that
implies a decision is a chart *plus* a `decision` construct — the
display member reports the shape, the interactive member collects the
answer. Do not smuggle a fork into a chart caption.

---

## Feedback asks — full-scope (chair-ruled 2026-07-30)

When the agent ASKS THE USER FOR FEEDBACK on its own conduct,
work, or a ruling recommendation (including inviting pushback),
the grammar is mandatory THROUGHOUT — both the generative half and
the disposition half render as constructs, each construct firing
when its content exists: `pushback` when the agent holds a
counter-position, `decision`/multi-select when enumerable points
await disposition, and free-text form fields (`textarea`) for the
open-ended half — an open ask is still a form, never bare prose,
and no construct fabricates disagreement or options to satisfy
the rule. Ruled by the chair over the lead's
disposition-only recommendation (both positions recorded in
feature-lead-governance decisions.md, 2026-07-30); prose may
accompany, never replace, the constructs.

One carve-out (same ruling, PROTECT-THEN-ASK): a reversible
protective act against the agent's OWN prior action — disarming an
auto-merge it armed, dropping a label it applied — executes BEFORE
any form is built; the form renders afterward for the standing
decision. A form is a request for input; a reversible guard needs
none. Undoing a CHAIR action is never a protective act — neither
directly (a chair-applied label, a chair-armed merge) nor
indirectly (reverting an own-action the chair has since endorsed
or relied on); those always go through the chair first.

---

## How to add the next member (#7)

**First decide the class.** Does the user *answer* it? Yes → interactive
construct, track A. No, it reports → display member, track B. Getting
this wrong is expensive in opposite directions: a `QuestionType` with no
answer to validate, or a kernel that needs a round-trip it cannot do.

### Track A — a new interactive construct

Keep it additive and substrate-reusing. The decision (v3), pushback
(v4), and progress (v5) constructs are the worked examples to copy.

1. **Decide the shape.** Does it compose existing question types, or
   need a new `QuestionType`? Prefer composing. A new type is justified
   only when rendering or answer-meaning genuinely differs.
2. **Extend the model additively** (`meta_workflows/models.py`). Add the
   `QuestionType` member and any *optional* `FormQuestion` fields
   (defaults `None`), so every existing form is unaffected.
3. **Reuse the answer path.** Map the new type's answer validation to an
   existing validator in `bridge.py::_validate_answer` if the answer is
   shaped like one already (a decision validates as a single-select).
   Only add validation logic for a genuinely new answer shape.
4. **Render it.** Add a branch to `widget.py::_control_html` (and the
   submit-script reader if the control isn't a plain input), plus any
   styles. Keep the `sendPrompt` guard so it degrades to a readable
   static card.
5. **Definition validation.** Extend `bridge.py::form_from_dict` to
   parse and validate the new fields (e.g. a referenced option must
   exist).
6. **Surfaces.** Widen the rich enum in `mcp/tool_schemas.py` (update
   the count guard in `tests/unit/mcp/test_tool_schemas.py`), map it in
   `elicitation_schema.py` if native elicitation should carry it, and
   document the construct + its `AskUserQuestion` fallback in the
   `elicit` skill (both `plugin/` and `.agents/` copies).
7. **Prove it.** Add a test module under `tests/unit/elicitation/`
   (model + definition validation + render + round-trip + fallback) and
   **dogfood the live widget round-trip** — render a real form, submit,
   and validate the postback (the receipt). The widget path makes no
   Anthropic API call, so this is provable without credits.

### Track B — a new display member (widget kernel)

`chartkit` is the worked example; `formkit` / `infokit` are the
specified next two. Do **not** touch `FormSchema`, `QuestionType`, or
`bridge.py::_validate_answer` — a display member has no answer.

1. **Write the spec schema first.** `spec.schema.json` is the contract
   between model and kernel. Keep it small enough that authoring costs
   ~50–200 tokens; that budget is the point of the pattern.
2. **Build the kernel sealed.** One directory under
   `src/attune/widgets/<kind>kit/`, its source importing nothing outside
   itself and nothing importing its internals. Hold a size budget and
   state it (chartkit: 6.7KB).
3. **Support patch updates.** `<kind>_id` + RFC 7386 merge patch against
   the stored spec, so an update costs a patch rather than a re-render.
   Persistence must degrade legibly — when it is unavailable, say so and
   require a full spec.
4. **Expose one MCP tool** in `mcp/tool_schemas.py` returning
   `{"success", "html", ...}` for `show_widget`, with a thin delegating
   handler in `mcp/server.py`. Update the tool-count guard in
   `tests/unit/mcp/test_tool_schemas.py` **and** the README's MCP tool
   list (its counts are not cap-marked, so no gate catches them).
5. **Errors are field-level at author time** — `encodings.x.field: Field
   required`, not a generic failure. That is this substrate's version of
   re-asking only the offending field.
6. **Prove it by rendering.** Kernel unit tests plus a boundary test
   that the seal holds, and dogfood one live render — the receipt is a
   widget that actually draws, not a schema that validates.
7. **Document it here** as the next `v<N>` display member, and add its
   row to the class table in "What this is".

---

## Cross-references

- [decision-routine.md](decision-routine.md) — when the decision
  construct fires (the trigger discipline; this file is the shape).
- `plugin/skills/elicit/SKILL.md` — the live skill that drives the
  substrate and carries the per-surface mapping rules.
- [docs/specs/elicitation-form-surface/](../../../docs/specs/elicitation-form-surface/)
  — the full decision log (D1–D14) and phase requirements.
- [docs/specs/widget-kernel-family/](../../../docs/specs/widget-kernel-family/)
  — the display substrate: the sealed-kernel pattern, the latency model,
  and the `formkit` / `infokit` roadmap.
- `src/attune/widgets/chartkit/` — the shipped display kernel;
  `spec.schema.json` is the model-facing contract.
