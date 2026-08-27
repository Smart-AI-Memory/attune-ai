"""Wizard registry and discovery.

Maintains a registry of wizard classes, supports both programmatic
registration, entry-point-based auto-discovery, and custom YAML wizards.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from attune.security.path_validation import _validate_file_path

if TYPE_CHECKING:
    from .base import BaseWizard, WizardConfig

logger = logging.getLogger(__name__)

# =========================================================================
# Registry
# =========================================================================

_WIZARD_REGISTRY: dict[str, type[BaseWizard]] = {}

# Separate store for config-driven wizard *instances* (not classes)
_CUSTOM_WIZARD_INSTANCES: dict[str, Any] = {}

# Default directory for custom wizard YAML files
CUSTOM_WIZARDS_DIR = Path(".attune") / "wizards"


def register_wizard(wizard_id: str, wizard_class: type[BaseWizard]) -> None:
    """Register a wizard class.

    Args:
        wizard_id: Short identifier (e.g. ``"debug"``).
        wizard_class: The wizard class to register.

    """
    _WIZARD_REGISTRY[wizard_id] = wizard_class
    logger.debug("Registered wizard: %s", wizard_id)


def get_wizard(wizard_id: str) -> type[BaseWizard] | None:
    """Get a wizard class by ID.

    Checks the in-memory registry first, then falls back to
    entry-point discovery, built-in loading, and custom YAML loading.

    Args:
        wizard_id: Short identifier.

    Returns:
        Wizard class or ``None`` if not found.

    """
    if wizard_id in _WIZARD_REGISTRY:
        return _WIZARD_REGISTRY[wizard_id]

    # Try entry point discovery and built-in loading
    _load_builtins()
    _load_custom_wizards()
    return _WIZARD_REGISTRY.get(wizard_id)


def list_wizards() -> list[WizardConfig]:
    """List all registered wizard configs.

    Returns:
        List of ``WizardConfig`` sorted by wizard_id.

    """
    _load_builtins()
    _load_custom_wizards()

    configs: list[WizardConfig] = []
    for wizard_class in _WIZARD_REGISTRY.values():
        if hasattr(wizard_class, "config"):
            configs.append(wizard_class.config)

    configs.sort(key=lambda c: c.wizard_id)
    return configs


# =========================================================================
# Custom wizard lifecycle
# =========================================================================


def save_custom_wizard(wizard_data: dict[str, Any], base_dir: str | None = None) -> Path:
    """Save a custom wizard definition to YAML.

    Args:
        wizard_data: Wizard definition dict (must include ``wizard_id``, ``name``, ``steps``).
        base_dir: Directory to save into. Defaults to ``.attune/wizards/``.

    Returns:
        Path where the YAML file was written.

    Raises:
        ValueError: If the data is invalid or path targets a system directory.

    """
    from .config_driven import ConfigDrivenWizard, _validate_schema

    _validate_schema(wizard_data)

    wizard_id = wizard_data["wizard_id"]
    target_dir = Path(base_dir) if base_dir else CUSTOM_WIZARDS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / f"{wizard_id}.yaml"
    validated = _validate_file_path(str(output_path))

    try:
        with validated.open("w", encoding="utf-8") as f:
            yaml.safe_dump(wizard_data, f, default_flow_style=False, sort_keys=False)
    except PermissionError as e:
        logger.error("Permission denied writing wizard to %s: %s", validated, e)
        raise
    except OSError as e:
        logger.error("OS error writing wizard to %s: %s", validated, e)
        raise ValueError(f"Cannot write wizard YAML: {e}") from e

    # Register the new wizard
    wizard = ConfigDrivenWizard._from_dict(wizard_data)
    _WIZARD_REGISTRY[wizard_id] = type(wizard)
    _CUSTOM_WIZARD_INSTANCES[wizard_id] = wizard

    logger.info("Saved custom wizard '%s' to %s", wizard_id, validated)
    return validated


def delete_custom_wizard(wizard_id: str, base_dir: str | None = None) -> bool:
    """Delete a custom wizard definition.

    Removes the YAML file and unregisters from the registry.
    Built-in wizards cannot be deleted.

    Args:
        wizard_id: Wizard ID to delete.
        base_dir: Directory to look in. Defaults to ``.attune/wizards/``.

    Returns:
        ``True`` if the wizard was deleted, ``False`` if not found.

    Raises:
        ValueError: If attempting to delete a built-in wizard.

    """
    # Protect built-in wizards
    try:
        from .builtin import BUILTIN_WIZARDS

        if wizard_id in BUILTIN_WIZARDS:
            raise ValueError(f"Cannot delete built-in wizard: '{wizard_id}'")
    except ImportError:
        pass

    target_dir = Path(base_dir) if base_dir else CUSTOM_WIZARDS_DIR
    yaml_path = target_dir / f"{wizard_id}.yaml"

    deleted = False
    if yaml_path.exists():
        yaml_path.unlink()
        deleted = True
        logger.info("Deleted wizard file: %s", yaml_path)

    # Remove from registries
    _WIZARD_REGISTRY.pop(wizard_id, None)
    _CUSTOM_WIZARD_INSTANCES.pop(wizard_id, None)

    return deleted


# =========================================================================
# Discovery
# =========================================================================


def _load_builtins() -> None:
    """Load built-in wizards into the registry if not already loaded."""
    if "debug" in _WIZARD_REGISTRY:
        return  # Already loaded

    try:
        from .builtin import BUILTIN_WIZARDS

        for wizard_id, wizard_class in BUILTIN_WIZARDS.items():
            if wizard_id not in _WIZARD_REGISTRY:
                _WIZARD_REGISTRY[wizard_id] = wizard_class
    except ImportError:
        logger.debug("Built-in wizards not available")


_custom_loaded = False


def _load_custom_wizards() -> None:
    """Load custom wizards from YAML files in ``.attune/wizards/``.

    Only runs once per process.
    """
    global _custom_loaded
    if _custom_loaded:
        return
    _custom_loaded = True

    if not CUSTOM_WIZARDS_DIR.exists():
        return

    from .config_driven import ConfigDrivenWizard

    for yaml_path in sorted(CUSTOM_WIZARDS_DIR.glob("*.yaml")):
        try:
            wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))
            wizard_id = wizard.config.wizard_id
            if wizard_id not in _WIZARD_REGISTRY:
                _WIZARD_REGISTRY[wizard_id] = type(wizard)
                _CUSTOM_WIZARD_INSTANCES[wizard_id] = wizard
                logger.debug("Loaded custom wizard: %s from %s", wizard_id, yaml_path)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Custom wizard loading is best-effort
            logger.warning("Failed to load custom wizard from %s: %s", yaml_path, e)
