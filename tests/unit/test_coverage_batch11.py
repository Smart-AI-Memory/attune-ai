# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for trivial __init__ and __main__ modules — Batch 11.

Covers: agents_md/__init__, context/__init__, learning/__init__,
optimization/__init__, project_index/__main__, test_generator/__main__,
validation/__init__, socratic_router_patterns,
meta_workflows/cli_commands/__init__, telemetry/__main__.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

# === Module: agents_md/__init__.py ===


class TestAgentsMdInit:
    def test_agent_loader_importable(self):
        from attune.agents_md import AgentLoader

        assert AgentLoader is not None

    def test_markdown_agent_parser_importable(self):
        from attune.agents_md import MarkdownAgentParser

        assert MarkdownAgentParser is not None

    def test_agent_registry_importable(self):
        from attune.agents_md import AgentRegistry

        assert AgentRegistry is not None

    def test_agent_loader_identity(self):
        from attune.agents_md import AgentLoader
        from attune.agents_md.loader import AgentLoader as Direct

        assert AgentLoader is Direct

    def test_namespace_has_all_symbols(self):
        from attune.agents_md import AgentLoader, MarkdownAgentParser, AgentRegistry

        for symbol in (AgentLoader, MarkdownAgentParser, AgentRegistry):
            assert symbol is not None


# === Module: context/__init__.py ===


class TestContextInit:
    def test_compact_state_importable(self):
        from attune.context import CompactState

        assert CompactState is not None

    def test_compaction_state_manager_importable(self):
        from attune.context import CompactionStateManager

        assert CompactionStateManager is not None

    def test_context_manager_importable(self):
        from attune.context import ContextManager

        assert ContextManager is not None

    def test_work_handoff_importable(self):
        from attune.context import WorkHandoff

        assert WorkHandoff is not None

    def test_all_list_complete(self):
        from attune import context as m

        for name in ("CompactState", "CompactionStateManager", "ContextManager", "WorkHandoff"):
            assert name in m.__all__

    def test_context_manager_instantiable(self):
        from attune.context import ContextManager

        cm = ContextManager()
        assert cm is not None

    def test_context_manager_identity(self):
        from attune.context import ContextManager
        from attune.context.manager import ContextManager as Direct

        assert ContextManager is Direct


# === Module: learning/__init__.py ===


class TestLearningInit:
    def test_extracted_pattern_importable(self):
        from attune.learning import ExtractedPattern

        assert ExtractedPattern is not None

    def test_learned_skill_importable(self):
        from attune.learning import LearnedSkill

        assert LearnedSkill is not None

    def test_learned_skills_storage_importable(self):
        from attune.learning import LearnedSkillsStorage

        assert LearnedSkillsStorage is not None

    def test_pattern_category_importable(self):
        from attune.learning import PatternCategory

        assert PatternCategory is not None

    def test_pattern_extractor_importable(self):
        from attune.learning import PatternExtractor

        assert PatternExtractor is not None

    def test_session_evaluator_importable(self):
        from attune.learning import SessionEvaluator

        assert SessionEvaluator is not None

    def test_session_quality_importable(self):
        from attune.learning import SessionQuality

        assert SessionQuality is not None

    def test_all_list_complete(self):
        import attune.learning as m

        for name in (
            "ExtractedPattern",
            "LearnedSkill",
            "LearnedSkillsStorage",
            "PatternCategory",
            "PatternExtractor",
            "SessionEvaluator",
            "SessionQuality",
        ):
            assert name in m.__all__

    def test_session_quality_is_enum(self):
        import enum

        from attune.learning import SessionQuality

        assert issubclass(SessionQuality, enum.Enum)

    def test_pattern_category_is_enum(self):
        import enum

        from attune.learning import PatternCategory

        assert issubclass(PatternCategory, enum.Enum)


# === Module: optimization/__init__.py ===


class TestOptimizationInit:
    def test_compression_level_importable(self):
        from attune.optimization import CompressionLevel

        assert CompressionLevel is not None

    def test_context_optimizer_importable(self):
        from attune.optimization import ContextOptimizer

        assert ContextOptimizer is not None

    def test_optimize_xml_prompt_callable(self):
        from attune.optimization import optimize_xml_prompt

        assert callable(optimize_xml_prompt)

    def test_all_list(self):
        import attune.optimization as m

        assert set(m.__all__) == {"CompressionLevel", "ContextOptimizer", "optimize_xml_prompt"}

    def test_compression_level_is_enum(self):
        import enum

        from attune.optimization import CompressionLevel

        assert issubclass(CompressionLevel, enum.Enum)


