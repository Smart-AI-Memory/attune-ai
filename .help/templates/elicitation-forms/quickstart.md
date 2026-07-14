---
type: quickstart
name: elicitation-forms-quickstart
feature: elicitation-forms
depth: quickstart
generated_at: 2026-07-14T15:58:51.698621+00:00
source_hash: ea2a2694719d75bff1894657cfe5e0f5c96ae71719ae4d7f00ce7252b9e9798a
status: generated
---

# Dynamic forms and the agent-to-user communication grammar

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
