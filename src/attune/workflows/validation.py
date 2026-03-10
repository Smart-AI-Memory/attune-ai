"""Workflow Validation Framework.

Provides structured validation at three levels:
- Input validation: Check required fields/types at execute() entry
- Stage output validation: Check stage outputs against contracts
- Inter-stage contracts: Ensure output schema matches next stage's input

Strict by default — raises WorkflowValidationError on invalid data.
Opt-out by leaving input_schema=None or stage_contracts={}.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class WorkflowValidationError(ValueError):
    """Raised when workflow input or stage output fails validation.

    Attributes:
        workflow_name: Name of the workflow that failed validation.
        stage: Stage where validation failed ("input" for input validation).
        errors: List of specific validation error messages.
    """

    def __init__(
        self,
        workflow_name: str,
        stage: str,
        errors: list[str],
    ) -> None:
        """Initialize a workflow validation error.

        Args:
            workflow_name: Name of the workflow that failed validation.
            stage: Stage where validation failed.
            errors: List of specific validation error messages.
        """
        self.workflow_name = workflow_name
        self.stage = stage
        self.errors = errors
        msg = f"Validation failed for '{workflow_name}' " f"at stage '{stage}': {'; '.join(errors)}"
        super().__init__(msg)


@dataclass
class InputSchema:
    """Schema for validating workflow input kwargs.

    Args:
        required_fields: Field names mapped to expected types.
        optional_fields: Optional field names mapped to expected types.
        validators: Custom validation functions per field.
            Each validator receives the field value and returns
            an error string or None.
    """

    required_fields: dict[str, type] = field(default_factory=dict)
    optional_fields: dict[str, type] = field(default_factory=dict)
    validators: dict[str, Callable[[Any], str | None]] = field(default_factory=dict)


@dataclass
class StageContract:
    """Schema for validating stage output.

    Args:
        required_keys: Keys that must be present in stage output.
        optional_keys: Keys that may be present.
        key_types: Expected types for specific keys.
    """

    required_keys: set[str] = field(default_factory=set)
    optional_keys: set[str] = field(default_factory=set)
    key_types: dict[str, type] = field(default_factory=dict)


def validate_against_input_schema(
    data: dict[str, Any],
    schema: InputSchema,
) -> list[str]:
    """Validate a data dict against an InputSchema.

    Args:
        data: The input data to validate.
        schema: The schema to validate against.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []

    for field_name, expected_type in schema.required_fields.items():
        if field_name not in data:
            errors.append(f"Missing required field: '{field_name}'")
        elif not isinstance(data[field_name], expected_type):
            actual = type(data[field_name]).__name__
            errors.append(
                f"Field '{field_name}' expected {expected_type.__name__}, " f"got {actual}"
            )

    for field_name, expected_type in schema.optional_fields.items():
        if field_name in data and not isinstance(data[field_name], expected_type):
            actual = type(data[field_name]).__name__
            errors.append(
                f"Field '{field_name}' expected {expected_type.__name__}, " f"got {actual}"
            )

    for field_name, validator in schema.validators.items():
        if field_name in data:
            err = validator(data[field_name])
            if err is not None:
                errors.append(f"Field '{field_name}': {err}")

    return errors


def validate_against_contract(
    data: dict[str, Any],
    contract: StageContract,
) -> list[str]:
    """Validate a stage output dict against a StageContract.

    Args:
        data: The stage output to validate.
        contract: The contract to validate against.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []

    for key in contract.required_keys:
        if key not in data:
            errors.append(f"Missing required key: '{key}'")

    for key, expected_type in contract.key_types.items():
        if key in data and not isinstance(data[key], expected_type):
            actual = type(data[key]).__name__
            errors.append(f"Key '{key}' expected {expected_type.__name__}, " f"got {actual}")

    return errors