# === Module: project_index/__main__.py ===


class TestProjectIndexMain:
    def test_module_importable(self):
        import attune.project_index.__main__

        assert attune.project_index.__main__ is not None

    def test_emit_deprecation_accessible(self):
        import attune.project_index.__main__ as m

        assert hasattr(m, "_emit_cli_deprecation")
        assert callable(m._emit_cli_deprecation)

    def test_main_accessible(self):
        import attune.project_index.__main__ as m

        assert hasattr(m, "main")
        assert callable(m.main)

    def test_guard_does_not_run_on_import(self):
        # If import succeeded without exit() being called the guard is working
        import attune.project_index.__main__  # noqa: F401

        assert True


# === Module: test_generator/__main__.py ===


class TestTestGeneratorMain:
    def test_module_importable(self):
        import attune.test_generator.__main__

        assert attune.test_generator.__main__ is not None

    def test_emit_deprecation_accessible(self):
        import attune.test_generator.__main__ as m

        assert hasattr(m, "_emit_cli_deprecation")
        assert callable(m._emit_cli_deprecation)

    def test_main_accessible(self):
        import attune.test_generator.__main__ as m

        assert hasattr(m, "main")
        assert callable(m.main)

    def test_guard_does_not_run_on_import(self):
        import attune.test_generator.__main__  # noqa: F401

        assert True


# === Module: validation/__init__.py ===


class TestValidationInit:
    def test_validation_result_importable(self):
        from attune.validation import ValidationResult

        assert ValidationResult is not None

    def test_xml_validator_importable(self):
        from attune.validation import XMLValidator

        assert XMLValidator is not None

    def test_validate_xml_response_callable(self):
        from attune.validation import validate_xml_response

        assert callable(validate_xml_response)

    def test_all_list(self):
        import attune.validation as m

        for name in ("ValidationResult", "XMLValidator", "validate_xml_response"):
            assert name in m.__all__

    def test_xml_validator_instantiable(self):
        from attune.validation import XMLValidator

        v = XMLValidator()
        assert v is not None


# === Module: socratic_router_patterns.py ===


class TestSocraticRouterPatterns:
    def test_intent_patterns_is_dict(self):
        from attune.socratic_router_patterns import INTENT_PATTERNS

        assert isinstance(INTENT_PATTERNS, dict)

    def test_all_six_intent_categories_present(self):
        from attune.socratic_router_models import IntentCategory
        from attune.socratic_router_patterns import INTENT_PATTERNS

        for cat in (
            IntentCategory.FIX,
            IntentCategory.IMPROVE,
            IntentCategory.VALIDATE,
            IntentCategory.SHIP,
            IntentCategory.UNDERSTAND,
            IntentCategory.CREATE,
        ):
            assert cat in INTENT_PATTERNS, f"Missing category {cat}"

    def test_each_entry_has_keywords_list(self):
        from attune.socratic_router_patterns import INTENT_PATTERNS

        for cat, data in INTENT_PATTERNS.items():
            assert "keywords" in data, f"Missing keywords for {cat}"
            assert isinstance(data["keywords"], list)
            assert len(data["keywords"]) > 0

    def test_each_entry_has_question_string(self):
        from attune.socratic_router_patterns import INTENT_PATTERNS

        for cat, data in INTENT_PATTERNS.items():
            assert "question" in data, f"Missing question for {cat}"
            assert isinstance(data["question"], str)
            assert len(data["question"]) > 0

    def test_each_entry_has_options(self):
        from attune.socratic_router_patterns import INTENT_PATTERNS

        for cat, data in INTENT_PATTERNS.items():
            assert "options" in data, f"Missing options for {cat}"
            assert len(data["options"]) >= 2

    def test_fix_category_has_debug_keyword(self):
        from attune.socratic_router_models import IntentCategory
        from attune.socratic_router_patterns import INTENT_PATTERNS

        keywords = INTENT_PATTERNS[IntentCategory.FIX]["keywords"]
        assert any(kw in keywords for kw in ("fix", "bug", "error", "broken", "debug"))

    def test_six_categories_total(self):
        from attune.socratic_router_patterns import INTENT_PATTERNS

        assert len(INTENT_PATTERNS) == 6


