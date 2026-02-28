"""Agent template system for meta-orchestration.

This package provides reusable agent archetypes that can be customized
for specific tasks. Templates define agent capabilities, tools, and
quality gates.

Security:
    - All template fields validated on creation
    - No eval() or exec() usage
    - Input sanitization on template lookup

Example:
    >>> template = get_template("test_coverage_analyzer")
    >>> print(template.role)
    Test Coverage Expert

    >>> templates = get_templates_by_capability("analyze_gaps")
    >>> print([t.id for t in templates])
    ['test_coverage_analyzer']

"""

# Import builtin_templates to trigger registration
from . import builtin_templates as _builtin_templates
from .models import AgentCapability, AgentTemplate, ResourceRequirements
from .registry import (
    get_all_templates,
    get_registry,
    get_template,
    get_templates_by_capability,
    get_templates_by_tier,
    register_custom_template,
    unregister_template,
)

__all__ = [
    "AgentCapability",
    "AgentTemplate",
    "ResourceRequirements",
    "get_all_templates",
    "get_registry",
    "get_template",
    "get_templates_by_capability",
    "get_templates_by_tier",
    "register_custom_template",
    "unregister_template",
]
