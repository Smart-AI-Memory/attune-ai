"""HTML Template Rendering for Socratic Web UI

Provides functions for rendering Socratic forms as HTML pages,
including field rendering, escaping, and complete page generation.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json

from .assets import FORM_CSS, FORM_JS
from .forms import FieldType, Form, FormField
from .react_schemas import ReactSessionSchema
from .session import SocraticSession


def render_form_html(form: Form, action_url: str = "/api/socratic/submit") -> str:
    """Render a form as HTML.

    Args:
        form: Form to render
        action_url: Form submission URL

    Returns:
        HTML string
    """
    html_parts = [
        f'<form id="{form.id}" action="{action_url}" method="POST" class="socratic-form">',
        '  <div class="form-header">',
        f"    <h2>{_escape_html(form.title)}</h2>",
        f'    <p class="form-description">{_escape_html(form.description)}</p>',
        '    <div class="progress-bar">',
        f'      <div class="progress-fill" style="width: {form.progress * 100}%"></div>',
        f'      <span class="progress-text">{form.progress:.0%}</span>',
        "    </div>",
        "  </div>",
        '  <div class="form-fields">',
    ]

    # Group fields by category
    fields_by_category = form.get_fields_by_category()

    for category, fields in fields_by_category.items():
        if len(fields_by_category) > 1:
            html_parts.append(f'    <fieldset class="field-category" data-category="{category}">')
            html_parts.append(f"      <legend>{category.title()}</legend>")

        for field in fields:
            html_parts.append(_render_field_html(field))

        if len(fields_by_category) > 1:
            html_parts.append("    </fieldset>")

    html_parts.extend(
        [
            "  </div>",
            '  <div class="form-actions">',
            '    <button type="submit" class="btn-primary">Continue</button>',
            "  </div>",
            "</form>",
        ]
    )

    return "\n".join(html_parts)


def _render_field_html(field: FormField) -> str:
    """Render a single field as HTML."""
    required = "required" if field.validation.required else ""
    required_indicator = '<span class="required">*</span>' if field.validation.required else ""

    # Show when data attribute
    show_when = ""
    if field.show_when:
        show_when = f" data-show-when='{json.dumps(field.show_when)}'"

    parts = [
        f'    <div class="form-field" data-field-id="{field.id}"{show_when}>',
        f'      <label for="{field.id}">{_escape_html(field.label)}{required_indicator}</label>',
    ]

    if field.help_text:
        parts.append(f'      <p class="help-text">{_escape_html(field.help_text)}</p>')

    # Render input based on type
    if field.field_type == FieldType.SINGLE_SELECT:
        parts.append('      <div class="radio-group">')
        for opt in field.options:
            rec_class = " recommended" if opt.recommended else ""
            parts.append(f'        <label class="radio-option{rec_class}">')
            parts.append(
                f'          <input type="radio" name="{field.id}" value="{opt.value}" {required}>'
            )
            parts.append(f'          <span class="option-label">{_escape_html(opt.label)}</span>')
            if opt.description:
                parts.append(
                    f'          <span class="option-desc">{_escape_html(opt.description)}</span>'
                )
            parts.append("        </label>")
        parts.append("      </div>")

    elif field.field_type == FieldType.MULTI_SELECT:
        parts.append('      <div class="checkbox-group">')
        for opt in field.options:
            rec_class = " recommended" if opt.recommended else ""
            parts.append(f'        <label class="checkbox-option{rec_class}">')
            parts.append(f'          <input type="checkbox" name="{field.id}" value="{opt.value}">')
            parts.append(f'          <span class="option-label">{_escape_html(opt.label)}</span>')
            if opt.description:
                parts.append(
                    f'          <span class="option-desc">{_escape_html(opt.description)}</span>'
                )
            parts.append("        </label>")
        parts.append("      </div>")

    elif field.field_type == FieldType.TEXT_AREA:
        max_len = (
            f' maxlength="{field.validation.max_length}"' if field.validation.max_length else ""
        )
        parts.append(
            f'      <textarea id="{field.id}" name="{field.id}" placeholder="{_escape_html(field.placeholder)}"{max_len} {required}></textarea>'
        )

    elif field.field_type == FieldType.BOOLEAN:
        parts.append('      <div class="switch-container">')
        parts.append('        <label class="switch">')
        parts.append(
            f'          <input type="checkbox" id="{field.id}" name="{field.id}" value="true">'
        )
        parts.append('          <span class="slider"></span>')
        parts.append("        </label>")
        parts.append("      </div>")

    elif field.field_type == FieldType.SLIDER:
        min_val = field.validation.min_value or 0
        max_val = field.validation.max_value or 100
        parts.append('      <div class="slider-container">')
        parts.append(
            f'        <input type="range" id="{field.id}" name="{field.id}" min="{min_val}" max="{max_val}">'
        )
        parts.append(f'        <output for="{field.id}"></output>')
        parts.append("      </div>")

    else:  # TEXT, NUMBER
        input_type = "number" if field.field_type == FieldType.NUMBER else "text"
        max_len = (
            f' maxlength="{field.validation.max_length}"' if field.validation.max_length else ""
        )
        parts.append(
            f'      <input type="{input_type}" id="{field.id}" name="{field.id}" placeholder="{_escape_html(field.placeholder)}"{max_len} {required}>'
        )

    parts.append("    </div>")

    return "\n".join(parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def render_complete_page(form: Form, session: SocraticSession) -> str:
    """Render a complete HTML page with form.

    Args:
        form: Form to render
        session: Current session

    Returns:
        Complete HTML page
    """
    form_html = render_form_html(form)
    session_data = ReactSessionSchema.from_session(session)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Socratic Workflow Builder</title>
    <style>
{FORM_CSS}
    </style>
</head>
<body>
    <div class="container">
        <div class="session-info">
            <span class="domain-badge">{session_data.domain or "General"}</span>
            <span class="confidence">Confidence: {session_data.confidence:.0%}</span>
        </div>

        {form_html}
    </div>

    <script>
{FORM_JS}

// Session data for client-side use
window.socraticSession = {session_data.to_json()};
    </script>
</body>
</html>"""
