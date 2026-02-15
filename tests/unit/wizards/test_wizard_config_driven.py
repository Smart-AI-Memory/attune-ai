"""Unit tests for ConfigDrivenWizard and helpers.

Tests cover:
- _interpolate_session_vars / _interpolate_dict
- _validate_schema
- _parse_steps / _parse_question
- _question_to_dict
- ConfigDrivenWizard.from_yaml / _from_dict / to_yaml / _to_dict
- build_prompt_context / process_step_result

Created: 2026-02-15
"""

import pytest

from pathlib import Path
from unittest.mock import MagicMock

import yaml

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.wizards.base import StepType, WizardStep
from attune.wizards.config_driven import (
    ConfigDrivenWizard,
    _interpolate_dict,
    _interpolate_session_vars,
    _parse_question,
    _parse_steps,
    _question_to_dict,
    _validate_schema,
)
from attune.wizards.session import WizardSession


# =========================================================================
# Session variable interpolation
# =========================================================================


class TestInterpolateSessionVars:
    """Test _interpolate_session_vars."""

    def test_basic_replacement(self):
        """Test basic session variable replacement."""
        session = WizardSession(wizard_id="test")
        session.set("name", "Alice")

        result = _interpolate_session_vars("Hello {session.name}!", session)
        assert result == "Hello Alice!"

    def test_multiple_vars(self):
        """Test multiple variable replacements."""
        session = WizardSession(wizard_id="test")
        session.set("source", "Flask")
        session.set("target", "FastAPI")

        result = _interpolate_session_vars(
            "Migrate from {session.source} to {session.target}", session
        )
        assert result == "Migrate from Flask to FastAPI"

    def test_missing_var_uses_placeholder(self):
        """Test missing variable shows placeholder."""
        session = WizardSession(wizard_id="test")

        result = _interpolate_session_vars("Value: {session.missing}", session)
        assert result == "Value: <missing>"

    def test_no_vars(self):
        """Test string with no variables is returned unchanged."""
        session = WizardSession(wizard_id="test")

        result = _interpolate_session_vars("plain text", session)
        assert result == "plain text"

    def test_falls_back_to_initial_context(self):
        """Test interpolation reads from initial_context."""
        session = WizardSession(wizard_id="test", initial_context={"path": "src/main.py"})

        result = _interpolate_session_vars("File: {session.path}", session)
        assert result == "File: src/main.py"


class TestInterpolateDict:
    """Test _interpolate_dict."""

    def test_string_values(self):
        """Test interpolation of string values."""
        session = WizardSession(wizard_id="test")
        session.set("target", "auth.py")

        result = _interpolate_dict({"goal": "Review {session.target}"}, session)
        assert result["goal"] == "Review auth.py"

    def test_list_values(self):
        """Test interpolation of list values."""
        session = WizardSession(wizard_id="test")
        session.set("framework", "Django")

        result = _interpolate_dict(
            {"instructions": ["Use {session.framework}", "Write tests"]}, session
        )
        assert result["instructions"][0] == "Use Django"
        assert result["instructions"][1] == "Write tests"

    def test_nested_dict_values(self):
        """Test interpolation of nested dict values."""
        session = WizardSession(wizard_id="test")
        session.set("name", "app")

        result = _interpolate_dict({"inner": {"key": "Value for {session.name}"}}, session)
        assert result["inner"]["key"] == "Value for app"

    def test_non_string_values_passed_through(self):
        """Test non-string values are passed through unchanged."""
        session = WizardSession(wizard_id="test")

        result = _interpolate_dict({"count": 42, "flag": True}, session)
        assert result["count"] == 42
        assert result["flag"] is True

    def test_non_string_list_items_passed_through(self):
        """Test non-string list items are passed through."""
        session = WizardSession(wizard_id="test")

        result = _interpolate_dict({"items": [1, "text", None]}, session)
        assert result["items"] == [1, "text", None]


# =========================================================================
# Schema validation
# =========================================================================


