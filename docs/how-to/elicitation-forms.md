# Elicitation Forms

## Quickstart

Build a form from plain data, render it to the widget surface, and
validate the answer that posts back:

```python
from attune.elicitation import (
    form_from_dict,
    form_to_widget_html,
    collect_form_response,
)

form = form_from_dict({
    "title": "Release plan",
    "fields": [{
        "id": "bump",
        "text": "Which version bump?",
        "type": "decision",
        "options": ["patch", "minor", "major"],
        "recommended": "minor",
        "rationale": "Three additive features since the last tag.",
        "option_notes": {"minor": "new API, backward-compatible"},
    }],
})

html = form_to_widget_html(form)          # pass straight to show_widget
# … the user picks an option; the widget posts {"bump": "minor"} back …
response = collect_form_response(form, {"bump": "minor"})
assert response.responses["bump"] == "minor"
```

## Tasks

### Render a decision

A recommended option with a rationale and per-option tradeoffs, rendered
as cards (recommended badged and ordered first):

```python
form = form_from_dict({
    "title": "Approval",
    "fields": [{
        "id": "gate", "text": "High-severity gate failed — proceed?",
        "type": "decision",
        "options": ["Fix and retry", "Approve and continue"],
        "recommended": "Fix and retry",
        "rationale": "Two findings are unverified.",
    }],
})
```

### Render a pushback

Disagreement framed as dissent — the user's approach beside the agent's
alternative, under a "why I'd push back" rationale:

```python
form = form_from_dict({
    "title": "Approach",
    "fields": [{
        "id": "call", "text": "Build it how?",
        "type": "pushback",
        "options": ["Hand-roll a parser", "Reuse the existing one"],
        "user_position": "Hand-roll a parser",
        "recommended": "Reuse the existing one",
        "rationale": "The existing parser already handles every case here.",
    }],
})
```

### Render a progress report with a blocked-item picker

`progress_items` carries every item by status; the blocked subset must
equal `options` (the picker). When nothing is blocked, the construct
degrades to a pure status display with no answer:

```python
form = form_from_dict({
    "title": "Where we are",
    "fields": [{
        "id": "next", "text": "Which blocker first?",
        "type": "progress",
        "options": ["Fix the failing lane"],
        "recommended": "Fix the failing lane",
        "progress_items": [
            {"label": "Spec drafted", "status": "done"},
            {"label": "Tests written", "status": "in_flight"},
            {"label": "Fix the failing lane", "status": "blocked"},
        ],
    }],
})
```

### Render a select as a numbered list

```python
form = form_from_dict({
    "title": "Delivery",
    "fields": [{
        "id": "fmt", "text": "Pick a format:",
        "type": "single_select",
        "options": ["Bulleted brief", "Numbered steps", "Markdown table"],
        "list_style": "ordered",
    }],
})
```

## Reference

### Public API — `attune.elicitation`

| Symbol | Purpose |
|--------|---------|
| `form_from_dict(data)` | Build and validate a `FormSchema` from plain data; raises `FormValidationError` on a malformed definition. |
| `form_to_widget_html(form, message="")` | Render the rich inline HTML form for `show_widget`. |
| `form_to_askuserquestion(form, batch_size=4)` | Render batched `AskUserQuestion` payloads (the fallback surface). |
| `form_to_elicitation_schema(form)` | Render a native MCP elicitation JSON schema. |
| `select_form_surface(form, widget_capable=True, keyboard_mode=False)` | Choose the surface: `"widget"` (the default) or `"ask"`. |
| `is_trivial_form(form)` | True when a form is small enough that buttons lose nothing: one select/boolean, ≤3 options, no label >120 chars. |
| `keyboard_mode_enabled(project_root=None)` | Read the per-project opt-out (`keyboard_mode` in `./attune.config.json`; `ATTUNE_KEYBOARD_MODE` overrides). |
| `set_keyboard_mode(enabled, project_root=None)` | Persist the opt-out; what `attune config set keyboard_mode` calls. Preserves other keys. |
| `form_response_summary(form, response)` | Collapse an answered form to a compact markdown summary. |
| `is_fully_inferred(form)` | True when every field's value was inferred — the form renders as a one-tap confirmation. |
| `inferred_field_count(form)` | How many fields carry an inferred value. |
| `needs_widget(form)` | Low-level controls check — True if `AskUserQuestion` would lose fidelity. Does not own the surface decision. |
| `collect_form_response(form, raw_answers, template_id="")` | Validate answers (R4) and return a `FormResponse`; raises `FormValidationError`. |
| `WIDGET_RESPONSE_MARKER` | The sentinel key the widget posts back under. |
| `FormValidationError` | Raised for a malformed definition or answer; lists every problem. |

### `QuestionType` values

`text_input`, `textarea`, `single_select`, `multi_select`, `boolean`,
`number` (with `minimum` / `maximum`), `date` (`YYYY-MM-DD`), and the
three construct types `decision`, `pushback`, `progress` — ten in all.

### Construct-specific `FormQuestion` fields

| Field | Used by | Meaning |
|-------|---------|---------|
| `recommended` | decision / pushback / progress | option to badge and order first; must be in `options` |
| `rationale` | decision / pushback / progress | the "why" callout |
| `option_notes` | decision / pushback | `{option: one-line tradeoff}` |
| `user_position` | pushback | the option that is the user's stated approach |
| `progress_items` | progress | `{label, status, detail?}` items; blocked subset must equal `options` |
| `list_style` | single_select / multi_select | `"ordered"` or `"unordered"` list render |

### MCP tools

`elicitation_render_form`, `elicitation_render_widget`,
`elicitation_collect_response`, and `elicitation_ask` — the same model,
exposed for agents that drive forms through the MCP server.

<!-- attune-generated: source_hash=65dd2400b49b9d8a20605f411f62b72c1ae2d9d530b8730bb0db0acfef04fb59 feature=elicitation-forms kind=how-to generated_at=2026-07-25 -->
