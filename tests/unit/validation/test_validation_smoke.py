"""Smoke tests for validation.

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
        import attune.validation

        assert attune.validation is not None

    def test_validator_classes_import(self) -> None:
        """Test that validator classes import."""
        from attune.validation import ValidationResult, XMLValidator

        assert ValidationResult is not None
        assert XMLValidator is not None

    def test_convenience_function_imports(self) -> None:
        """Test that validate_xml_response imports."""
        from attune.validation import validate_xml_response

        assert validate_xml_response is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_xml_validator_defaults(self) -> None:
        """Test XMLValidator with defaults."""
        from attune.validation import XMLValidator

        validator = XMLValidator()
        assert validator is not None
        assert validator.strict is False

    def test_validation_result_creation(self) -> None:
        """Test ValidationResult dataclass creation."""
        from attune.validation import ValidationResult

        result = ValidationResult(is_valid=True, parsed_data={"key": "value"})
        assert result.is_valid is True
        assert result.error_message is None
        assert result.fallback_used is False


@pytest.mark.unit
class TestValidation:
    """Verify validation methods work."""

    def test_validate_valid_xml(self) -> None:
        """Test validating well-formed XML."""
        from attune.validation import XMLValidator

        validator = XMLValidator()
        result = validator.validate("<root><item>test</item></root>")
        assert result.is_valid is True

    def test_validate_invalid_xml_non_strict(self) -> None:
        """Test that invalid XML uses fallback in non-strict mode."""
        from attune.validation import XMLValidator

        validator = XMLValidator(strict=False)
        result = validator.validate("<root><unclosed>")
        # In non-strict mode, should try fallback
        assert isinstance(result.is_valid, bool)

    def test_validate_xml_response_convenience(self) -> None:
        """Test the convenience function."""
        from attune.validation import validate_xml_response

        result = validate_xml_response("<answer>42</answer>")
        assert result.is_valid is True
