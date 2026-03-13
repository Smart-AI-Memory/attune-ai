"""Tests for the Workflow Validation Framework.

Tests input validation, stage contracts, and inter-stage
contract enforcement at all three levels.
"""

import pytest

from attune.workflows.validation import (
    InputSchema,
    StageContract,
    WorkflowValidationError,
    validate_against_contract,
    validate_against_input_schema,
)

# --- WorkflowValidationError ---


class TestWorkflowValidationError:
    """Tests for WorkflowValidationError."""

    def test_is_value_error_subclass(self):
        """WorkflowValidationError inherits from ValueError."""
        err = WorkflowValidationError(
            workflow_name="test-wf",
            stage="input",
            errors=["missing field"],
        )
        assert isinstance(err, ValueError)

    def test_includes_context(self):
        """Error message includes workflow name and stage."""
        err = WorkflowValidationError(
            workflow_name="code-review",
            stage="classify",
            errors=["Missing required key: 'risk_level'"],
        )
        assert "code-review" in str(err)
        assert "classify" in str(err)
        assert "risk_level" in str(err)

    def test_attributes_set(self):
        """Error stores workflow_name, stage, and errors."""
        err = WorkflowValidationError(
            workflow_name="test",
            stage="input",
            errors=["err1", "err2"],
        )
        assert err.workflow_name == "test"
        assert err.stage == "input"
        assert err.errors == ["err1", "err2"]

    def test_multiple_errors_joined(self):
        """Multiple errors are joined with semicolons."""
        err = WorkflowValidationError(
            workflow_name="test",
            stage="input",
            errors=["err1", "err2"],
        )
        assert "err1; err2" in str(err)


# --- InputSchema ---


class TestInputSchema:
    """Tests for InputSchema and validate_against_input_schema."""

    def test_validates_required_fields_present(self):
        """Missing required fields produce errors."""
        schema = InputSchema(required_fields={"path": str, "name": str})
        errors = validate_against_input_schema({}, schema)
        assert len(errors) == 2
        assert any("path" in e for e in errors)
        assert any("name" in e for e in errors)

    def test_validates_required_field_types(self):
        """Wrong types on required fields produce errors."""
        schema = InputSchema(required_fields={"path": str})
        errors = validate_against_input_schema({"path": 123}, schema)
        assert len(errors) == 1
        assert "expected str" in errors[0]
        assert "got int" in errors[0]

    def test_passes_valid_required_fields(self):
        """Correct required fields produce no errors."""
        schema = InputSchema(required_fields={"path": str})
        errors = validate_against_input_schema({"path": "src/"}, schema)
        assert errors == []

    def test_allows_extra_fields(self):
        """Extra fields not in schema are allowed."""
        schema = InputSchema(required_fields={"path": str})
        errors = validate_against_input_schema({"path": "src/", "extra": True}, schema)
        assert errors == []

    def test_validates_optional_field_types(self):
        """Wrong types on optional fields produce errors."""
        schema = InputSchema(
            required_fields={},
            optional_fields={"diff": str},
        )
        errors = validate_against_input_schema({"diff": 42}, schema)
        assert len(errors) == 1
        assert "diff" in errors[0]

    def test_allows_missing_optional_fields(self):
        """Missing optional fields are not errors."""
        schema = InputSchema(
            required_fields={},
            optional_fields={"diff": str},
        )
        errors = validate_against_input_schema({}, schema)
        assert errors == []

    def test_custom_validators(self):
        """Custom validators run on present fields."""

        def check_path(v):
            if not v.startswith("/"):
                return "must be absolute path"
            return None

        schema = InputSchema(
            required_fields={"path": str},
            validators={"path": check_path},
        )
        errors = validate_against_input_schema({"path": "relative/path"}, schema)
        assert len(errors) == 1
        assert "absolute path" in errors[0]

    def test_custom_validator_passes(self):
        """Custom validators returning None produce no errors."""

        def check_path(v):
            return None

        schema = InputSchema(
            required_fields={"path": str},
            validators={"path": check_path},
        )
        errors = validate_against_input_schema({"path": "src/"}, schema)
        assert errors == []

    def test_custom_validator_skipped_if_field_missing(self):
        """Custom validators are skipped for missing fields."""

        def always_fail(v):
            return "should not run"

        schema = InputSchema(
            required_fields={},
            validators={"optional_field": always_fail},
        )
        errors = validate_against_input_schema({}, schema)
        # Only the required field error, not the validator error
        assert not any("should not run" in e for e in errors)


# --- StageContract ---


