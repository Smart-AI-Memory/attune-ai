"""Unit tests for attune.meta_workflows.cli_commands.template_commands.

Covers list_templates, inspect_template, and generate_plan_cmd CLI commands.
Uses Typer's CliRunner with the shared app from cli_commands/__init__.py,
following the pattern established in test_workflow_commands.py: real
MetaWorkflowTemplate/FormSchema/FormQuestion/AgentCompositionRule dataclass
instances as fakes (so attribute access is verified against the real shape,
not a MagicMock that silently answers anything), and unittest.mock.patch on
the module-level TemplateRegistry import / the lazily-imported generate_plan.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from attune.meta_workflows.cli_commands import meta_workflow_app
from attune.meta_workflows.models import (
    AgentCompositionRule,
    FormQuestion,
    FormSchema,
    MetaWorkflowTemplate,
    QuestionType,
    TierStrategy,
)

# template_commands.py imports TemplateRegistry at module scope from
# attune.meta_workflows, so it must be patched at its bound location.
REGISTRY = "attune.meta_workflows.cli_commands.template_commands.TemplateRegistry"
# generate_plan is imported *inside* generate_plan_cmd's try block
# (`from attune.meta_workflows.plan_generator import generate_plan`), so it
# must be patched at its source module, not at template_commands.
GENERATE_PLAN = "attune.meta_workflows.plan_generator.generate_plan"


@pytest.fixture
def runner():
    return CliRunner()


def _question(
    id="q1",
    text="Pick one",
    type=QuestionType.SINGLE_SELECT,
    options=None,
    required=True,
    default=None,
):
    return FormQuestion(
        id=id,
        text=text,
        type=type,
        options=options or [],
        required=required,
        default=default,
    )


def _rule(
    role="security",
    base_template="reviewer",
    tier_strategy=TierStrategy.CHEAP_ONLY,
    tools=None,
    required_responses=None,
    config_mapping=None,
):
    return AgentCompositionRule(
        role=role,
        base_template=base_template,
        tier_strategy=tier_strategy,
        tools=tools or [],
        required_responses=required_responses or {},
        config_mapping=config_mapping or {},
    )


def _template(
    template_id="release-prep",
    name="Release Prep",
    description="Prepare a release",
    version="1.0.0",
    author="system",
    tags=None,
    questions=None,
    rules=None,
    cost_range=(0.10, 0.50),
    duration=5,
):
    return MetaWorkflowTemplate(
        template_id=template_id,
        name=name,
        description=description,
        form_schema=FormSchema(title="t", description="d", questions=questions or []),
        agent_composition_rules=rules or [],
        version=version,
        tags=tags or ["release"],
        author=author,
        estimated_cost_range=cost_range,
        estimated_duration_minutes=duration,
    )


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


class TestListTemplates:
    def test_no_templates_found(self, runner):
        with patch(REGISTRY) as MockReg:
            MockReg.return_value.list_templates.return_value = []
            result = runner.invoke(
                meta_workflow_app,
                ["list-templates", "--storage-dir", "/tmp/my-templates"],
            )

        assert result.exit_code == 0
        assert "No templates found." in result.output
        assert "Looking in: /tmp/my-templates" in result.output
        assert "Create templates by running workflow workflow or" in result.output

    def test_lists_builtin_and_user_with_details(self, runner):
        builtin = _template(
            template_id="release-prep",
            name="Release Prep",
            questions=[_question(), _question(id="q2")],
            rules=[_rule()],
            cost_range=(0.25, 1.50),
            duration=12,
        )
        user_tpl = _template(template_id="my-custom", name="My Custom", tags=["custom"])

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.list_templates.return_value = ["release-prep", "my-custom"]
            MockReg.return_value.is_builtin.side_effect = lambda tid: tid == "release-prep"
            MockReg.return_value.load_template.side_effect = {
                "release-prep": builtin,
                "my-custom": user_tpl,
            }.get
            result = runner.invoke(meta_workflow_app, ["list-templates"])

        assert result.exit_code == 0
        out = result.output
        assert "Available Templates (2 total)" in out
        assert "Built-in: 1" in out
        assert "User: 1" in out
        # Migration hint shown because builtin_count > 0.
        assert "Built-in templates replace deprecated Crew workflows." in out
        # Built-in badge + details.
        assert "BUILT-IN" in out
        assert "Release Prep" in out
        assert "ID: release-prep" in out
        assert "Version: 1.0.0" in out
        assert "Author: system" in out
        assert "Tags: release" in out
        assert "Questions: 2" in out
        assert "Agent Rules: 1" in out
        assert "Est. Cost: $0.25-$1.50" in out
        assert "Est. Duration: ~12 min" in out
        assert "Quick Start: empathy meta-workflow run release-prep" in out
        # User badge for the second template.
        assert "USER" in out
        assert "My Custom" in out

    def test_no_migration_hint_when_no_builtin(self, runner):
        user_tpl = _template(template_id="my-custom", name="My Custom")

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.list_templates.return_value = ["my-custom"]
            MockReg.return_value.is_builtin.return_value = False
            MockReg.return_value.load_template.return_value = user_tpl
            result = runner.invoke(meta_workflow_app, ["list-templates"])

        assert result.exit_code == 0
        assert "Built-in templates replace deprecated Crew workflows." not in result.output

    def test_skips_unloadable_template_silently(self, runner):
        """A template ID whose load_template() returns None is skipped, not a crash."""
        real_tpl = _template(template_id="real", name="Real Template")

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.list_templates.return_value = ["real", "ghost"]
            MockReg.return_value.is_builtin.return_value = False
            MockReg.return_value.load_template.side_effect = {
                "real": real_tpl,
                "ghost": None,
            }.get
            result = runner.invoke(meta_workflow_app, ["list-templates"])

        assert result.exit_code == 0
        # Header count reflects list_templates(), even though "ghost" never renders.
        assert "Available Templates (2 total)" in result.output
        assert "Real Template" in result.output
        # The unloadable template must be skipped, not rendered as a ghost panel.
        assert "ghost" not in result.output

    def test_registry_error_exits_1(self, runner):
        with patch(REGISTRY, side_effect=RuntimeError("storage unavailable")):
            result = runner.invoke(meta_workflow_app, ["list-templates"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "storage unavailable" in result.output


# ---------------------------------------------------------------------------
# inspect_template
# ---------------------------------------------------------------------------


class TestInspectTemplate:
    def test_template_not_found(self, runner):
        with patch(REGISTRY) as MockReg:
            MockReg.return_value.load_template.return_value = None
            result = runner.invoke(meta_workflow_app, ["inspect", "missing"])

        assert result.exit_code == 1
        assert "Template not found: missing" in result.output

    def test_basic_inspection_without_rules(self, runner):
        tpl = _template(
            name="Release Prep",
            description="Prepare a release",
            questions=[_question(id="q1", text="Ready?", required=False)],
        )

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["inspect", "release-prep"])

        assert result.exit_code == 0
        out = result.output
        assert "Template: Release Prep" in out
        assert "Prepare a release" in out
        assert "Ready?" in out
        assert "ID: q1" in out
        assert "Type: single_select" in out
        # required=False -> no "Required" node.
        assert "Required" not in out
        # --show-rules not passed -> composition rules section absent.
        assert "Agent Composition Rules:" not in out
        assert "Summary:" in out
        assert "Questions: 1" in out
        assert "Agent Rules: 0" in out

    def test_options_truncated_over_three_and_required_default_shown(self, runner):
        tpl = _template(
            questions=[
                _question(
                    id="q1",
                    text="Choose",
                    options=["a", "b", "c", "d", "e"],
                    required=True,
                    default="a",
                ),
            ],
        )

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["inspect", "release-prep"])

        assert result.exit_code == 0
        out = result.output
        assert "Options: a, b, c, ... (2 more)" in out
        assert "Required" in out
        assert "Default: a" in out

    def test_show_rules_displays_composition_rules(self, runner):
        tpl = _template(
            rules=[
                _rule(
                    role="security",
                    base_template="reviewer",
                    tier_strategy=TierStrategy.PROGRESSIVE,
                    tools=["grep", "read"],
                    required_responses={"q1": "yes"},
                    config_mapping={"q1": "cfg_key"},
                ),
            ],
        )

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["inspect", "release-prep", "--show-rules"])

        assert result.exit_code == 0
        out = result.output
        assert "Agent Composition Rules: (1)" in out
        assert "1. security" in out
        assert "Base Template: reviewer" in out
        assert "Tier Strategy: progressive" in out
        assert "Tools: grep, read" in out
        assert "Required When: {'q1': 'yes'}" in out
        assert "Config Mapping: 1 fields" in out

    def test_show_rules_empty_tools_and_no_optional_fields(self, runner):
        tpl = _template(
            rules=[
                _rule(role="writer", tools=[], required_responses={}, config_mapping={}),
            ],
        )

        with patch(REGISTRY) as MockReg:
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["inspect", "release-prep", "-r"])

        assert result.exit_code == 0
        out = result.output
        assert "Tools: None" in out
        assert "Required When:" not in out
        assert "Config Mapping:" not in out

    def test_exception_exits_1(self, runner):
        with patch(REGISTRY, side_effect=RuntimeError("boom")):
            result = runner.invoke(meta_workflow_app, ["inspect", "release-prep"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "boom" in result.output


# ---------------------------------------------------------------------------
# generate_plan_cmd (plan)
# ---------------------------------------------------------------------------


class TestGeneratePlanCmd:
    def test_template_not_found(self, runner):
        with patch(REGISTRY) as MockReg:
            MockReg.return_value.load_template.return_value = None
            result = runner.invoke(meta_workflow_app, ["plan", "missing"])

        assert result.exit_code == 1
        assert "Generating plan for: missing" in result.output
        assert "Template not found: missing" in result.output

    def test_default_markdown_to_stdout(self, runner):
        tpl = _template()

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN CONTENT") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep"])

        assert result.exit_code == 0
        out = result.output
        assert "PLAN CONTENT" in out
        assert "=" * 60 in out
        assert "Copy prompts into Claude Code conversation" in out
        assert "Cost: $0 (uses your Max subscription)" in out
        mock_gen.assert_called_once_with(
            template_id="release-prep",
            form_responses=None,
            use_defaults=True,
            output_format="markdown",
        )

    def test_use_defaults_skips_interactive_prompts_even_with_questions(self, runner):
        tpl = _template(questions=[_question()])

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep"])

        assert result.exit_code == 0
        assert "Configuration:" not in result.output
        assert mock_gen.call_args.kwargs["form_responses"] is None

    def test_interactive_no_questions_leaves_form_responses_none(self, runner):
        tpl = _template(questions=[])

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep", "--interactive"])

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] is None

    def test_multi_choice_valid_numeric_selection(self, runner):
        tpl = _template(
            questions=[
                _question(
                    id="q1",
                    text="Choose",
                    options=["alpha", "beta", "gamma"],
                    default="gamma",
                ),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="1\n",
            )

        assert result.exit_code == 0
        assert "3. gamma (default)" in result.output
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "alpha"}

    def test_multi_choice_blank_input_uses_prompt_default_of_first_option(self, runner):
        """The Choice prompt's own default is hardcoded '1' (index 0) -- it is
        NOT the question's marked default, even when that default is a
        different option. Blank input picks options[0], not question.default.
        """
        tpl = _template(
            questions=[
                _question(
                    id="q1",
                    text="Choose",
                    options=["alpha", "beta", "gamma"],
                    default="gamma",
                ),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="\n",
            )

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "alpha"}

    def test_multi_choice_out_of_range_falls_back_to_question_default(self, runner):
        tpl = _template(
            questions=[
                _question(id="q1", text="Choose", options=["alpha", "beta"], default="beta"),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="9\n",
            )

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "beta"}

    def test_multi_choice_non_numeric_falls_back_to_first_option_when_no_default(self, runner):
        tpl = _template(
            questions=[
                _question(id="q1", text="Choose", options=["alpha", "beta"], default=None),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="not-a-number\n",
            )

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "alpha"}

    def test_multi_choice_zero_wraps_to_last_option_via_negative_indexing(self, runner):
        """Genuine quirk: `idx = int(choice) - 1` on choice='0' gives idx=-1,
        which is a VALID Python index (last element), not an IndexError. So
        entering '0' silently selects the LAST option instead of failing.
        """
        tpl = _template(
            questions=[
                _question(id="q1", text="Choose", options=["alpha", "beta", "gamma"]),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="0\n",
            )

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "gamma"}

    def test_text_question_uses_prompt_default_on_blank_input(self, runner):
        tpl = _template(
            questions=[
                _question(
                    id="q1",
                    text="Deploy now?",
                    type=QuestionType.BOOLEAN,
                    options=[],
                    default=None,
                ),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="\n",
            )

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "Yes"}

    def test_text_question_explicit_answer_overrides_default(self, runner):
        tpl = _template(
            questions=[
                _question(
                    id="q1",
                    text="Deploy now?",
                    type=QuestionType.TEXT_INPUT,
                    options=[],
                    default="Yes",
                ),
            ],
        )

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--interactive"],
                input="custom answer\n",
            )

        assert result.exit_code == 0
        assert mock_gen.call_args.kwargs["form_responses"] == {"q1": "custom answer"}

    def test_output_file_writes_plan(self, runner, tmp_path):
        tpl = _template()
        output_file = tmp_path / "plan.md"

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="THE PLAN"),
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--output", str(output_file)],
            )

        assert result.exit_code == 0
        assert "Plan saved to:" in result.output
        assert output_file.read_text() == "THE PLAN"

    def test_output_file_rejects_dangerous_system_path(self, runner):
        """Security: _validate_file_path rejects a system directory target;
        the ValueError is caught by the broad except and surfaces as an
        exit-1 error, not a silent write.
        """
        tpl = _template()

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="THE PLAN"),
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--output", "/etc/attune-plan-test.md"],
            )

        assert result.exit_code == 1
        assert "Error generating plan:" in result.output
        assert "Cannot write to system directory" in result.output

    def test_stdout_output_when_no_install_or_output_file(self, runner):
        tpl = _template()

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="STDOUT PLAN CONTENT"),
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep"])

        assert result.exit_code == 0
        assert "STDOUT PLAN CONTENT" in result.output
        assert "Plan saved to:" not in result.output
        assert "Installed as Claude Code skill:" not in result.output

    def test_install_skill_converts_non_skill_format_and_writes_file(
        self, runner, tmp_path, monkeypatch
    ):
        """--install with the default markdown format triggers a SECOND
        generate_plan() call requesting output_format='skill', and the
        file written is the skill-format content, not the markdown one.
        """
        monkeypatch.chdir(tmp_path)
        tpl = _template(template_id="release-prep")

        def _gen(*, template_id, form_responses, use_defaults, output_format):
            return "MARKDOWN-PLAN" if output_format == "markdown" else "SKILL-PLAN"

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, side_effect=_gen) as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep", "--install"])

        assert result.exit_code == 0
        assert mock_gen.call_count == 2
        skill_path = tmp_path / ".claude" / "commands" / "release-prep.md"
        assert skill_path.read_text() == "SKILL-PLAN"
        assert "Installed as Claude Code skill:" in result.output
        assert "Run with: /project:release-prep" in result.output

    def test_install_skill_already_skill_format_no_reconversion(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        tpl = _template(template_id="release-prep")

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, return_value="SKILL-PLAN") as mock_gen,
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(
                meta_workflow_app,
                ["plan", "release-prep", "--format", "skill", "--install"],
            )

        assert result.exit_code == 0
        assert mock_gen.call_count == 1
        skill_path = tmp_path / ".claude" / "commands" / "release-prep.md"
        assert skill_path.read_text() == "SKILL-PLAN"

    def test_import_error_shows_plan_generator_not_available(self, runner):
        tpl = _template()

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, side_effect=ImportError("no module")),
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep"])

        assert result.exit_code == 1
        assert "Plan generator not available." in result.output
        assert "This feature requires the plan_generator module." in result.output

    def test_generate_plan_unexpected_exception_exits_1(self, runner):
        tpl = _template()

        with (
            patch(REGISTRY) as MockReg,
            patch(GENERATE_PLAN, side_effect=RuntimeError("boom")),
        ):
            MockReg.return_value.load_template.return_value = tpl
            result = runner.invoke(meta_workflow_app, ["plan", "release-prep"])

        assert result.exit_code == 1
        assert "Error generating plan:" in result.output
        assert "boom" in result.output
