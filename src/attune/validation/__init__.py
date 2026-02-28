"""XML validation for XML-enhanced prompts.

Provides schema validation and graceful fallbacks.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.validation.xml_validator import (
    ValidationResult,
    XMLValidator,
    validate_xml_response,
)

__all__ = [
    "ValidationResult",
    "XMLValidator",
    "validate_xml_response",
]
