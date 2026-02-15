"""Built-in wizards for Attune AI.

Provides 5 developer-focused wizards out of the box:
- Debug: Guided debugging flow
- Test Gen: Test generation assistant
- Refactor: Refactoring planner
- Security: Security audit wizard
- Release Prep: Release readiness wizard

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune.wizards.base import BaseWizard

from .debug_wizard import DebugWizard
from .refactor_wizard import RefactorWizard
from .release_prep_wizard import ReleasePrepWizard
from .security_wizard import SecurityWizard
from .test_gen_wizard import TestGenWizard

BUILTIN_WIZARDS: dict[str, type[BaseWizard]] = {
    "debug": DebugWizard,
    "test-gen": TestGenWizard,
    "refactor": RefactorWizard,
    "security": SecurityWizard,
    "release-prep": ReleasePrepWizard,
}

__all__ = [
    "BUILTIN_WIZARDS",
    "DebugWizard",
    "RefactorWizard",
    "ReleasePrepWizard",
    "SecurityWizard",
    "TestGenWizard",
]
