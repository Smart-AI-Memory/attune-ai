---
type: task
name: elicitation-forms-task
feature: elicitation-forms
depth: task
generated_at: 2026-08-29T23:25:57.407014+00:00
source_hash: adc929d111b4cf4bf48479bf6b325ab34d6f63740017d7fc0df1383da12ed22e
status: generated
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
