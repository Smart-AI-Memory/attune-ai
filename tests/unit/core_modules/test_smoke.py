"""Smoke tests for attune.core_modules module."""


class TestCoreModulesImports:
    """Verify the core_modules package exports are importable."""

    def test_import_package(self):
        """Test that the core_modules package imports cleanly."""
        import attune.core_modules

        assert hasattr(attune.core_modules, "__all__")

    def test_lazy_empathyos_import(self):
        """Test lazy import of EmpathyOS via __getattr__."""
        from attune.core_modules import EmpathyOS

        assert EmpathyOS is not None

    def test_lazy_collaboration_state_import(self):
        """Test lazy import of CollaborationState via __getattr__."""
        from attune.core_modules import CollaborationState

        assert CollaborationState is not None

    def test_helpers_mixin_importable(self):
        """Test that EmpathyHelpersMixin can be imported."""
        from attune.core_modules.helpers import EmpathyHelpersMixin

        assert EmpathyHelpersMixin is not None
        assert hasattr(EmpathyHelpersMixin, "_process_request")

    def test_unknown_attr_raises(self):
        """Test that unknown attributes raise an error."""
        import pytest

        import attune.core_modules

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = attune.core_modules.NonexistentClass
