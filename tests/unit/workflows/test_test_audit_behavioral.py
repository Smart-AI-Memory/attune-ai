"""Behavioral tests for TestAuditWorkflow (SDK-native).

Tests class attributes, construction, and BaseWorkflow integration.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestTestAuditAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert wf.name == "test-audit"

    def test_workflow_has_description(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert isinstance(wf.description, str)
        assert "Agent SDK" in wf.description

    def test_workflow_has_stages_list(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert isinstance(wf.stages, list)
        assert wf.stages == ["agent-audit"]

    def test_workflow_has_tier_map(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert "agent-audit" in wf.tier_map
        assert wf.tier_map["agent-audit"] == ModelTier.CAPABLE

    def test_inherits_base_workflow(self) -> None:
        from attune.workflows.base import BaseWorkflow
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        assert issubclass(TestAuditWorkflow, BaseWorkflow)

    def test_has_execute_method(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        assert hasattr(TestAuditWorkflow, "execute")
        assert callable(TestAuditWorkflow.execute)


@pytest.mark.unit
class TestTestAuditReExports:
    """Test backward-compatibility re-exports."""

    def test_module_coverage_importable(self) -> None:
        from attune.workflows.test_audit.workflow import ModuleCoverage

        assert ModuleCoverage is not None

    def test_parse_coverage_json_importable(self) -> None:
        from attune.workflows.test_audit.workflow import parse_coverage_json

        assert callable(parse_coverage_json)

    def test_batch_task_template_importable(self) -> None:
        from attune.workflows.test_audit.workflow import BATCH_TASK_TEMPLATE

        assert isinstance(BATCH_TASK_TEMPLATE, str)