# === Module: meta_workflows/cli_commands/__init__.py ===


class TestMetaWorkflowsCliCommandsInit:
    def test_meta_workflow_app_exists(self):
        from attune.meta_workflows.cli_commands import meta_workflow_app

        assert meta_workflow_app is not None

    def test_meta_workflow_app_name(self):
        from attune.meta_workflows.cli_commands import meta_workflow_app

        assert meta_workflow_app.info.name == "meta-workflow"

    def test_no_args_is_help(self):
        from attune.meta_workflows.cli_commands import meta_workflow_app

        assert meta_workflow_app.info.no_args_is_help is True

    def test_list_templates_importable(self):
        from attune.meta_workflows.cli_commands import list_templates

        assert callable(list_templates)

    def test_run_workflow_importable(self):
        from attune.meta_workflows.cli_commands import run_workflow

        assert callable(run_workflow)

    def test_natural_language_run_importable(self):
        from attune.meta_workflows.cli_commands import natural_language_run

        assert callable(natural_language_run)

    def test_detect_intent_importable(self):
        from attune.meta_workflows.cli_commands import detect_intent

        assert callable(detect_intent)

    def test_show_analytics_importable(self):
        from attune.meta_workflows.cli_commands import show_analytics

        assert callable(show_analytics)

    def test_list_runs_importable(self):
        from attune.meta_workflows.cli_commands import list_runs

        assert callable(list_runs)

    def test_create_agent_importable(self):
        from attune.meta_workflows.cli_commands import create_agent

        assert callable(create_agent)

    def test_create_team_importable(self):
        from attune.meta_workflows.cli_commands import create_team

        assert callable(create_team)

    def test_all_list_contains_app(self):
        import attune.meta_workflows.cli_commands as m

        assert "meta_workflow_app" in m.__all__

    def test_all_list_contains_workflow_commands(self):
        import attune.meta_workflows.cli_commands as m

        for name in ("run_workflow", "natural_language_run", "detect_intent"):
            assert name in m.__all__


# === Module: telemetry/__main__.py ===


class TestTelemetryMain:
    def test_main_function_exists(self):
        from attune.telemetry.__main__ import main

        assert callable(main)

    def test_main_no_command_returns_one(self):
        from attune.telemetry.__main__ import main

        with patch("attune.telemetry.__main__._emit_cli_deprecation"):
            with patch("sys.argv", ["prog"]):
                result = main()
        assert result == 1

    def test_main_show_dispatches(self):
        from attune.telemetry.__main__ import main

        mock_core = MagicMock()
        mock_core.cmd_telemetry_show.return_value = 0
        with patch("attune.telemetry.__main__._emit_cli_deprecation"):
            with patch("sys.argv", ["prog", "show"]):
                with patch.dict(sys.modules, {"attune.telemetry.cli_core": mock_core}):
                    result = main()
        assert result == 0
        mock_core.cmd_telemetry_show.assert_called_once()

    def test_main_savings_dispatches(self):
        from attune.telemetry.__main__ import main

        mock_core = MagicMock()
        mock_core.cmd_telemetry_savings.return_value = 0
        with patch("attune.telemetry.__main__._emit_cli_deprecation"):
            with patch("sys.argv", ["prog", "savings"]):
                with patch.dict(sys.modules, {"attune.telemetry.cli_core": mock_core}):
                    result = main()
        assert result == 0
        mock_core.cmd_telemetry_savings.assert_called_once()

    def test_main_export_dispatches(self):
        from attune.telemetry.__main__ import main

        mock_core = MagicMock()
        mock_core.cmd_telemetry_export.return_value = 0
        with patch("attune.telemetry.__main__._emit_cli_deprecation"):
            with patch("sys.argv", ["prog", "export", "--output", "/tmp/out.json"]):
                with patch.dict(sys.modules, {"attune.telemetry.cli_core": mock_core}):
                    result = main()
        assert result == 0
        mock_core.cmd_telemetry_export.assert_called_once()

    def test_emit_deprecation_called(self):
        from attune.telemetry.__main__ import main

        with patch("attune.telemetry.__main__._emit_cli_deprecation") as mock_dep:
            with patch("sys.argv", ["prog"]):
                main()
        mock_dep.assert_called_once()

    def test_guard_does_not_run_on_import(self):
        import attune.telemetry.__main__  # noqa: F401

        assert True
