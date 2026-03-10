"""Smoke tests for attune.validation module."""


class TestValidationImports:
    """Verify the validation package exports are importable."""

    def test_import_package(self):
        """Test that the validation package imports cleanly."""
        from attune.validation import (
            ValidationResult,
            XMLValidator,
            validate_xml_response,
        )

        assert XMLValidator is not None
        assert ValidationResult is not None
        assert validate_xml_response is not None

    def test_validation_result_dataclass(self):
        """Test ValidationResult instantiation."""
        from attune.validation.xml_validator import ValidationResult

        result = ValidationResult(is_valid=True, parsed_data={"key": "value"})
        assert result.is_valid is True
        assert result.error_message is None
        assert result.fallback_used is False

    def test_xml_validator_instantiation(self):
        """Test XMLValidator can be created."""
        from attune.validation.xml_validator import XMLValidator

        validator = XMLValidator(strict=False, enable_xsd=False)
        assert validator.strict is False
        assert validator.enable_xsd is False

    def test_xml_validator_validates_wellformed_xml(self):
        """Test XMLValidator validates well-formed XML."""
        from attune.validation.xml_validator import XMLValidator

        validator = XMLValidator()
        result = validator.validate("<root><child>text</child></root>")
        assert result.is_valid is True

    def test_xml_validator_rejects_malformed_xml(self):
        """Test XMLValidator rejects malformed XML."""
        from attune.validation.xml_validator import XMLValidator

        validator = XMLValidator(strict=True)
        result = validator.validate("<root><unclosed>")
        assert result.is_valid is False
