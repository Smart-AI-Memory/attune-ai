"""Tests for DocAuditWorkflow.

Covers workflow class attributes.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.doc_audit.workflow import DocAuditWorkflow

# ---------------------------------------------------------------------------
# TestDocAuditWorkflowConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocAuditWorkflowConfig:
    """Verify DocAuditWorkflow class attributes are set correctly."""

    def test_name(self):
        """Workflow name is 'doc-audit'."""
        assert DocAuditWorkflow.name == "doc-audit"

    def test_description(self):
        """Workflow description is a non-empty string."""
        assert isinstance(DocAuditWorkflow.description, str)
        assert DocAuditWorkflow.description
