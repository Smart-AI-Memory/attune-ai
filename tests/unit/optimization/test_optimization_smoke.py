"""Smoke tests for optimization.

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
        import attune.optimization

        assert attune.optimization is not None

    def test_optimizer_classes_import(self) -> None:
        """Test that optimizer classes import."""
        from attune.optimization import CompressionLevel, ContextOptimizer

        assert CompressionLevel is not None
        assert ContextOptimizer is not None

    def test_convenience_function_imports(self) -> None:
        """Test that optimize_xml_prompt imports."""
        from attune.optimization import optimize_xml_prompt

        assert optimize_xml_prompt is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_context_optimizer_defaults(self) -> None:
        """Test ContextOptimizer with defaults."""
        from attune.optimization import CompressionLevel, ContextOptimizer

        optimizer = ContextOptimizer()
        assert optimizer.level == CompressionLevel.MODERATE

    def test_context_optimizer_custom_level(self) -> None:
        """Test ContextOptimizer with custom level."""
        from attune.optimization import CompressionLevel, ContextOptimizer

        optimizer = ContextOptimizer(level=CompressionLevel.AGGRESSIVE)
        assert optimizer.level == CompressionLevel.AGGRESSIVE

    def test_compression_level_enum(self) -> None:
        """Test CompressionLevel enum values."""
        from attune.optimization import CompressionLevel

        assert CompressionLevel.NONE.value == "none"
        assert CompressionLevel.AGGRESSIVE.value == "aggressive"


@pytest.mark.unit
class TestOptimization:
    """Verify optimization methods work."""

    def test_optimize_passthrough_on_none_level(self) -> None:
        """Test that NONE level returns input unchanged."""
        from attune.optimization import CompressionLevel, ContextOptimizer

        optimizer = ContextOptimizer(level=CompressionLevel.NONE)
        input_text = "<thinking>Hello world</thinking>"
        assert optimizer.optimize(input_text) == input_text

    def test_optimize_reduces_tokens(self) -> None:
        """Test that MODERATE level reduces output length."""
        from attune.optimization import CompressionLevel, ContextOptimizer

        optimizer = ContextOptimizer(level=CompressionLevel.MODERATE)
        input_text = "<thinking>  \n  Hello world  \n  </thinking>"
        result = optimizer.optimize(input_text)
        assert len(result) <= len(input_text)

    def test_optimize_xml_prompt_convenience(self) -> None:
        """Test the convenience function."""
        from attune.optimization import optimize_xml_prompt

        result = optimize_xml_prompt("<thinking>test</thinking>")
        assert isinstance(result, str)
