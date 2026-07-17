# Elicitation Form Surface — Design (v1)

**Status:** v1 shipped (verified 2026-07-14); v2+ status tracked in [requirements.md](requirements.md)

Design for the [requirements](requirements.md), post-Phase 0. Surface
decision is [decisions.md](decisions.md) **D4**: AskUserQuestion-first,
elicitation rejected, widget deferred. v1 = a declarative-form artifact
(D3) + a renderer onto `AskUserQuestion` + a rule that says *when* to
batch fields into one multi-question turn. No new infrastructure.

## 1. The form artifact (D3 — form as data)

A form is a serializable object — never imperative agent code — so the
same artifact can render today, be human-authored later, and bind to
data later (North star), at no extra cost now.

```python
Form     = {title: str, fields: list[Field]}
Field    = {
    id: str,                 # stable key in the result
    label: str,              # the question text shown
    type: "select" | "multiselect" | "text",   # v1 types
    options: list[str] = [], # for (multi)select; 0 for text
    required: bool = True,
    default: str | list[str] | None = None,
    help: str | None = None,
}
```

v1 renders **select / multiselect / text**. `slider`, `date`,
`number`, `color` are valid artifact types but **out of v1** (no
portable AskUserQuestion control — deferred to the widget enhancement);
the renderer rejects them with a clear error rather than silently
coercing.

## 2. Renderer — form → `AskUserQuestion`

Mapping rules:

- **field → question.** Each field becomes one entry in the
  `questions` array; `id` keys the returned answer.
- **type → control.** `select` → `multiSelect: false`; `multiselect`
  → `multiSelect: true`; `text` → a question whose options are any
  curated suggestions plus the built-in **"Other" free-text** escape
  (the only way to collect arbitrary text on this surface in v1).
- **≤4 fields per call.** `AskUserQuestion` takes 1–4 questions. A form
  with >4 fields renders as **sequential passes** of ≤4 (the result is
  still one merged object). v1 may cap forms at 4 fields and revisit.
- **2–4 options per question.** A (multi)select field with >4 options
  uses the established **two-tier picker** (category → item) rather than
  overflowing — reuses the existing large-catalog pattern.
- **recommendation-first.** Per `feedback_question_shape`, each field's
  first option is the recommended one (label ends "(Recommended)").

## 3. Result + validation (R1, R4)

`AskUserQuestion` returns `answers` keyed by question text; the renderer
maps it back to a `{field.id: value}` object (value = str for select,
list[str] for multiselect, str for text/Other). Before the flow
consumes it, validate types + `required` against the artifact; a
missing required field re-asks just that field, never silently passes
malformed input.

## 4. When to render a multi-field form (the rule relaxation)

This is the behavioral change and the part needing sign-off. Today's
`feedback_question_shape` rule is "ask ONE question per turn." The
relaxation:

**Batch 2–4 fields into one form-turn only when ALL hold:**

- the fields are **independent dimensions of one decision** the user
  must make together (e.g. spec kickoff: outcome + approach +
  concerns), AND
- answers **don't branch** on each other (no field's relevance depends
  on another's answer — branching ⇒ stay sequential), AND
- each field is **genuinely ambiguous/unknown** per the sibling rule
  `socratic-ambiguity-calibration` — a field the user already specified
  is omitted, not asked.

**Stay single-question when** only one dimension is genuinely unknown,
or a later question depends on an earlier answer, or batching would
feel like a bureaucratic intake for a simple ask.

Composition, stated plainly: **`socratic-ambiguity-calibration` decides
*which* fields are worth asking; this form decides *whether* those
fields are batched into one turn or asked one at a time.** The form
never adds fields the ambiguity rule wouldn't already ask.

## 5. First integrated flow (G3)

Recommendation: the **`/attune` Socratic discovery scoping turn** — the
headline differentiator and the most frequent genuine multi-dimension
intake (goal + scope + focus, today asked as sequential buttons). It is
the cleanest demonstration of "N button-turns → one form" and exercises
multiselect (focus/concerns) natively. Dogfood it end-to-end (R5) —
a real round-trip, not a mock.

## 6. Out of v1 (deferred)

- Rich controls with no AskUserQuestion home: slider, date, number,
  color → the widget-enhancement phase (off the *same* artifact).
- User-authored forms + data-bound options (North star).
- The widget surface itself (fragile post-back return — D4).

## Open — for sign-off

- **First-target flow** — `/attune` discovery recommended (§5); confirm
  or redirect (wizard step / `/spec` intake are alternatives).
- **Rule-relaxation criteria** (§4) — the behavioral change; needs
  explicit OK, since it edits attune's Socratic question-shape habit.

## 7. Reference form — every control type (freeze-safe V7 precursor)

`attune.elicitation.reference_form` is the single code-verified example
of a *complete* declarative form: exactly one field per `QuestionType`
member (all ten — the four v1 controls, the three v2.1 rich controls,
and the v3–v5 constructs), each with realistic values, paired with
valid `EXAMPLE_ANSWERS`.

```python
from attune.elicitation import (
    REFERENCE_FORM,
    EXAMPLE_ANSWERS,
    form_from_dict,
    collect_form_response,
)

form = form_from_dict(REFERENCE_FORM)
response = collect_form_response(form, EXAMPLE_ANSWERS)
```

It is a plain data constant — **not** a template-store entry or a
`form_from_template` call. That mechanism is the V7 template library,
design-frozen until 2026-07-28; this reference is the freeze-safe
precursor that becomes V7's first stored template verbatim when the
freeze lifts.

`tests/unit/elicitation/test_reference_form.py` guards it: a
completeness test fails CI if a new `QuestionType` is added without a
field here, so the reference cannot silently fall behind the grammar.
The same test proves the definition validates, the answers round-trip,
a missing required answer is rejected (R4), and the form casts to all
three surfaces (`widget` / `AskUserQuestion` / native elicitation).
