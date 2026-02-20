"""Web UI Components for Socratic Workflow Builder

Provides components for rendering Socratic forms in web interfaces:
- React component schemas
- HTML template rendering
- API endpoint helpers
- WebSocket support for real-time sessions

This module re-exports all public APIs from the focused submodules:
- react_schemas: ReactFormSchema, ReactSessionSchema, ReactBlueprintSchema
- html_renderer: render_form_html, render_complete_page, _escape_html
- assets: FORM_CSS, FORM_JS, get_form_assets
- api_helpers: APIResponse, create_form_response, create_blueprint_response

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

# API helpers
from .api_helpers import APIResponse, create_blueprint_response, create_form_response

# CSS and JavaScript assets
from .assets import FORM_CSS, FORM_JS, get_form_assets

# HTML rendering
from .html_renderer import _escape_html, _render_field_html, render_complete_page, render_form_html

# React schemas
from .react_schemas import (
    ReactBlueprintSchema,
    ReactFormSchema,
    ReactSessionSchema,
    _field_type_to_component,
)

__all__ = [
    # React schemas
    "ReactFormSchema",
    "ReactSessionSchema",
    "ReactBlueprintSchema",
    "_field_type_to_component",
    # HTML rendering
    "render_form_html",
    "render_complete_page",
    "_render_field_html",
    "_escape_html",
    # Assets
    "FORM_CSS",
    "FORM_JS",
    "get_form_assets",
    # API helpers
    "APIResponse",
    "create_form_response",
    "create_blueprint_response",
]