class TestValidateSchema:
    """Test _validate_schema."""

    def test_valid_schema(self):
        """Test valid schema passes validation."""
        data = {
            "wizard_id": "test",
            "name": "Test Wizard",
            "steps": [{"id": "step1", "step_type": "question"}],
        }
        _validate_schema(data)  # Should not raise

    def test_missing_wizard_id(self):
        """Test missing wizard_id raises ValueError."""
        with pytest.raises(ValueError, match="wizard_id"):
            _validate_schema({"name": "Test", "steps": [{"id": "s1"}]})

    def test_missing_name(self):
        """Test missing name raises ValueError."""
        with pytest.raises(ValueError, match="name"):
            _validate_schema({"wizard_id": "test", "steps": [{"id": "s1"}]})

    def test_missing_steps(self):
        """Test missing steps raises ValueError."""
        with pytest.raises(ValueError, match="steps"):
            _validate_schema({"wizard_id": "test", "name": "Test"})

    def test_empty_steps(self):
        """Test empty steps list raises ValueError."""
        with pytest.raises(ValueError, match="non-empty list"):
            _validate_schema({"wizard_id": "test", "name": "Test", "steps": []})

    def test_steps_not_list(self):
        """Test non-list steps raises ValueError."""
        with pytest.raises(ValueError, match="non-empty list"):
            _validate_schema({"wizard_id": "test", "name": "Test", "steps": "bad"})

    def test_step_not_dict(self):
        """Test step that's not a dict raises ValueError."""
        with pytest.raises(ValueError, match="Step 0 must be a mapping"):
            _validate_schema({"wizard_id": "test", "name": "Test", "steps": ["bad"]})

    def test_step_missing_id(self):
        """Test step missing id raises ValueError."""
        with pytest.raises(ValueError, match="missing required field: 'id'"):
            _validate_schema(
                {"wizard_id": "test", "name": "Test", "steps": [{"step_type": "question"}]}
            )

    def test_invalid_step_type(self):
        """Test invalid step_type raises ValueError."""
        with pytest.raises(ValueError, match="invalid step_type"):
            _validate_schema(
                {
                    "wizard_id": "test",
                    "name": "Test",
                    "steps": [{"id": "s1", "step_type": "invalid"}],
                }
            )

    def test_default_step_type(self):
        """Test step without step_type defaults to question (valid)."""
        data = {
            "wizard_id": "test",
            "name": "Test",
            "steps": [{"id": "s1"}],  # No step_type
        }
        _validate_schema(data)  # Should not raise


# =========================================================================
# Parsing helpers
# =========================================================================


class TestParseSteps:
    """Test _parse_steps."""

    def test_parse_basic_step(self):
        """Test parsing a basic step dict."""
        steps = _parse_steps([{"id": "q1", "name": "Question", "step_type": "question"}])

        assert len(steps) == 1
        assert steps[0].id == "q1"
        assert steps[0].name == "Question"
        assert steps[0].step_type == StepType.QUESTION

    def test_parse_step_defaults(self):
        """Test step parsing uses defaults."""
        steps = _parse_steps([{"id": "s1"}])

        assert steps[0].name == "s1"  # defaults to id
        assert steps[0].description == ""
        assert steps[0].step_type == StepType.QUESTION
        assert steps[0].tier == "capable"
        assert steps[0].max_tokens == 4096

    def test_parse_llm_step_with_prompt_context(self):
        """Test parsing LLM step with prompt context."""
        steps = _parse_steps(
            [
                {
                    "id": "analyze",
                    "step_type": "llm_call",
                    "tier": "premium",
                    "prompt_context": {
                        "role": "analyst",
                        "goal": "Analyze {session.target}",
                    },
                }
            ]
        )

        assert steps[0].step_type == StepType.LLM_CALL
        assert steps[0].tier == "premium"
        assert steps[0].prompt_context_template["role"] == "analyst"

    def test_parse_question_step_with_questions(self):
        """Test parsing question step with question definitions."""
        steps = _parse_steps(
            [
                {
                    "id": "gather",
                    "step_type": "question",
                    "questions": [
                        {"id": "target", "text": "Target?", "type": "text_input"},
                    ],
                }
            ]
        )

        assert steps[0].questions is not None
        assert len(steps[0].questions) == 1
        assert steps[0].questions[0].id == "target"


