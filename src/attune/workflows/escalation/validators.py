"""Validator protocol and bundled implementations for EscalationChain.

Validators run as Layer 1 (structural checks) before the optional
evaluator LLM. They are fast, deterministic, and free.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Validator(Protocol):
    """Protocol for rule-based response validators.

    Validators receive the parsed response and return a (passed, message)
    tuple. A falsy message is fine when passed=True.

    Example:
        >>> class MyValidator:
        ...     def validate(self, response: Any) -> tuple[bool, str | None]:
        ...         return bool(response), "Response was empty"

    """

    def validate(self, response: Any) -> tuple[bool, str | None]:
        """Check whether the response meets requirements.

        Args:
            response: Parsed LLM response (dict, str, or None).

        Returns:
            (True, None) on success or (False, reason) on failure.

        """
        ...


class StructureValidator:
    """Check that all required fields are present in the response dict.

    Args:
        required_fields: Field names that must exist in the response.

    Example:
        >>> v = StructureValidator(["answer", "confidence"])
        >>> v.validate({"answer": "42", "confidence": 0.9})
        (True, None)
        >>> v.validate({"answer": "42"})
        (False, "Missing required fields: confidence")

    """

    def __init__(self, required_fields: list[str]) -> None:
        """Initialize with the list of required field names.

        Args:
            required_fields: Field names that must exist in the response dict.

        """
        self.required_fields = required_fields

    def validate(self, response: Any) -> tuple[bool, str | None]:
        """Check that all required fields are present.

        Args:
            response: Parsed LLM response — must be a dict to pass.

        Returns:
            (True, None) if all fields present, (False, reason) otherwise.

        """
        if not isinstance(response, dict):
            return False, f"Expected dict response, got {type(response).__name__}"
        missing = [f for f in self.required_fields if f not in response]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        return True, None


class ConfidenceValidator:
    """Check that the response confidence meets a minimum threshold.

    Expects the response to be a dict with a numeric `confidence` field.

    Args:
        min_confidence: Minimum acceptable confidence (0.0–1.0).

    Example:
        >>> v = ConfidenceValidator(min_confidence=0.7)
        >>> v.validate({"confidence": 0.85})
        (True, None)
        >>> v.validate({"confidence": 0.5})
        (False, "Confidence 0.50 below threshold 0.70")

    """

    def __init__(self, min_confidence: float = 0.7) -> None:
        """Initialize with the minimum confidence threshold.

        Args:
            min_confidence: Minimum acceptable confidence value (0.0–1.0).

        """
        self.min_confidence = min_confidence

    def validate(self, response: Any) -> tuple[bool, str | None]:
        """Check that response confidence meets the threshold.

        Args:
            response: Parsed LLM response dict with a `confidence` field.

        Returns:
            (True, None) if confidence is sufficient, (False, reason) otherwise.

        """
        if not isinstance(response, dict):
            return False, f"Expected dict response, got {type(response).__name__}"
        confidence = response.get("confidence")
        if confidence is None:
            return False, "Response missing 'confidence' field"
        try:
            value = float(confidence)
        except (TypeError, ValueError):
            return False, f"Invalid confidence value: {confidence!r}"
        if value < self.min_confidence:
            return (
                False,
                f"Confidence {value:.2f} below threshold {self.min_confidence:.2f}",
            )
        return True, None
