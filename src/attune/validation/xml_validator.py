"""XML validation for response verification.

Validates XML-structured responses with graceful fallbacks.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Result of XML validation.

    Attributes:
        is_valid: Whether XML is valid
        error_message: Error message if invalid
        parsed_data: Parsed data if valid
        fallback_used: Whether fallback parsing was used

    """

    is_valid: bool
    error_message: str | None = None
    parsed_data: dict[str, Any] | None = None
    fallback_used: bool = False


class XMLValidator:
    """Validates XML responses with graceful fallbacks.

    Supports:
    - Well-formedness validation
    - XSD schema validation (optional)
    - Graceful fallback on validation errors
    - Schema caching for performance

    Usage:
        validator = XMLValidator()
        result = validator.validate("<thinking>...</thinking>")

        if result.is_valid:
            data = result.parsed_data
        else:
            # Use fallback parsing
            data = fallback_parse(response)
    """

    def __init__(
        self,
        schema_dir: str = ".attune/schemas",
        strict: bool = False,
        enable_xsd: bool = False,
    ):
        """Initialize validator.

        Args:
            schema_dir: Directory containing XSD schemas
            strict: If True, fail on validation errors. If False, use fallback.
            enable_xsd: Enable XSD schema validation (requires lxml)

        """
        self.schema_dir = Path(schema_dir)
        self.strict = strict
        self.enable_xsd = enable_xsd
        self._schema_cache: dict[str, Any] = {}

        # Try to import lxml for XSD validation
        self._lxml_available = False
        if enable_xsd:
            try:
                from lxml import etree as lxml_etree  # noqa: F401

                self._lxml_available = True
            except ImportError:
                pass

    def validate(self, xml_string: str, schema_name: str | None = None) -> ValidationResult:
        """Validate XML string.

        Args:
            xml_string: XML content to validate
            schema_name: Optional XSD schema name (e.g., "agent_response")

        Returns:
            ValidationResult with validation status and parsed data

        """
        # Step 1: Well-formedness validation
        try:
            root = ET.fromstring(xml_string)  # nosec B314 - parsing trusted LLM responses
        except ET.ParseError as e:
            if self.strict:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"XML parsing failed: {e}",
                    fallback_used=False,
                )
            # Try fallback parsing
            return self._fallback_parse(xml_string, str(e))

        # Step 2: XSD schema validation (optional)
        if schema_name and self.enable_xsd and self._lxml_available:
            schema_result = self._validate_with_xsd(xml_string, schema_name)
            if not schema_result.is_valid:
                if self.strict:
                    return schema_result
                # Continue with parsed data despite schema error
                return ValidationResult(
                    is_valid=True,
                    parsed_data=self._extract_data(root),
                    fallback_used=True,
                    error_message=f"Schema validation failed: {schema_result.error_message}",
                )

        # Step 3: Extract structured data
        parsed_data = self._extract_data(root)

        return ValidationResult(
            is_valid=True,
            parsed_data=parsed_data,
            fallback_used=False,
        )

    def _validate_with_xsd(self, xml_string: str, schema_name: str) -> ValidationResult:
        """Validate XML against XSD schema.

        Args:
            xml_string: XML content
            schema_name: Schema file name (without .xsd extension)

        Returns:
            ValidationResult

        """
        if not self._lxml_available:
            return ValidationResult(
                is_valid=False,
                error_message="lxml not available for XSD validation",
            )

        try:
            from lxml import etree as lxml_etree
        except ImportError:
            return ValidationResult(
                is_valid=False,
                error_message="lxml import failed",
            )

        # Load schema
        schema_path = self.schema_dir / f"{schema_name}.xsd"
        if not schema_path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Schema not found: {schema_path}",
            )

        # Check cache
        if schema_name not in self._schema_cache:
            try:
                schema_doc = lxml_etree.parse(str(schema_path))
                self._schema_cache[schema_name] = lxml_etree.XMLSchema(schema_doc)
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Schema loading failed: {e}",
                )

        schema = self._schema_cache[schema_name]

        # Validate
        try:
            xml_doc = lxml_etree.fromstring(xml_string.encode("utf-8"))
            is_valid = schema.validate(xml_doc)

            if not is_valid:
                error_log = schema.error_log
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Schema validation failed: {error_log}",
                )

            return ValidationResult(is_valid=True)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {e}",
            )

    def _fallback_parse(self, xml_string: str, error: str) -> ValidationResult:
        """Attempt fallback parsing of malformed XML.

        Args:
            xml_string: XML string that failed to parse
            error: Parse error message

        Returns:
            ValidationResult with fallback data

        """
        # Try to extract data using regex patterns
        import re

        data: dict[str, Any] = {}

        # Extract thinking content
        thinking_match = re.search(r"<thinking[^>]*>(.*?)</thinking>", xml_string, re.DOTALL)
        if thinking_match:
            data["thinking"] = thinking_match.group(1).strip()

        # Extract answer content
        answer_match = re.search(r"<answer[^>]*>(.*?)</answer>", xml_string, re.DOTALL)
        if answer_match:
            data["answer"] = answer_match.group(1).strip()

        # If we extracted something, consider it a partial success
        if data:
            return ValidationResult(
                is_valid=True,
                parsed_data=data,
                fallback_used=True,
                error_message=f"XML parsing failed, used fallback: {error}",
            )

        # Complete failure
        return ValidationResult(
            is_valid=False,
            error_message=f"XML parsing and fallback failed: {error}",
            fallback_used=True,
        )

    def _extract_data(self, root: ET.Element) -> dict[str, Any]:
        """Extract structured data from parsed XML.

        Args:
            root: Parsed XML root element

        Returns:
            Dictionary with extracted data

        """
        data: dict[str, Any] = {}

        # Extract all child elements
        for child in root:
            # Handle nested elements
            if len(child):
                data[child.tag] = self._extract_data(child)
            else:
                # Leaf node - get text content
                data[child.tag] = child.text or ""

        # Also store root attributes
        if root.attrib:
            data["_attributes"] = dict(root.attrib)

        return data


def validate_xml_response(
    response: str,
    schema_name: str | None = None,
    strict: bool = False,
) -> ValidationResult:
    """Convenience function to validate XML response.

    Args:
        response: XML response string
        schema_name: Optional XSD schema name
        strict: If True, fail on validation errors

    Returns:
        ValidationResult

    Example:
        >>> response = "<thinking>Analysis</thinking><answer>Result</answer>"
        >>> result = validate_xml_response(response)
        >>> if result.is_valid:
        ...     print(result.parsed_data)

    """
    validator = XMLValidator(strict=strict)
    return validator.validate(response, schema_name)