class TestParseQuestion:
    """Test _parse_question."""

    def test_text_input(self):
        """Test parsing a text input question."""
        q = _parse_question({"id": "name", "text": "Name?", "type": "text_input"})

        assert q.id == "name"
        assert q.text == "Name?"
        assert q.type == QuestionType.TEXT_INPUT

    def test_single_select(self):
        """Test parsing a single select question."""
        q = _parse_question(
            {
                "id": "mode",
                "text": "Mode?",
                "type": "single_select",
                "options": ["fast", "thorough"],
                "default": "fast",
            }
        )

        assert q.type == QuestionType.SINGLE_SELECT
        assert q.options == ["fast", "thorough"]
        assert q.default == "fast"

    def test_boolean(self):
        """Test parsing a boolean question."""
        q = _parse_question({"id": "confirm", "text": "Sure?", "type": "boolean"})

        assert q.type == QuestionType.BOOLEAN

    def test_unknown_type_defaults_to_text(self):
        """Test unknown question type defaults to TEXT_INPUT."""
        q = _parse_question({"id": "q", "text": "Q?", "type": "unknown_type"})

        assert q.type == QuestionType.TEXT_INPUT

    def test_help_text(self):
        """Test parsing help_text."""
        q = _parse_question({"id": "q", "text": "Q?", "type": "text_input", "help_text": "Helpful"})

        assert q.help_text == "Helpful"


class TestQuestionToDict:
    """Test _question_to_dict."""

    def test_basic_question(self):
        """Test serializing a basic question."""
        q = FormQuestion(id="q1", text="What?", type=QuestionType.TEXT_INPUT)
        d = _question_to_dict(q)

        assert d["id"] == "q1"
        assert d["text"] == "What?"
        assert d["type"] == "text_input"

    def test_with_options(self):
        """Test serializing question with options."""
        q = FormQuestion(
            id="mode",
            text="Mode?",
            type=QuestionType.SINGLE_SELECT,
            options=["a", "b"],
            default="a",
            help_text="Choose one",
        )
        d = _question_to_dict(q)

        assert d["options"] == ["a", "b"]
        assert d["default"] == "a"
        assert d["help_text"] == "Choose one"


# =========================================================================
# ConfigDrivenWizard
# =========================================================================


