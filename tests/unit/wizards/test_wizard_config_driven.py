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
import yaml

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.wizards.base import StepType
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


# =========================================================================
# File write error paths
# =========================================================================


class TestToYamlErrorPaths:
    """Test to_yaml error handling for PermissionError and OSError."""

    def _make_wizard(self, tmp_path):
        """Create a ConfigDrivenWizard from a minimal YAML for testing."""
        yaml_content = {
            "schema_version": "1.0",
            "wizard_id": "err-test",
            "name": "Error Test",
            "description": "Test error paths",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        yaml_path = tmp_path / "err-test.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(yaml_content, f)
        return ConfigDrivenWizard.from_yaml(str(yaml_path))

    def test_to_yaml_permission_error_raises(self, tmp_path):
        """Test to_yaml raises PermissionError on write failure."""
        from pathlib import Path
        from unittest.mock import patch as _patch

        wizard = self._make_wizard(tmp_path)
        output = tmp_path / "output.yaml"

        with _patch.object(Path, "open", side_effect=PermissionError("read-only filesystem")):
            with pytest.raises(PermissionError, match="read-only filesystem"):
                wizard.to_yaml(str(output))

    def test_to_yaml_os_error_raises_value_error(self, tmp_path):
        """Test to_yaml wraps OSError as ValueError."""
        from pathlib import Path
        from unittest.mock import patch as _patch

        wizard = self._make_wizard(tmp_path)
        output = tmp_path / "output.yaml"

        with _patch.object(Path, "open", side_effect=OSError("disk full")):
            with pytest.raises(ValueError, match="Cannot write wizard YAML"):
                wizard.to_yaml(str(output))

    def test_build_prompt_context_raises_without_session(self, tmp_path):
        """Test build_prompt_context raises RuntimeError without session."""
        wizard = self._make_wizard(tmp_path)
        wizard._session = None
        step = wizard.steps[0]

        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.build_prompt_context(step)

    def test_process_step_result_raises_without_session(self, tmp_path):
        """Test process_step_result raises RuntimeError without session."""
        wizard = self._make_wizard(tmp_path)
        wizard._session = None
        step = wizard.steps[0]

        with pytest.raises(RuntimeError, match="session not initialized"):
            wizard.process_step_result(step, {"key": "value"})


# =========================================================================
# Additional uncovered paths
# =========================================================================


class TestFromDictEdgeCases:
    """Test _from_dict with edge cases."""

    def test_from_dict_minimal_required_fields(self):
        """Test _from_dict with only required fields."""
        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "minimal",
            "name": "Minimal Wizard",
            "steps": [{"id": "s1", "step_type": "question"}],
        }
        wizard = ConfigDrivenWizard._from_dict(data)

        assert wizard.config.wizard_id == "minimal"
        assert wizard.config.description == ""
        assert wizard.config.domain == "development"
        assert wizard.config.version == "1.0.0"
        assert wizard.config.source == "custom"
        assert len(wizard.steps) == 1

    def test_from_dict_with_all_optional_fields(self):
        """Test _from_dict with all optional fields populated."""
        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "full",
            "name": "Full Wizard",
            "description": "A complete wizard",
            "domain": "security",
            "version": "2.5.0",
            "estimated_cost_range": [0.05, 1.00],
            "estimated_duration_minutes": 15,
            "steps": [
                {"id": "q1", "step_type": "question"},
                {"id": "a1", "step_type": "llm_call"},
            ],
        }
        wizard = ConfigDrivenWizard._from_dict(data)

        assert wizard.config.domain == "security"
        assert wizard.config.version == "2.5.0"
        assert wizard.config.estimated_cost_range == (0.05, 1.00)
        assert wizard.config.estimated_duration_minutes == 15
        assert len(wizard.steps) == 2

    def test_from_dict_with_extra_fields_ignored(self):
        """Test _from_dict ignores unrecognized fields without error."""
        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "extra-fields",
            "name": "Extra Fields Wizard",
            "steps": [{"id": "q1", "step_type": "question"}],
            "unknown_field": "ignored",
            "another_extra": 42,
        }
        # Should not raise
        wizard = ConfigDrivenWizard._from_dict(data)

        assert wizard.config.wizard_id == "extra-fields"

    def test_from_dict_default_cost_range(self):
        """Test _from_dict uses default cost range when not specified."""
        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "default-cost",
            "name": "Default Cost Wizard",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        wizard = ConfigDrivenWizard._from_dict(data)

        assert wizard.config.estimated_cost_range == (0.01, 0.50)

    def test_from_dict_all_step_types(self):
        """Test _from_dict parses all valid step types."""
        from attune.wizards.base import StepType
        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "all-types",
            "name": "All Types",
            "steps": [
                {"id": "s_question", "step_type": "question"},
                {"id": "s_llm", "step_type": "llm_call"},
                {"id": "s_decompose", "step_type": "task_decompose"},
                {"id": "s_review", "step_type": "review"},
                {"id": "s_preview", "step_type": "preview"},
                {"id": "s_confirm", "step_type": "confirm"},
            ],
        }
        wizard = ConfigDrivenWizard._from_dict(data)

        type_map = {s.id: s.step_type for s in wizard.steps}
        assert type_map["s_question"] == StepType.QUESTION
        assert type_map["s_llm"] == StepType.LLM_CALL
        assert type_map["s_decompose"] == StepType.TASK_DECOMPOSE
        assert type_map["s_review"] == StepType.REVIEW
        assert type_map["s_preview"] == StepType.PREVIEW
        assert type_map["s_confirm"] == StepType.CONFIRM


