"""Tests for verification default strategy mapping."""

from __future__ import annotations

from attune.verification.defaults import (
    DEFAULT_VERIFICATION_STRATEGIES,
    get_default_strategy,
)


class TestDefaultStrategies:
    """Test default strategy resolution."""

    def test_code_review_defaults_to_lint(self) -> None:
        """Test code-review workflow maps to lint-check."""
        assert get_default_strategy("code-review") == "lint-check"

    def test_test_gen_defaults_to_run_tests(self) -> None:
        """Test test-gen workflow maps to run-tests."""
        assert get_default_strategy("test-gen") == "run-tests"

    def test_release_prep_defaults_to_build(self) -> None:
        """Test release-prep workflow maps to build."""
        assert get_default_strategy("release-prep") == "build"

    def test_doc_gen_defaults_to_none(self) -> None:
        """Test doc-gen workflow maps to none."""
        assert get_default_strategy("doc-gen") == "none"

    def test_unknown_workflow_defaults_to_none(self) -> None:
        """Test unknown workflow defaults to 'none'."""
        assert get_default_strategy("unknown-workflow") == "none"

    def test_all_defaults_have_valid_strategies(self) -> None:
        """Test all default strategies are valid names."""
        valid_strategies = {
            "run-tests",
            "lint-check",
            "type-check",
            "build",
            "custom-command",
            "none",
        }
        for workflow, strategy in DEFAULT_VERIFICATION_STRATEGIES.items():
            assert strategy in valid_strategies, (
                f"Workflow {workflow!r} has invalid default strategy " f"{strategy!r}"
            )

    def test_security_audit_defaults_to_lint(self) -> None:
        """Test security-audit maps to lint-check."""
        assert get_default_strategy("security-audit") == "lint-check"

    def test_refactor_plan_defaults_to_run_tests(self) -> None:
        """Test refactor-plan maps to run-tests."""
        assert get_default_strategy("refactor-plan") == "run-tests"
