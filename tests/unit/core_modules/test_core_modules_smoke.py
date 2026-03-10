"""Smoke tests for core_modules.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.core_modules

        assert attune.core_modules is not None

    def test_empathy_os_imports(self) -> None:
        """Test that EmpathyOS re-export works via lazy import."""
        from attune.core_modules import EmpathyOS

        assert EmpathyOS is not None

    def test_collaboration_state_imports(self) -> None:
        """Test that CollaborationState re-export works."""
        from attune.core_modules import CollaborationState

        assert CollaborationState is not None

    def test_all_exports_defined(self) -> None:
        """Test that __all__ contains expected names."""
        import attune.core_modules

        assert "EmpathyOS" in attune.core_modules.__all__
        assert "CollaborationState" in attune.core_modules.__all__

    def test_invalid_attr_raises(self) -> None:
        """Test that accessing invalid attribute raises AttributeError."""
        import attune.core_modules

        with pytest.raises(AttributeError):
            _ = attune.core_modules.DoesNotExist
