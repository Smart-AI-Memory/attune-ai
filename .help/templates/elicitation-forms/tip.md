---
type: tip
name: elicitation-forms-tip
feature: elicitation-forms
depth: tip
generated_at: 2026-09-06T00:35:04.869548+00:00
source_hash: 9162a67905eb555cfdd3b260da2b35f34972ceed46c693d35319d40e7370db18
status: generated
---

# Dynamic forms and the agent-to-user communication grammar

## Notes & tips

- Infer before you ask. If the answer is already in the conversation,
  skip the form and proceed — a one-question form beats five where four
  are already answerable.
- Use `recommended` to lead with a stated preference; the fallback surface
  orders it first.
- Keep option labels short. For richer options, the widget surface shows
  `option_notes` under each card.
- `options` is a list of plain strings — per-option detail never nests
  inside it. A dict in `options` fails validation; the notes belong in
  `option_notes` keyed by the option string, and the recommendation in
  `recommended` (which must match one of the options exactly).
- Any key the parser does not read — top-level or field-level — is a
  definition **error**, not ignorable extra data (a typo'd key would
  otherwise silently drop the bound it meant to declare). If
  `form_from_dict` rejects a key you expected to work, check the
  Quickstart example for the canonical spelling.
- To try a form without wiring a surface: the live demos at
  [smartaimemory.com/forms-demo/audit.html](https://smartaimemory.com/forms-demo/audit.html)
  and
  [smartaimemory.com/forms-demo/retro.html](https://smartaimemory.com/forms-demo/retro.html)
  are these exact renderers on static pages
  (`scripts/render_demo_forms.py` regenerates them).
