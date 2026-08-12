# Elicitation Forms

## Reference

### Public API — `attune.elicitation`

The implementation lives in the standalone `attune-forms` package;
`attune.elicitation` re-exports it unchanged and remains the
supported import path inside attune-ai.

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

<!-- attune-generated: source_hash=1d0bd5af58687db6aab66d7cc8fc7057e34be8f79d6c76e2ef2e46758496302b feature=elicitation-forms kind=reference generated_at=2026-08-12 -->
