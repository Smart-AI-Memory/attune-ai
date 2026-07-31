"""Input-schema coverage sweep (workflow-intake-forms Task 1).

Every registered workflow declares an InputSchema, and malformed
input fails with NAMED fields — at the mixin seam and through the
real CLI exit contract.
"""

from __future__ import annotations

import pytest

import attune.workflows as workflows_pkg
from attune.workflows.validation import InputSchema, WorkflowValidationError

#: Shrink-only: workflows ruled exempt from declaring a schema.
#: Empty at seeding (2026-07-31) — additions need a chair ruling.
ALLOWLIST: frozenset[str] = frozenset()


def _registry() -> dict[str, type]:
    workflows_pkg._ensure_registry_initialized()
    return dict(workflows_pkg.WORKFLOW_REGISTRY)


def test_every_registered_workflow_declares_input_schema() -> None:
    missing = sorted(
        name
        for name, cls in _registry().items()
        if name not in ALLOWLIST and getattr(cls, "input_schema", None) is None
    )
    assert missing == [], (
        f"workflows without input_schema: {missing} — declare one "
        "(attune.workflows.validation.InputSchema) or obtain a chair "
        "ruling for the allowlist"
    )


def test_declared_schemas_are_wellformed() -> None:
    for name, cls in _registry().items():
        schema = getattr(cls, "input_schema", None)
        if schema is None:
            continue
        assert isinstance(schema, InputSchema), f"{name}: input_schema is not an InputSchema"
        overlap = set(schema.required_fields) & set(schema.optional_fields)
        assert not overlap, f"{name}: fields both required and optional: {overlap}"


def test_missing_required_field_is_named_at_the_seam() -> None:
    """fix declares hard-required fields; missing ones are NAMED.

    The standard family deliberately keeps `path` optional-typed:
    those workflows already return a graceful in-result error for a
    missing path (pinned by their execute tests), and the schema
    layer must not regress that contract — its added value there is
    TYPE validation.
    """
    from attune.workflows.fix_workflow import FixWorkflow

    schema = FixWorkflow.input_schema
    from attune.workflows.validation import validate_against_input_schema

    errors = validate_against_input_schema({}, schema)
    assert "Missing required field: 'goal'" in errors
    assert "Missing required field: 'scope_paths'" in errors


def test_wrong_type_is_named_at_the_seam() -> None:
    from attune.workflows.security_audit import SecurityAuditWorkflow

    wf = SecurityAuditWorkflow()
    with pytest.raises(WorkflowValidationError) as exc_info:
        wf.validate_input({"path": 42})
    assert any("expected str" in e for e in exc_info.value.errors)


def test_numeric_optionals_accept_int_and_float() -> None:
    from attune.workflows.security_audit import SecurityAuditWorkflow

    wf = SecurityAuditWorkflow()
    wf.validate_input({"path": "src", "max_budget_usd": 5})
    wf.validate_input({"path": "src", "max_budget_usd": 5.0})


def test_cli_run_rejects_malformed_input_exit_3_no_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The real exit contract: validation error -> named fields,
    EXIT_CLI_ERROR, and no traceback on stderr."""
    from attune.cli_commands._exit_codes import EXIT_CLI_ERROR, run_workflow_with_exit_code
    from attune.workflows.security_audit import SecurityAuditWorkflow

    code = run_workflow_with_exit_code(
        SecurityAuditWorkflow,
        {"path": 42},
        name="security-audit",
        json_mode=False,
        print_result=lambda result: None,
    )
    captured = capsys.readouterr()
    assert code == EXIT_CLI_ERROR
    assert "Invalid input for workflow 'security-audit'" in captured.out
    assert "expected str" in captured.out
    assert "Traceback" not in captured.err
