---
name: elicitation-forms
source: content/features/elicitation-forms.md
tags:
- elicitation
- forms
- communication
- ux
- widget
type: task
---

# Dynamic forms and the agent-to-user communication grammar

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

### Cast a stored template

From Python, name the template and supply one string per declared slot;
the result is a validated `FormSchema` like any other:

```python
from attune.elicitation import form_from_template, list_templates

list_templates()                     # ['session-contract', ...]
form = form_from_template("session-contract", {"project": "attune-ai"})
form.title                           # 'Session contract — attune-ai'
```

Over MCP, pass `template` + `slots` INSTEAD of `form` to any form-taking
tool — the cast, validation, and render all happen server-side:

```json
{"template": "session-contract", "slots": {"project": "attune-ai"},
 "message": "Fill before non-trivial work."}
```

`elicitation_render_widget` returns the same `{success, html, title,
field_ids}` it returns for a `form`; `elicitation_collect_response`
takes the same `template` + `slots` beside `answers` and echoes
`template_id`. Passing both `form` and `template`, neither, or `slots`
without `template` comes back as a listed problem, never a raise. An
unknown name lists the available templates.

### Preview every stored template

The authoring preview renders every stored template — cast with its
`example_slots` — through the production widget renderer into one
standalone page, light and dark, with the payload the widget posts
shown on submit:

```bash
python -m attune_forms.preview --open          # every template
python -m attune_forms.preview session-contract --out preview.html
```

Edit a template, reload, and see exactly what users will see. Preview
casts do not count toward the form telemetry.
