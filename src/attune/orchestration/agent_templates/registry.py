"""Template registry for agent templates.

Provides storage and lookup functions for agent templates.
Templates are stored in a global registry and can be queried
by ID, capability, or tier.

Example:
    >>> from attune.orchestration.agent_templates.registry import get_template
    >>> template = get_template("test_coverage_analyzer")
    >>> print(template.role)
    Test Coverage Expert
"""

import logging

from .models import AgentTemplate

logger = logging.getLogger(__name__)

# Registry of pre-built agent templates
_TEMPLATE_REGISTRY: dict[str, AgentTemplate] = {}


def _register_template(template: AgentTemplate) -> None:
    """Register a template in the global registry.

    Args:
        template: Template to register

    Raises:
        ValueError: If template with same ID already registered
    """
    if template.id in _TEMPLATE_REGISTRY:
        raise ValueError(f"Template '{template.id}' already registered")
    _TEMPLATE_REGISTRY[template.id] = template
    logger.debug(f"Registered template: {template.id}")


def get_template(template_id: str) -> AgentTemplate | None:
    """Retrieve template by ID.

    Args:
        template_id: Template identifier

    Returns:
        Template if found, None otherwise

    Example:
        >>> template = get_template("test_coverage_analyzer")
        >>> print(template.role)
        Test Coverage Expert
    """
    if not template_id or not isinstance(template_id, str):
        logger.warning(f"Invalid template_id: {template_id}")
        return None
    return _TEMPLATE_REGISTRY.get(template_id)


def get_all_templates() -> list[AgentTemplate]:
    """Retrieve all registered templates.

    Returns:
        List of all templates

    Example:
        >>> templates = get_all_templates()
        >>> len(templates) >= 13
        True
    """
    return list(_TEMPLATE_REGISTRY.values())


def get_templates_by_capability(capability: str) -> list[AgentTemplate]:
    """Retrieve templates with a specific capability.

    Args:
        capability: Capability name to search for

    Returns:
        List of templates with that capability

    Example:
        >>> templates = get_templates_by_capability("analyze_gaps")
        >>> any(t.id == "test_coverage_analyzer" for t in templates)
        True
    """
    if not capability or not isinstance(capability, str):
        logger.warning(f"Invalid capability: {capability}")
        return []

    return [
        template for template in _TEMPLATE_REGISTRY.values() if capability in template.capabilities
    ]


def get_templates_by_tier(tier: str) -> list[AgentTemplate]:
    """Retrieve templates preferring a specific tier.

    Args:
        tier: Tier name ("CHEAP", "CAPABLE", "PREMIUM")

    Returns:
        List of templates preferring that tier

    Example:
        >>> templates = get_templates_by_tier("CAPABLE")
        >>> len(templates) > 0
        True
    """
    if tier not in AgentTemplate.ALLOWED_TIERS:
        logger.warning(f"Invalid tier: {tier}")
        return []

    return [
        template for template in _TEMPLATE_REGISTRY.values() if template.tier_preference == tier
    ]


def register_custom_template(template: AgentTemplate) -> None:
    """Register a user-defined template at runtime.

    Unlike the internal ``_register_template``, this function allows
    overwriting an existing template (useful for customization).

    Args:
        template: Template to register.

    Raises:
        ValueError: If template validation fails.
    """
    _TEMPLATE_REGISTRY[template.id] = template
    logger.info(f"Registered custom template: {template.id}")


def unregister_template(template_id: str) -> bool:
    """Remove a template from the registry.

    Args:
        template_id: ID of the template to remove.

    Returns:
        True if removed, False if not found.
    """
    if template_id in _TEMPLATE_REGISTRY:
        del _TEMPLATE_REGISTRY[template_id]
        logger.info(f"Unregistered template: {template_id}")
        return True
    return False


def get_registry() -> dict[str, AgentTemplate]:
    """Return a read-only snapshot of the template registry.

    Returns:
        Dict mapping template IDs to templates.
    """
    return dict(_TEMPLATE_REGISTRY)
