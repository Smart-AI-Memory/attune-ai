"""Tests for TestAuditWorkflow (SDK-native).

Covers:
- Class attributes (name, description, stages, tier_map)
- Constructor defaults
- Subagent definitions
- Re-exports from submodules

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.test_audit.coverage_parser import ModuleCoverage
from attune.workflows.test_audit.workflow import (
    _DEPTH_MAX_TURNS,
    _SUBAGENT_NAMES,
    TestAuditWorkflow,
)

# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClassAttributes:
    """Test TestAuditWorkflow class-level attributes."""

    def test_name(self) -> None:
        assert TestAuditWorkflow.name == "test-audit"

    def test_description_mentions_agent_sdk(self) -> None:
        assert "Agent SDK" in TestAuditWorkflow.description

    def test_stages(self) -> None:
        assert TestAuditWorkflow.stages == ["agent-audit"]

    def test_tier_map(self) -> None:
        assert TestAuditWorkflow.tier_map == {"agent-audit": ModelTier.CAPABLE}


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstructor:
    """Test TestAuditWorkflow constructor."""

    def test_default_construction(self) -> None:
        wf = TestAuditWorkflow()
        assert wf.name == "test-audit"

    def test_kwargs_passed_to_base(self) -> None:
        wf = TestAuditWorkflow(enable_post_simplification=False)
        assert wf is not None


# ---------------------------------------------------------------------------
# Constants and subagent configuration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstants:
    """Test module-level constants."""

    def test_depth_max_turns_keys(self) -> None:
        assert set(_DEPTH_MAX_TURNS.keys()) == {"quick", "standard", "deep"}

    def test_depth_max_turns_values_ascending(self) -> None:
        assert _DEPTH_MAX_TURNS["quick"] < _DEPTH_MAX_TURNS["standard"]
        assert _DEPTH_MAX_TURNS["standard"] < _DEPTH_MAX_TURNS["deep"]

    def test_subagent_names(self) -> None:
        assert len(_SUBAGENT_NAMES) == 3
        assert "coverage-auditor" in _SUBAGENT_NAMES
        assert "gap-analyzer" in _SUBAGENT_NAMES
        assert "test-planner" in _SUBAGENT_NAMES


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReExports:
    """Test backward-compatibility re-exports."""

    def test_module_coverage_importable(self) -> None:
        from attune.workflows.test_audit.workflow import ModuleCoverage as MC

        assert MC is ModuleCoverage

    def test_parse_coverage_json_importable(self) -> None:
        from attune.workflows.test_audit.workflow import parse_coverage_json

        assert callable(parse_coverage_json)

    def test_batch_task_template_importable(self) -> None:
        from attune.workflows.test_audit.workflow import BATCH_TASK_TEMPLATE

        assert isinstance(BATCH_TASK_TEMPLATE, str)