class TestStageContract:
    """Tests for StageContract and validate_against_contract."""

    def test_validates_required_keys(self):
        """Missing required keys produce errors."""
        contract = StageContract(required_keys={"findings", "summary"})
        errors = validate_against_contract({}, contract)
        assert len(errors) == 2
        assert any("findings" in e for e in errors)
        assert any("summary" in e for e in errors)

    def test_passes_valid_output(self):
        """Output with all required keys passes."""
        contract = StageContract(required_keys={"findings"})
        errors = validate_against_contract({"findings": ["issue1"]}, contract)
        assert errors == []

    def test_allows_extra_keys(self):
        """Extra keys not in contract are allowed."""
        contract = StageContract(required_keys={"findings"})
        errors = validate_against_contract({"findings": [], "extra": True}, contract)
        assert errors == []

    def test_validates_key_types(self):
        """Wrong types on typed keys produce errors."""
        contract = StageContract(
            required_keys={"findings"},
            key_types={"findings": list},
        )
        errors = validate_against_contract({"findings": "not a list"}, contract)
        assert len(errors) == 1
        assert "expected list" in errors[0]

    def test_allows_missing_optional_keys(self):
        """Optional keys can be absent without errors."""
        contract = StageContract(
            required_keys=set(),
            optional_keys={"details"},
        )
        errors = validate_against_contract({}, contract)
        assert errors == []


# --- LLMMixin integration ---


class TestLLMMixinValidation:
    """Tests for validate_input() and validate_contract() on LLMMixin."""

    def _make_mixin(self, input_schema=None, stage_contracts=None):
        """Create a minimal LLMMixin instance for testing."""
        from attune.workflows.llm_mixin import LLMMixin

        class TestMixin(LLMMixin):
            name = "test-workflow"
            stages = ["stage1"]

        obj = object.__new__(TestMixin)
        obj.name = "test-workflow"
        obj.stages = ["stage1"]
        if input_schema is not None:
            obj.input_schema = input_schema
        if stage_contracts is not None:
            obj.stage_contracts = stage_contracts
        return obj

    def test_validate_input_raises_on_missing_field(self):
        """validate_input raises WorkflowValidationError."""
        mixin = self._make_mixin(input_schema=InputSchema(required_fields={"path": str}))
        with pytest.raises(WorkflowValidationError) as exc_info:
            mixin.validate_input({})
        assert "path" in str(exc_info.value)
        assert exc_info.value.stage == "input"

    def test_validate_input_skips_when_no_schema(self):
        """validate_input does nothing when input_schema is None."""
        mixin = self._make_mixin(input_schema=None)
        # Should not raise
        mixin.validate_input({})
        mixin.validate_input({"anything": "goes"})

    def test_validate_input_passes_valid_data(self):
        """validate_input passes when required fields present."""
        mixin = self._make_mixin(input_schema=InputSchema(required_fields={"path": str}))
        # Should not raise
        mixin.validate_input({"path": "src/"})

    def test_validate_contract_raises_on_missing_key(self):
        """validate_contract raises WorkflowValidationError."""
        mixin = self._make_mixin(
            stage_contracts={"stage1": StageContract(required_keys={"findings"})}
        )
        with pytest.raises(WorkflowValidationError) as exc_info:
            mixin.validate_contract("stage1", {})
        assert "findings" in str(exc_info.value)
        assert exc_info.value.stage == "stage1"

    def test_validate_contract_skips_when_no_contract(self):
        """validate_contract does nothing for unstaged contracts."""
        mixin = self._make_mixin(stage_contracts={})
        # Should not raise
        mixin.validate_contract("unknown_stage", {})

    def test_validate_contract_passes_valid_output(self):
        """validate_contract passes when required keys present."""
        mixin = self._make_mixin(
            stage_contracts={"stage1": StageContract(required_keys={"result"})}
        )
        # Should not raise
        mixin.validate_contract("stage1", {"result": "ok"})


# --- Workflow schema declarations ---


class TestWorkflowSchemas:
    """Test that key workflows have schemas declared."""

    # test_security_audit_has_input_schema: Removed — SDK-native
    # workflow validates path in execute(), not via input_schema.

    # test_test_gen_has_input_schema: Removed — SDK-native
    # workflow validates in execute(), not via input_schema.

    # test_perf_audit_has_input_schema: Removed — SDK-native
    # workflow validates path in execute(), not via input_schema.

    def test_simplify_code_has_input_schema(self):
        """SimplifyCodeWorkflow declares input_schema."""
        from attune.workflows.simplify_code import (
            SimplifyCodeWorkflow,
        )

        assert SimplifyCodeWorkflow.input_schema is not None
        assert "path" in SimplifyCodeWorkflow.input_schema.required_fields
