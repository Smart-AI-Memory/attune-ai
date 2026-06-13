"""Behavioral tests for the first_time_init SessionStart hook.

The hook decides whether a project needs Attune initialization and, on
request, creates the .attune/ scaffold and default config. These tests
drive every public function against real tmp_path directories — the
already-initialized / never-ask / needs-init branches of check_init, the
init / never / skip_once branches of handle_init_response, and the
error-handling paths of initialize_project (exercised by pointing the
project root at a plain file so directory and file creation fail).
"""

from __future__ import annotations

from pathlib import Path

from attune.hooks.scripts import first_time_init as hook

# ---------------------------------------------------------------------------
# get_project_root
# ---------------------------------------------------------------------------


class TestGetProjectRoot:
    def test_uses_explicit_project_path(self, tmp_path):
        assert hook.get_project_root(project_path=str(tmp_path)) == Path(str(tmp_path))

    def test_falls_back_to_cwd(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        assert hook.get_project_root() == Path.cwd()


# ---------------------------------------------------------------------------
# is_initialized / never-ask helpers
# ---------------------------------------------------------------------------


class TestInitializedState:
    def test_not_initialized_when_empty(self, tmp_path):
        assert hook.is_initialized(tmp_path) is False

    def test_initialized_when_attune_dir_present(self, tmp_path):
        (tmp_path / ".attune").mkdir()
        assert hook.is_initialized(tmp_path) is True

    def test_initialized_when_config_present(self, tmp_path):
        (tmp_path / "attune.config.yaml").write_text("x\n")
        assert hook.is_initialized(tmp_path) is True

    def test_should_skip_init_reflects_marker(self, tmp_path):
        assert hook.should_skip_init(tmp_path) is False
        hook.mark_never_ask(tmp_path)
        assert hook.should_skip_init(tmp_path) is True

    def test_mark_never_ask_writes_marker_file(self, tmp_path):
        hook.mark_never_ask(tmp_path)
        marker = hook.get_never_ask_file(tmp_path)
        assert marker.exists()
        assert "Created:" in marker.read_text()


# ---------------------------------------------------------------------------
# initialize_project
# ---------------------------------------------------------------------------


class TestInitializeProject:
    def test_creates_dirs_config_and_gitignore(self, tmp_path):
        result = hook.initialize_project(tmp_path)

        assert result["success"] is True
        assert result["errors"] == []
        assert ".attune" in result["created_directories"]
        assert "attune.config.yaml" in result["created_files"]
        assert (tmp_path / "attune.config.yaml").exists()
        assert (tmp_path / ".attune" / "compact_states").is_dir()
        assert (tmp_path / ".attune" / ".gitignore_additions").exists()

    def test_skips_existing_config(self, tmp_path):
        (tmp_path / "attune.config.yaml").write_text("preexisting\n")
        result = hook.initialize_project(tmp_path)

        # config already there -> not re-created / not listed
        assert "attune.config.yaml" not in result["created_files"]
        assert (tmp_path / "attune.config.yaml").read_text() == "preexisting\n"

    def test_records_errors_when_root_is_a_file(self, tmp_path):
        blocker = tmp_path / "not_a_dir"
        blocker.write_text("file, not a directory\n")

        result = hook.initialize_project(blocker)

        # every dir/file creation under a file path fails
        assert result["success"] is False
        assert result["errors"]


# ---------------------------------------------------------------------------
# check_init
# ---------------------------------------------------------------------------


class TestCheckInit:
    def test_already_initialized(self, tmp_path):
        (tmp_path / ".attune").mkdir()
        result = hook.check_init(project_path=str(tmp_path))

        assert result["already_initialized"] is True
        assert result["needs_init"] is False

    def test_skipped_when_never_marker_present(self, tmp_path):
        hook.mark_never_ask(tmp_path)
        result = hook.check_init(project_path=str(tmp_path))

        assert result["skipped"] is True
        assert result["prompt_user"] is False

    def test_needs_init_offers_prompt(self, tmp_path):
        result = hook.check_init(project_path=str(tmp_path))

        assert result["needs_init"] is True
        assert result["prompt_user"] is True
        actions = [opt["action"] for opt in result["prompt"]["options"]]
        assert actions == ["init", "skip_once", "never"]


# ---------------------------------------------------------------------------
# handle_init_response
# ---------------------------------------------------------------------------


class TestHandleInitResponse:
    def test_init_action_initializes_and_messages(self, tmp_path):
        result = hook.handle_init_response("init", project_path=str(tmp_path))

        assert result["success"] is True
        assert result["message"] == "Attune AI initialized successfully!"
        assert (tmp_path / "attune.config.yaml").exists()

    def test_init_action_reports_errors(self, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.write_text("x\n")
        result = hook.handle_init_response("init", project_path=str(blocker))

        assert result["success"] is False
        assert result["message"] == "Initialization completed with errors."

    def test_never_action_marks_marker(self, tmp_path):
        result = hook.handle_init_response("never", project_path=str(tmp_path))

        assert result["action"] == "never"
        assert hook.should_skip_init(tmp_path) is True

    def test_skip_once_action_is_noop(self, tmp_path):
        result = hook.handle_init_response("skip_once", project_path=str(tmp_path))

        assert result["action"] == "skip_once"
        assert hook.should_skip_init(tmp_path) is False


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def test_main_delegates_to_check_init(tmp_path):
    result = hook.main(project_path=str(tmp_path))
    assert result["checked"] is True
    assert result["needs_init"] is True
