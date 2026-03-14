"""Tests for DependencyCheckWorkflow (SDK-native).

Covers class attributes, construction, re-exports, and
format_dependency_check_report().

Copyright 2025 Smart AI Memory, LLC
"""

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.dependency_check import (
    DEPENDENCY_CHECK_STEPS,
    DependencyCheckWorkflow,
    format_dependency_check_report,
)

# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClassAttributes:
    """Test DependencyCheckWorkflow class-level attributes."""

    def test_name(self) -> None:
        assert DependencyCheckWorkflow.name == "dependency-check"

    def test_description_mentions_agent_sdk(self) -> None:
        assert "Agent SDK" in DependencyCheckWorkflow.description

    def test_stages(self) -> None:
        assert DependencyCheckWorkflow.stages == ["agent-check"]

    def test_tier_map(self) -> None:
        assert DependencyCheckWorkflow.tier_map == {
            "agent-check": ModelTier.CAPABLE,
        }


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstructor:
    """Test DependencyCheckWorkflow constructor."""

    def test_default_construction(self) -> None:
        wf = DependencyCheckWorkflow()
        assert wf.name == "dependency-check"

    def test_kwargs_passed_to_base(self) -> None:
        wf = DependencyCheckWorkflow(enable_post_simplification=False)
        assert wf is not None


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReExports:
    """Test backward-compatibility re-exports."""

    def test_dependency_check_steps(self) -> None:
        assert isinstance(DEPENDENCY_CHECK_STEPS, dict)
        assert len(DEPENDENCY_CHECK_STEPS) > 0

    def test_format_report_callable(self) -> None:
        assert callable(format_dependency_check_report)

    def test_main_importable(self) -> None:
        from attune.workflows.dependency_check import main

        assert callable(main)

    def test_audit_helpers_importable(self) -> None:
        from attune.workflows.dependency_check import _run_pip_audit

        assert callable(_run_pip_audit)
