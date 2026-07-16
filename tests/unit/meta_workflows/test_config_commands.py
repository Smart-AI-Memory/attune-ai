"""Unit tests for attune.meta_workflows.cli_commands.config_commands.

Covers suggest_defaults_cmd and show_migration_guide CLI commands.
Uses Typer's CliRunner with the shared app declared in
cli_commands/__init__.py.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from attune.meta_workflows.cli_commands import meta_workflow_app


@pytest.fixture
def runner():
    return CliRunner()


def _fake_question(question_id, text):
    return SimpleNamespace(id=question_id, text=text)


def _fake_template(template_id="demo-template", name="Demo Template", questions=None):
    if questions is None:
        questions = [_fake_question("q1", "Preferred test framework?")]
    return SimpleNamespace(
        template_id=template_id,
        name=name,
        form_schema=SimpleNamespace(questions=questions),
    )


# ---------------------------------------------------------------------------
# suggest_defaults_cmd
# ---------------------------------------------------------------------------


class TestSuggestDefaultsCmd:
    def test_template_not_found_exits_1(self, runner):
        """Lines 59-61: missing template -> exit 1, error names the template id."""
        with patch(
            "attune.meta_workflows.cli_commands.config_commands.TemplateRegistry"
        ) as MockReg:
            MockReg.return_value.load_template.return_value = None
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", "missing"])
        assert result.exit_code == 1
        assert "Template not found: missing" in result.output

    def test_no_suggestions_available(self, runner):
        """Lines 72-74: empty defaults dict -> informational message, exit 0."""
        template = _fake_template()
        with (
            patch("attune.meta_workflows.cli_commands.config_commands.TemplateRegistry") as MockReg,
            patch("attune.memory.unified.UnifiedMemory", return_value=MagicMock()),
            patch("attune.meta_workflows.session_context.SessionContext") as MockSession,
        ):
            MockReg.return_value.load_template.return_value = template
            MockSession.return_value.suggest_defaults.return_value = {}
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", template.template_id])
        assert result.exit_code == 0
        assert "No suggestions available (no recent history)." in result.output

    def test_suggestions_render_known_question_text(self, runner):
        """Lines 77-97: known question id -> table row uses question.text."""
        template = _fake_template(questions=[_fake_question("q1", "Preferred test framework?")])
        with (
            patch("attune.meta_workflows.cli_commands.config_commands.TemplateRegistry") as MockReg,
            patch("attune.memory.unified.UnifiedMemory", return_value=MagicMock()),
            patch("attune.meta_workflows.session_context.SessionContext") as MockSession,
        ):
            MockReg.return_value.load_template.return_value = template
            MockSession.return_value.suggest_defaults.return_value = {"q1": "pytest"}
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", template.template_id])
        assert result.exit_code == 0
        assert "Found 1 suggested default(s):" in result.output
        assert "Preferred test framework?" in result.output
        assert "pytest" in result.output
        assert f"attune workflow run {template.template_id} --use-defaults" in result.output

    def test_suggestion_unknown_question_id_falls_back_to_raw_id(self, runner):
        """Line 89: question_id absent from form_schema -> display text = raw id."""
        template = _fake_template(questions=[])
        with (
            patch("attune.meta_workflows.cli_commands.config_commands.TemplateRegistry") as MockReg,
            patch("attune.memory.unified.UnifiedMemory", return_value=MagicMock()),
            patch("attune.meta_workflows.session_context.SessionContext") as MockSession,
        ):
            MockReg.return_value.load_template.return_value = template
            MockSession.return_value.suggest_defaults.return_value = {"mystery_q": "value_x"}
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", template.template_id])
        assert result.exit_code == 0
        assert "mystery_q" in result.output

    def test_suggestion_list_value_joined_with_commas(self, runner):
        """Lines 91-93: list value -> joined with ', '."""
        template = _fake_template(questions=[_fake_question("tags", "Tags")])
        with (
            patch("attune.meta_workflows.cli_commands.config_commands.TemplateRegistry") as MockReg,
            patch("attune.memory.unified.UnifiedMemory", return_value=MagicMock()),
            patch("attune.meta_workflows.session_context.SessionContext") as MockSession,
        ):
            MockReg.return_value.load_template.return_value = template
            MockSession.return_value.suggest_defaults.return_value = {
                "tags": ["red", "green", "blue"]
            }
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", template.template_id])
        assert result.exit_code == 0
        assert "red, green, blue" in result.output

    def test_default_user_id_and_session_id_forwarded(self, runner):
        """No --session-id/--user-id -> defaults ('cli_user', None) forwarded."""
        template = _fake_template()
        with (
            patch("attune.meta_workflows.cli_commands.config_commands.TemplateRegistry") as MockReg,
            patch("attune.memory.unified.UnifiedMemory") as MockMemory,
            patch("attune.meta_workflows.session_context.SessionContext") as MockSession,
        ):
            MockReg.return_value.load_template.return_value = template
            MockSession.return_value.suggest_defaults.return_value = {}
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", template.template_id])
        assert result.exit_code == 0
        MockMemory.assert_called_once_with(user_id="cli_user")
        MockSession.assert_called_once_with(memory=MockMemory.return_value, session_id=None)

    def test_explicit_session_id_and_user_id_forwarded(self, runner):
        """--session-id/--user-id options are forwarded verbatim."""
        template = _fake_template()
        with (
            patch("attune.meta_workflows.cli_commands.config_commands.TemplateRegistry") as MockReg,
            patch("attune.memory.unified.UnifiedMemory") as MockMemory,
            patch("attune.meta_workflows.session_context.SessionContext") as MockSession,
        ):
            MockReg.return_value.load_template.return_value = template
            MockSession.return_value.suggest_defaults.return_value = {}
            result = runner.invoke(
                meta_workflow_app,
                [
                    "suggest-defaults",
                    template.template_id,
                    "--session-id",
                    "sess_123",
                    "--user-id",
                    "alice",
                ],
            )
        assert result.exit_code == 0
        MockMemory.assert_called_once_with(user_id="alice")
        MockSession.assert_called_once_with(memory=MockMemory.return_value, session_id="sess_123")

    def test_import_error_shows_dependency_message(self, runner):
        """Lines 103-108: ImportError from memory/session setup -> exit 1,
        the specific 'not available' message (not the generic exception one).
        """
        with patch(
            "attune.memory.unified.UnifiedMemory",
            side_effect=ImportError("no module named attune.memory"),
        ):
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", "any-template"])
        assert result.exit_code == 1
        assert "Session context not available." in result.output
        # Rich wraps this line at the console width, so match the two
        # halves separately rather than the full contiguous sentence.
        assert "Ensure memory and session modules are" in result.output
        assert "installed." in result.output

    def test_generic_exception_shows_error_message(self, runner):
        """Lines 109-111: any other exception -> exit 1, 'Error: {e}'."""
        with (
            patch("attune.memory.unified.UnifiedMemory", return_value=MagicMock()),
            patch(
                "attune.meta_workflows.session_context.SessionContext",
                return_value=MagicMock(),
            ),
            patch(
                "attune.meta_workflows.cli_commands.config_commands.TemplateRegistry",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = runner.invoke(meta_workflow_app, ["suggest-defaults", "any-template"])
        assert result.exit_code == 1
        assert "Error: boom" in result.output


# ---------------------------------------------------------------------------
# show_migration_guide (migrate)
# ---------------------------------------------------------------------------


class TestShowMigrationGuide:
    def test_overview_shows_all_crews_and_sections(self, runner):
        """No crew_name -> overview: table lists all 4 crews + guidance sections."""
        result = runner.invoke(meta_workflow_app, ["migrate"])
        assert result.exit_code == 0
        assert "Why Migrate?" in result.output
        assert "Migration Map" in result.output
        for crew in (
            "ReleasePreparationCrew",
            "TestCoverageBoostCrew",
            "TestMaintenanceCrew",
            "ManageDocumentationCrew",
        ):
            assert crew in result.output
        assert "Quick Start" in result.output
        assert "More Details" in result.output

    def test_unknown_crew_name_lists_available_and_exits_1(self, runner):
        """Lines 168-173: unrecognized crew_name -> exit 1, lists known names."""
        result = runner.invoke(meta_workflow_app, ["migrate", "NotARealCrew"])
        assert result.exit_code == 1
        assert "Unknown Crew workflow: NotARealCrew" in result.output
        assert "Available Crew workflows:" in result.output
        assert "ReleasePreparationCrew" in result.output

    def test_known_crew_name_shows_migration_details(self, runner):
        """Lines 175-192: known crew_name -> before/after + benefits + try-it."""
        result = runner.invoke(meta_workflow_app, ["migrate", "ReleasePreparationCrew"])
        assert result.exit_code == 0
        assert "Migrating: ReleasePreparationCrew" in result.output
        assert "DEPRECATED (Before):" in result.output
        assert (
            "from attune.workflows.release_prep_crew import ReleasePreparationCrew" in result.output
        )
        assert "RECOMMENDED (After):" in result.output
        assert "attune workflow run release-prep" in result.output
        assert "No CrewAI/LangChain dependency required" in result.output
        assert "Try it now: attune workflow run release-prep" in result.output

    @pytest.mark.parametrize(
        "crew_name,template_id",
        [
            ("ReleasePreparationCrew", "release-prep"),
            ("TestCoverageBoostCrew", "test-coverage-boost"),
            ("TestMaintenanceCrew", "test-maintenance"),
            ("ManageDocumentationCrew", "manage-docs"),
        ],
    )
    def test_all_known_crews_map_to_correct_template(self, runner, crew_name, template_id):
        """Every CREW_MIGRATION_MAP entry resolves to its documented template."""
        result = runner.invoke(meta_workflow_app, ["migrate", crew_name])
        assert result.exit_code == 0
        assert f"Migrating: {crew_name}" in result.output
        assert f"attune workflow run {template_id}" in result.output
