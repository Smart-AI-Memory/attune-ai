"""Tests for the Socratic Workflow Builder CLI (socratic/cli.py).

Drives each cmd_* function with an argparse-style namespace and mocked
storage / builder / form-renderer, plus main() dispatch. No real
sessions, storage, or interactive prompts are touched.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from attune.socratic.cli import (
    cmd_blueprints,
    cmd_delete,
    cmd_export,
    cmd_list,
    cmd_resume,
    cmd_show,
    cmd_start,
    main,
)
from attune.socratic.session import SessionState

STORAGE = "attune.socratic.cli.get_default_storage"
BUILDER = "attune.socratic.cli.SocraticWorkflowBuilder"
RENDER = "attune.socratic.cli.render_form_interactive"


def _session(session_id="abcd1234efgh", state=SessionState.READY_TO_GENERATE):
    s = MagicMock()
    s.session_id = session_id
    s.goal = "harden the auth layer"
    s.state = state
    s.goal_analysis = MagicMock(domain="security", confidence=0.9, intent="improve")
    s.goal_analysis.ambiguities = ["which auth provider?"]
    s.blueprint = MagicMock()
    s.blueprint.id = "bp123456xyz"
    s.requirements.must_have = ["MFA"]
    s.created_at = "2026-01-01"
    s.updated_at = "2026-01-02"
    return s


def _ready_builder(session):
    b = MagicMock()
    b.start_session.return_value = session
    b.set_goal.return_value = session
    b.submit_answers.return_value = session
    b.is_ready_to_generate.return_value = True
    wf = MagicMock()
    wf.describe.return_value = "Workflow description"
    b.generate_workflow.return_value = wf
    return b


class TestStart:
    def test_with_goal_generates_and_saves_blueprint(self):
        session = _session()
        builder = _ready_builder(session)
        storage = MagicMock()
        with patch(STORAGE, return_value=storage), patch(BUILDER, return_value=builder):
            rc = cmd_start(SimpleNamespace(goal="harden auth", non_interactive=False))
        assert rc == 0
        builder.set_goal.assert_called_once()
        storage.save_blueprint.assert_called_once()

    def test_no_goal_empty_form_returns_one(self):
        session = _session()
        builder = _ready_builder(session)
        with (
            patch(STORAGE, return_value=MagicMock()),
            patch(BUILDER, return_value=builder),
            patch(RENDER, return_value={"goal": ""}),
        ):
            rc = cmd_start(SimpleNamespace(goal=None, non_interactive=False))
        assert rc == 1

    def test_interactive_questioning_loop(self):
        session = _session()
        builder = _ready_builder(session)
        # First not ready (enter loop), then ready (exit), then ready (generate).
        builder.is_ready_to_generate.side_effect = [False, True, True]
        builder.get_next_questions.return_value = MagicMock()
        builder.get_session_summary.return_value = {"requirements_completeness": 0.7}
        with (
            patch(STORAGE, return_value=MagicMock()),
            patch(BUILDER, return_value=builder),
            patch(RENDER, return_value={"a": "b"}),
        ):
            rc = cmd_start(SimpleNamespace(goal="x", non_interactive=False))
        assert rc == 0
        builder.submit_answers.assert_called_once()

    def test_loop_breaks_when_no_form(self):
        session = _session()
        builder = _ready_builder(session)
        # Enter loop (not ready), get no form -> break; stay not-ready -> no generate.
        builder.is_ready_to_generate.side_effect = [False, False]
        builder.get_next_questions.return_value = None
        with (
            patch(STORAGE, return_value=MagicMock()),
            patch(BUILDER, return_value=builder),
            patch(RENDER, return_value={}),
        ):
            rc = cmd_start(SimpleNamespace(goal="x", non_interactive=False))
        assert rc == 0
        builder.generate_workflow.assert_not_called()


class TestResume:
    def test_not_found_returns_one(self):
        storage = MagicMock()
        storage.load_session.return_value = None
        storage.list_sessions.return_value = []
        with patch(STORAGE, return_value=storage), patch(BUILDER, return_value=MagicMock()):
            rc = cmd_resume(SimpleNamespace(session_id="zzz"))
        assert rc == 1

    def test_multiple_partial_matches_returns_one(self):
        storage = MagicMock()
        storage.load_session.return_value = None
        storage.list_sessions.return_value = [
            {"session_id": "abc111", "state": "completed"},
            {"session_id": "abc222", "state": "in_progress"},
        ]
        with patch(STORAGE, return_value=storage), patch(BUILDER, return_value=MagicMock()):
            rc = cmd_resume(SimpleNamespace(session_id="abc"))
        assert rc == 1

    def test_already_completed_returns_zero(self):
        session = _session(state=SessionState.COMPLETED)
        storage = MagicMock()
        storage.load_session.return_value = session
        builder = MagicMock()
        with patch(STORAGE, return_value=storage), patch(BUILDER, return_value=builder):
            rc = cmd_resume(SimpleNamespace(session_id="abcd1234"))
        assert rc == 0

    def test_partial_match_then_generates(self):
        session = _session()
        storage = MagicMock()
        # Direct load misses; single partial match resolves.
        storage.load_session.side_effect = [None, session]
        storage.list_sessions.return_value = [{"session_id": "abcd1234efgh", "state": "ready"}]
        builder = _ready_builder(session)
        with (
            patch(STORAGE, return_value=storage),
            patch(BUILDER, return_value=builder),
            patch(RENDER, return_value={}),
        ):
            rc = cmd_resume(SimpleNamespace(session_id="abcd"))
        assert rc == 0
        builder.generate_workflow.assert_called_once()

    def test_questioning_loop_then_generates(self):
        session = _session()  # READY_TO_GENERATE (not completed) -> enters loop
        storage = MagicMock()
        storage.load_session.return_value = session
        builder = MagicMock()
        builder.is_ready_to_generate.side_effect = [False, True, True]
        builder.get_next_questions.return_value = MagicMock()
        builder.submit_answers.return_value = session
        wf = MagicMock()
        wf.describe.return_value = "WF"
        builder.generate_workflow.return_value = wf
        with (
            patch(STORAGE, return_value=storage),
            patch(BUILDER, return_value=builder),
            patch(RENDER, return_value={}),
        ):
            rc = cmd_resume(SimpleNamespace(session_id="abcd1234efgh"))
        assert rc == 0
        builder.submit_answers.assert_called_once()

    def test_loop_breaks_when_no_form(self):
        session = _session()
        storage = MagicMock()
        storage.load_session.return_value = session
        builder = MagicMock()
        builder.is_ready_to_generate.side_effect = [False, False]
        builder.get_next_questions.return_value = None  # -> break
        with patch(STORAGE, return_value=storage), patch(BUILDER, return_value=builder):
            rc = cmd_resume(SimpleNamespace(session_id="abcd1234efgh"))
        assert rc == 0
        builder.generate_workflow.assert_not_called()


class TestList:
    def test_invalid_state_returns_one(self):
        with patch(STORAGE, return_value=MagicMock()):
            rc = cmd_list(SimpleNamespace(state="bogus", limit=20))
        assert rc == 1

    def test_empty_returns_zero(self):
        storage = MagicMock()
        storage.list_sessions.return_value = []
        with patch(STORAGE, return_value=storage):
            rc = cmd_list(SimpleNamespace(state=None, limit=20))
        assert rc == 0

    def test_populated_renders_table(self):
        storage = MagicMock()
        storage.list_sessions.return_value = [
            {
                "session_id": "abcd1234efgh",
                "state": "completed",
                "goal": "g" * 50,  # exercises the >40 truncation branch
                "updated_at": "2026-01-02T10:00:00",
            },
            {"session_id": "ef567890", "state": "in_progress"},  # missing goal/updated
        ]
        with patch(STORAGE, return_value=storage):
            rc = cmd_list(SimpleNamespace(state="completed", limit=10))
        assert rc == 0


class TestBlueprints:
    def test_empty_returns_zero(self):
        storage = MagicMock()
        storage.list_blueprints.return_value = []
        with patch(STORAGE, return_value=storage):
            rc = cmd_blueprints(SimpleNamespace(domain=None, limit=20))
        assert rc == 0

    def test_populated_renders_table(self):
        storage = MagicMock()
        storage.list_blueprints.return_value = [
            {
                "id": "bp123456",
                "name": "Security Review",
                "domain": "security",
                "agents_count": 3,
                "generated_at": "2026-01-01T09:00:00",
            },
            {},  # missing id -> "?" branch
        ]
        with patch(STORAGE, return_value=storage):
            rc = cmd_blueprints(SimpleNamespace(domain="security", limit=20))
        assert rc == 0


class TestShow:
    def test_session_details(self):
        storage = MagicMock()
        storage.load_session.return_value = _session()
        with patch(STORAGE, return_value=storage):
            rc = cmd_show(SimpleNamespace(id="abcd1234"))
        assert rc == 0

    def test_blueprint_details(self):
        storage = MagicMock()
        storage.load_session.return_value = None
        bp = MagicMock()
        bp.name = "Sec"
        bp.id = "bp1"
        bp.domain = "security"
        bp.supported_languages = ["python"]
        bp.quality_focus = ["safety"]
        agent = MagicMock()
        agent.spec.name = "scanner"
        agent.spec.role.value = "analyst"
        agent.spec.goal = "find issues"
        bp.agents = [agent]
        stage = MagicMock()
        stage.name = "scan"
        stage.parallel = True
        stage.agent_ids = ["scanner"]
        bp.stages = [stage]
        storage.load_blueprint.return_value = bp
        with patch(STORAGE, return_value=storage):
            rc = cmd_show(SimpleNamespace(id="bp1"))
        assert rc == 0

    def test_not_found_returns_one(self):
        storage = MagicMock()
        storage.load_session.return_value = None
        storage.load_blueprint.return_value = None
        with patch(STORAGE, return_value=storage):
            rc = cmd_show(SimpleNamespace(id="ghost"))
        assert rc == 1


class TestDelete:
    def test_cancel_when_not_confirmed(self):
        with patch(STORAGE, return_value=MagicMock()), patch("builtins.input", return_value="n"):
            rc = cmd_delete(SimpleNamespace(session_id="s1", force=False))
        assert rc == 0

    def test_force_delete_success(self):
        storage = MagicMock()
        storage.delete_session.return_value = True
        with patch(STORAGE, return_value=storage):
            rc = cmd_delete(SimpleNamespace(session_id="s1", force=True))
        assert rc == 0

    def test_force_delete_not_found(self):
        storage = MagicMock()
        storage.delete_session.return_value = False
        with patch(STORAGE, return_value=storage):
            rc = cmd_delete(SimpleNamespace(session_id="s1", force=True))
        assert rc == 1


class TestExport:
    def test_not_found_returns_one(self):
        storage = MagicMock()
        storage.load_blueprint.return_value = None
        with patch(STORAGE, return_value=storage):
            rc = cmd_export(SimpleNamespace(blueprint_id="ghost", output=None))
        assert rc == 1

    def test_stdout_output(self, capsys):
        storage = MagicMock()
        bp = MagicMock()
        bp.to_dict.return_value = {"id": "bp1"}
        storage.load_blueprint.return_value = bp
        with patch(STORAGE, return_value=storage):
            rc = cmd_export(SimpleNamespace(blueprint_id="bp1", output=None))
        assert rc == 0
        assert '"id": "bp1"' in capsys.readouterr().out

    def test_file_output(self, tmp_path):
        storage = MagicMock()
        bp = MagicMock()
        bp.to_dict.return_value = {"id": "bp1"}
        storage.load_blueprint.return_value = bp
        out = tmp_path / "bp.json"
        with patch(STORAGE, return_value=storage):
            rc = cmd_export(SimpleNamespace(blueprint_id="bp1", output=str(out)))
        assert rc == 0
        assert out.exists()


class TestMain:
    def test_no_command_prints_help(self):
        assert main([]) == 0

    def test_dispatches_to_command(self):
        with patch("attune.socratic.cli.cmd_list", return_value=0) as mock_list:
            rc = main(["list"])
        assert rc == 0
        mock_list.assert_called_once()

    def test_keyboard_interrupt_returns_130(self):
        with patch("attune.socratic.cli.cmd_list", side_effect=KeyboardInterrupt):
            assert main(["list"]) == 130

    def test_exception_returns_one(self):
        with patch("attune.socratic.cli.cmd_list", side_effect=RuntimeError("boom")):
            assert main(["list"]) == 1
