"""Behavioral tests for DocAuditWorkflow.

Tests class attributes without hitting real file systems or LLMs.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestDocAuditAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert wf.name == "doc-audit"

    def test_workflow_has_description(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert isinstance(wf.stages, list)
        assert wf.stages == ["agent-audit"]

    def test_workflow_has_tier_map(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert "agent-audit" in wf.tier_map
