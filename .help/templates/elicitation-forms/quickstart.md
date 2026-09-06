---
type: quickstart
name: elicitation-forms-quickstart
feature: elicitation-forms
depth: quickstart
generated_at: 2026-09-06T00:35:04.869548+00:00
source_hash: 9162a67905eb555cfdd3b260da2b35f34972ceed46c693d35319d40e7370db18
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
