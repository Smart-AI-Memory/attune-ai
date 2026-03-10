"""Smoke tests for attune.optimization module."""


class TestOptimizationImports:
    """Verify the optimization package exports are importable."""

    def test_import_package(self):
        """Test that the optimization package imports cleanly."""
        from attune.optimization import (
            CompressionLevel,
            ContextOptimizer,
            optimize_xml_prompt,
        )

        assert ContextOptimizer is not None
        assert CompressionLevel is not None
        assert optimize_xml_prompt is not None

    def test_compression_level_enum(self):
        """Test CompressionLevel enum values."""
        from attune.optimization.context_optimizer import CompressionLevel

        assert CompressionLevel.NONE.value == "none"
        assert CompressionLevel.LIGHT.value == "light"
        assert CompressionLevel.MODERATE.value == "moderate"
        assert CompressionLevel.AGGRESSIVE.value == "aggressive"

    def test_context_optimizer_instantiation(self):
        """Test ContextOptimizer can be created."""
        from attune.optimization.context_optimizer import (
            CompressionLevel,
            ContextOptimizer,
        )

        optimizer = ContextOptimizer(level=CompressionLevel.MODERATE)
        assert optimizer.level == CompressionLevel.MODERATE

    def test_optimizer_has_tag_mappings(self):
        """Test optimizer has expected tag compression mappings."""
        from attune.optimization.context_optimizer import ContextOptimizer

        optimizer = ContextOptimizer()
        assert "thinking" in optimizer._tag_mappings
        assert "answer" in optimizer._tag_mappings

    def test_optimize_preserves_content(self):
        """Test that optimize returns a string for valid input."""
        from attune.optimization.context_optimizer import ContextOptimizer

        optimizer = ContextOptimizer()
        result = optimizer.optimize("<thinking>Hello</thinking>")
        assert isinstance(result, str)
        assert len(result) > 0