class TestConfigDrivenWizard:
    """Test ConfigDrivenWizard creation and serialization."""

    def test_from_yaml(self, tmp_path):
        """Test loading wizard from a YAML file."""
        yaml_content = {
            "schema_version": "1.0",
            "wizard_id": "test-wiz",
            "name": "Test Wizard",
            "description": "A test wizard",
            "steps": [
                {
                    "id": "q1",
                    "name": "Input",
                    "step_type": "question",
                    "questions": [
                        {"id": "target", "text": "Target?", "type": "text_input"},
                    ],
                },
                {
                    "id": "analyze",
                    "name": "Analyze",
                    "step_type": "llm_call",
                    "tier": "capable",
                    "prompt_context": {
                        "role": "analyst",
                        "goal": "Analyze {session.target}",
                    },
                },
            ],
        }
        yaml_path = tmp_path / "test-wiz.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))

        assert wizard.config.wizard_id == "test-wiz"
        assert wizard.config.name == "Test Wizard"
        assert wizard.config.source == "custom"
        assert len(wizard.steps) == 2
        assert wizard.steps[0].step_type == StepType.QUESTION
        assert wizard.steps[1].step_type == StepType.LLM_CALL

    def test_from_yaml_file_not_found(self):
        """Test FileNotFoundError for missing YAML."""
        with pytest.raises(FileNotFoundError):
            ConfigDrivenWizard.from_yaml("/nonexistent/wizard.yaml")

    def test_from_yaml_invalid_content(self, tmp_path):
        """Test ValueError for non-dict YAML."""
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text("- just\n- a\n- list\n")

        with pytest.raises(ValueError, match="expected a mapping"):
            ConfigDrivenWizard.from_yaml(str(yaml_path))

    def test_to_yaml_round_trip(self, tmp_path):
        """Test YAML round-trip (from_yaml -> to_yaml -> from_yaml)."""
        yaml_content = {
            "schema_version": "1.0",
            "wizard_id": "roundtrip",
            "name": "Roundtrip Wizard",
            "description": "Tests round-trip",
            "steps": [
                {
                    "id": "q1",
                    "name": "Input",
                    "step_type": "question",
                    "questions": [
                        {"id": "target", "text": "Target?", "type": "text_input"},
                    ],
                },
            ],
        }
        original_path = tmp_path / "original.yaml"
        with original_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        # Load and save
        wizard = ConfigDrivenWizard.from_yaml(str(original_path))
        output_path = tmp_path / "output.yaml"
        wizard.to_yaml(str(output_path))

        # Reload and compare
        wizard2 = ConfigDrivenWizard.from_yaml(str(output_path))
        assert wizard2.config.wizard_id == "roundtrip"
        assert len(wizard2.steps) == 1
        assert wizard2.steps[0].id == "q1"

    def test_to_yaml_system_dir_blocked(self, tmp_path):
        """Test to_yaml blocks system directories."""
        yaml_content = {
            "schema_version": "1.0",
            "wizard_id": "test",
            "name": "Test",
            "description": "Test",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        yaml_path = tmp_path / "test.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))

        with pytest.raises(ValueError, match="Cannot write to system directory"):
            wizard.to_yaml("/etc/evil.yaml")

    def test_to_dict_includes_all_fields(self, tmp_path):
        """Test _to_dict includes all expected fields."""
        yaml_content = {
            "schema_version": "1.0",
            "wizard_id": "full",
            "name": "Full Wizard",
            "description": "Has everything",
            "domain": "testing",
            "version": "2.0.0",
            "steps": [
                {
                    "id": "q1",
                    "name": "Q",
                    "step_type": "question",
                    "questions": [{"id": "t", "text": "T?", "type": "text_input"}],
                },
            ],
        }
        yaml_path = tmp_path / "full.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))
        d = wizard._to_dict()

        assert d["schema_version"] == "1.0"
        assert d["wizard_id"] == "full"
        assert d["name"] == "Full Wizard"
        assert d["description"] == "Has everything"
        assert d["domain"] == "testing"
        assert d["version"] == "2.0.0"
        assert len(d["steps"]) == 1

    def test_build_prompt_context_with_template(self, tmp_path):
        """Test build_prompt_context interpolates session vars."""
        yaml_content = {
            "wizard_id": "ctx-test",
            "name": "Context Test",
            "steps": [
                {
                    "id": "analyze",
                    "step_type": "llm_call",
                    "prompt_context": {
                        "role": "analyst",
                        "goal": "Review {session.target}",
                        "instructions": ["Check {session.target} for issues"],
                    },
                },
            ],
        }
        yaml_path = tmp_path / "ctx.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))
        wizard._session = WizardSession(wizard_id="ctx-test")
        wizard._session.set("target", "auth.py")

        ctx = wizard.build_prompt_context(wizard.steps[0])

        assert ctx.role == "analyst"
        assert ctx.goal == "Review auth.py"
        assert "Check auth.py for issues" in ctx.instructions

    def test_build_prompt_context_no_template(self, tmp_path):
        """Test build_prompt_context with no template returns defaults."""
        yaml_content = {
            "wizard_id": "no-ctx",
            "name": "No Context",
            "steps": [{"id": "analyze", "step_type": "llm_call"}],
        }
        yaml_path = tmp_path / "noctx.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))
        wizard._session = WizardSession(wizard_id="no-ctx")

        ctx = wizard.build_prompt_context(wizard.steps[0])

        assert ctx.role == "assistant"
        assert "analyze" in ctx.goal.lower()

    def test_process_step_result_stores_under_step_id(self, tmp_path):
        """Test process_step_result stores results keyed by step ID."""
        yaml_content = {
            "wizard_id": "proc",
            "name": "Proc",
            "steps": [{"id": "s1", "step_type": "llm_call"}],
        }
        yaml_path = tmp_path / "proc.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)

        wizard = ConfigDrivenWizard.from_yaml(str(yaml_path))
        wizard._session = WizardSession(wizard_id="proc")

        wizard.process_step_result(wizard.steps[0], {"key": "value"})

        assert wizard._session.get("s1_result") == {"key": "value"}