class TestToYamlRoundTripComplex:
    """Test to_yaml round-trip with complex wizard definitions."""

    def test_round_trip_with_llm_and_question_steps(self, tmp_path):
        """Test round-trip preserves LLM step with prompt_context."""
        yaml_content = {
            "schema_version": "1.0",
            "wizard_id": "complex-rt",
            "name": "Complex Round-trip",
            "description": "Tests complex round-trip",
            "domain": "security",
            "version": "1.2.0",
            "steps": [
                {
                    "id": "gather",
                    "name": "Gather Info",
                    "step_type": "question",
                    "questions": [
                        {
                            "id": "target",
                            "text": "Target?",
                            "type": "text_input",
                            "help_text": "Path to file",
                        },
                        {
                            "id": "mode",
                            "text": "Mode?",
                            "type": "single_select",
                            "options": ["fast", "thorough"],
                            "default": "fast",
                        },
                    ],
                },
                {
                    "id": "analyze",
                    "name": "Analyze",
                    "step_type": "llm_call",
                    "tier": "premium",
                    "prompt_context": {
                        "role": "analyst",
                        "goal": "Analyze {session.target}",
                        "instructions": ["Check thoroughly"],
                        "constraints": ["No breaking changes"],
                    },
                },
                {
                    "id": "preview",
                    "name": "Preview",
                    "step_type": "preview",
                },
            ],
        }
        original_path = tmp_path / "complex.yaml"
        with original_path.open("w") as f:
            import yaml

            yaml.safe_dump(yaml_content, f)

        from attune.wizards.config_driven import ConfigDrivenWizard

        wizard = ConfigDrivenWizard.from_yaml(str(original_path))
        output_path = tmp_path / "complex_out.yaml"
        wizard.to_yaml(str(output_path))

        wizard2 = ConfigDrivenWizard.from_yaml(str(output_path))
        assert wizard2.config.wizard_id == "complex-rt"
        assert wizard2.config.domain == "security"
        assert wizard2.config.version == "1.2.0"
        assert len(wizard2.steps) == 3
        assert wizard2.steps[0].id == "gather"
        assert wizard2.steps[1].id == "analyze"
        assert wizard2.steps[1].tier == "premium"

    def test_to_yaml_non_capable_tier_preserved(self, tmp_path):
        """Test non-default tier (premium) is written to YAML."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "tier-test",
            "name": "Tier Test",
            "steps": [{"id": "analyze", "step_type": "llm_call", "tier": "premium"}],
        }
        path = tmp_path / "tier.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        out = tmp_path / "tier_out.yaml"
        wizard.to_yaml(str(out))

        with out.open() as f:
            saved = yaml.safe_load(f)

        # Premium tier should be in output (non-default)
        step = saved["steps"][0]
        assert step.get("tier") == "premium"

    def test_to_yaml_capable_tier_omitted(self, tmp_path):
        """Test default capable tier is omitted from YAML output."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "capable-test",
            "name": "Capable Test",
            "steps": [{"id": "analyze", "step_type": "llm_call", "tier": "capable"}],
        }
        path = tmp_path / "capable.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        out = tmp_path / "capable_out.yaml"
        wizard.to_yaml(str(out))

        with out.open() as f:
            saved = yaml.safe_load(f)

        # Default tier should be omitted (to reduce noise)
        step = saved["steps"][0]
        assert "tier" not in step


