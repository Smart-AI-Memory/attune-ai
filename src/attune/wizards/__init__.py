"""XML-Enhanced Wizard System for Attune AI.

Provides interactive, multi-step wizards that combine guided flows,
XML task decomposition, and template-driven generation.

Usage:
    from attune.wizards import BaseWizard, WizardConfig, WizardStep, StepType
    from attune.wizards import list_wizards, get_wizard

    # List available wizards
    for config in list_wizards():
        print(f"{config.wizard_id}: {config.name} ({config.source})")

    # Run a built-in wizard
    wizard_cls = get_wizard("debug")
    wizard = wizard_cls(ask_user_callback=my_callback)
    result = await wizard.run({"error": "TypeError: ..."})

    # Create a custom wizard from YAML
    from attune.wizards import ConfigDrivenWizard
    wizard = ConfigDrivenWizard.from_yaml(".attune/wizards/my-wizard.yaml")

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from .base import BaseWizard, StepType, WizardConfig, WizardResult, WizardStep
from .config_driven import ConfigDrivenWizard
from .decomposer import DecomposedTask, TaskDecomposer
from .registry import (
    delete_custom_wizard,
    get_wizard,
    list_wizards,
    register_wizard,
    save_custom_wizard,
)
from .session import WizardSession

__all__ = [
    "BaseWizard",
    "ConfigDrivenWizard",
    "DecomposedTask",
    "StepType",
    "TaskDecomposer",
    "WizardConfig",
    "WizardResult",
    "WizardSession",
    "WizardStep",
    "delete_custom_wizard",
    "get_wizard",
    "list_wizards",
    "register_wizard",
    "save_custom_wizard",
]
