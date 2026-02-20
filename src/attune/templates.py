"""Template Starters for Attune AI -- Facade Module.

This module re-exports the public API that was originally defined
here before the refactor into focused modules:

- template_defs_basic  -- minimal and python-cli template data
- template_defs_web    -- python-fastapi and python-agent template data
- template_engine      -- scaffolding logic, CLI handler, registry

All original imports (TEMPLATES, list_templates, scaffold_project,
cmd_new) continue to work unchanged.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.template_engine import (
    TEMPLATES,
    cmd_new,
    list_templates,
    scaffold_project,
)

__all__ = [
    "TEMPLATES",
    "cmd_new",
    "list_templates",
    "scaffold_project",
]