class TestToDictSerializationFidelity:
    """Test _to_dict serializes all wizard data correctly."""

    def test_to_dict_includes_estimated_cost_range_as_list(self, tmp_path):
        """Test estimated_cost_range is serialized as a list (not tuple)."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "cost-test",
            "name": "Cost Test",
            "estimated_cost_range": [0.05, 2.00],
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        path = tmp_path / "cost.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        d = wizard._to_dict()

        assert isinstance(d["estimated_cost_range"], list)
        assert d["estimated_cost_range"] == [0.05, 2.00]

    def test_to_dict_schema_version_is_string(self, tmp_path):
        """Test schema_version in _to_dict is always '1.0'."""
        import yaml

        from attune.wizards.config_driven import SCHEMA_VERSION, ConfigDrivenWizard

        data = {
            "wizard_id": "schema-test",
            "name": "Schema Test",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        path = tmp_path / "schema.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        d = wizard._to_dict()

        assert d["schema_version"] == SCHEMA_VERSION

    def test_to_dict_step_description_omitted_when_empty(self, tmp_path):
        """Test step description is omitted from dict when empty string."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "desc-test",
            "name": "Desc Test",
            "steps": [{"id": "q1", "step_type": "question"}],
        }
        path = tmp_path / "desc.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        d = wizard._to_dict()

        step = d["steps"][0]
        assert "description" not in step  # Empty string should be omitted

    def test_to_dict_step_with_description_included(self, tmp_path):
        """Test step description is included when non-empty."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "desc-full",
            "name": "Desc Full",
            "steps": [
                {
                    "id": "q1",
                    "step_type": "question",
                    "description": "Please answer this",
                }
            ],
        }
        path = tmp_path / "desc_full.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        d = wizard._to_dict()

        step = d["steps"][0]
        assert step.get("description") == "Please answer this"


class TestProcessStepResultVariousSteps:
    """Test process_step_result with various step IDs."""

    def _make_wizard(self, tmp_path):
        """Create a ConfigDrivenWizard for testing."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard

        data = {
            "wizard_id": "proc-test",
            "name": "Proc Test",
            "steps": [
                {"id": "analyze", "step_type": "llm_call"},
                {"id": "check", "step_type": "llm_call"},
                {"id": "plan", "step_type": "task_decompose"},
            ],
        }
        path = tmp_path / "proc.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)
        return ConfigDrivenWizard.from_yaml(str(path))

    def test_process_stores_each_step_under_own_key(self, tmp_path):
        """Test each step stores result under {step_id}_result key."""
        from attune.wizards.session import WizardSession

        wizard = self._make_wizard(tmp_path)
        wizard._session = WizardSession(wizard_id="proc-test")

        for step in wizard.steps:
            wizard.process_step_result(step, {"data": f"result_for_{step.id}"})

        assert wizard._session.get("analyze_result") == {"data": "result_for_analyze"}
        assert wizard._session.get("check_result") == {"data": "result_for_check"}
        assert wizard._session.get("plan_result") == {"data": "result_for_plan"}

    def test_process_overwrites_prior_result_for_same_step(self, tmp_path):
        """Test process_step_result overwrites prior result for same step."""
        from attune.wizards.session import WizardSession

        wizard = self._make_wizard(tmp_path)
        wizard._session = WizardSession(wizard_id="proc-test")

        analyze_step = wizard.steps[0]
        wizard.process_step_result(analyze_step, {"v": 1})
        wizard.process_step_result(analyze_step, {"v": 2})

        assert wizard._session.get("analyze_result") == {"v": 2}


class TestSessionVariableInterpolationNested:
    """Test session variable interpolation in nested dict structures."""

    def test_nested_dict_interpolation_in_build_context(self, tmp_path):
        """Test nested dict values in prompt_context are interpolated."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard
        from attune.wizards.session import WizardSession

        data = {
            "wizard_id": "nested-interp",
            "name": "Nested Interp",
            "steps": [
                {
                    "id": "analyze",
                    "step_type": "llm_call",
                    "prompt_context": {
                        "role": "analyst",
                        "goal": "Analyze {session.target}",
                        "nested": {"inner_key": "For {session.mode} analysis"},
                    },
                }
            ],
        }
        path = tmp_path / "nested.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        wizard._session = WizardSession(wizard_id="nested-interp")
        wizard._session.set("target", "main.py")
        wizard._session.set("mode", "thorough")

        ctx = wizard.build_prompt_context(wizard.steps[0])

        assert ctx.goal == "Analyze main.py"

    def test_list_interpolation_in_instructions(self, tmp_path):
        """Test list items in instructions are interpolated."""
        import yaml

        from attune.wizards.config_driven import ConfigDrivenWizard
        from attune.wizards.session import WizardSession

        data = {
            "wizard_id": "list-interp",
            "name": "List Interp",
            "steps": [
                {
                    "id": "check",
                    "step_type": "llm_call",
                    "prompt_context": {
                        "role": "checker",
                        "goal": "Check code",
                        "instructions": [
                            "Review {session.target}",
                            "Focus on {session.focus}",
                            "Plain instruction",
                        ],
                    },
                }
            ],
        }
        path = tmp_path / "list.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f)

        wizard = ConfigDrivenWizard.from_yaml(str(path))
        wizard._session = WizardSession(wizard_id="list-interp")
        wizard._session.set("target", "auth.py")
        wizard._session.set("focus", "security")

        ctx = wizard.build_prompt_context(wizard.steps[0])

        assert "Review auth.py" in ctx.instructions
        assert "Focus on security" in ctx.instructions
        assert "Plain instruction" in ctx.instructions


@pytest.mark.unit
class TestConfigDrivenWizardMalformedYAML:
    """Regression: the documented ValueError contract covers bad YAML."""

    def test_from_yaml_malformed_raises_valueerror(self, tmp_path):
        """Syntactically-broken YAML raises the DOCUMENTED ValueError.

        ``yaml.YAMLError`` is not a ``ValueError`` subclass, so before the
        fix ``from_yaml`` violated its own ``Raises: ValueError: If the
        YAML is invalid`` contract (library-review batch-2 widening).
        """
        yaml_path = tmp_path / "broken.yaml"
        yaml_path.write_text("features:\n  - foo: [unclosed\n bad: : :\n")

        with pytest.raises(ValueError, match="Invalid wizard YAML"):
            ConfigDrivenWizard.from_yaml(str(yaml_path))
