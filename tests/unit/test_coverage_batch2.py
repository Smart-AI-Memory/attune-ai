"""Coverage Batch 2 - Comprehensive tests for templates.

Targets coverage for:
- src/attune/templates.py (~75 stmts, 0% -> high coverage)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from attune.templates import (
    TEMPLATES,
    cmd_new,
    list_templates,
    scaffold_project,
)

# =============================================================================
# MODULE 2: templates.py
# =============================================================================


class TestTemplatesConstant:
    """Tests for the TEMPLATES constant dict."""

    def test_templates_has_four_entries(self) -> None:
        """Test TEMPLATES contains exactly 4 templates."""
        assert len(TEMPLATES) == 4

    def test_templates_keys(self) -> None:
        """Test TEMPLATES has expected keys."""
        assert set(TEMPLATES.keys()) == {
            "minimal",
            "python-cli",
            "python-fastapi",
            "python-agent",
        }

    def test_each_template_has_name_description_files(self) -> None:
        """Test each template has name, description, and files keys."""
        for tid, template in TEMPLATES.items():
            assert "name" in template, f"Template {tid} missing 'name'"
            assert "description" in template, f"Template {tid} missing 'description'"
            assert "files" in template, f"Template {tid} missing 'files'"

    def test_each_template_files_is_dict(self) -> None:
        """Test each template's files value is a dict."""
        for tid, template in TEMPLATES.items():
            assert isinstance(template["files"], dict), f"Template {tid} files not dict"


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_all_four_templates(self) -> None:
        """Test list_templates returns exactly 4 templates."""
        templates = list_templates()
        assert len(templates) == 4

    def test_each_has_id_name_description(self) -> None:
        """Test each template dict has id, name, and description keys."""
        for t in list_templates():
            assert "id" in t
            assert "name" in t
            assert "description" in t

    def test_template_ids_match_expected(self) -> None:
        """Test template IDs match expected set."""
        ids = {t["id"] for t in list_templates()}
        assert ids == {"minimal", "python-cli", "python-fastapi", "python-agent"}


class TestScaffoldProject:
    """Tests for scaffold_project function using tmp_path for file operations."""

    def test_minimal_creates_config_file(self, tmp_path: Path) -> None:
        """Test scaffold minimal template creates attune.config.yml."""
        target = tmp_path / "my_project"
        result = scaffold_project("minimal", "my_project", str(target))
        assert result["success"] is True
        assert result["template"] == "minimal"
        assert result["project_name"] == "my_project"
        assert (target / "attune.config.yml").exists()

    def test_minimal_creates_claude_md(self, tmp_path: Path) -> None:
        """Test scaffold minimal template creates .claude/CLAUDE.md."""
        target = tmp_path / "proj"
        scaffold_project("minimal", "proj", str(target))
        assert (target / ".claude" / "CLAUDE.md").exists()

    def test_minimal_creates_patterns_directory(self, tmp_path: Path) -> None:
        """Test scaffold creates patterns directory."""
        target = tmp_path / "proj"
        scaffold_project("minimal", "proj", str(target))
        assert (target / "patterns").is_dir()

    def test_unknown_template_returns_error(self, tmp_path: Path) -> None:
        """Test scaffold with unknown template returns error with available list."""
        result = scaffold_project("nonexistent", "test_proj", str(tmp_path / "out"))
        assert result["success"] is False
        assert "Unknown template" in result["error"]
        assert "available" in result
        assert isinstance(result["available"], list)

    def test_nonempty_dir_without_force_returns_error(self, tmp_path: Path) -> None:
        """Test scaffold to non-empty dir without force returns error."""
        target = tmp_path / "existing"
        target.mkdir()
        (target / "somefile.txt").write_text("content")
        result = scaffold_project("minimal", "test_proj", str(target))
        assert result["success"] is False
        assert "not empty" in result["error"]

    def test_nonempty_dir_with_force_succeeds(self, tmp_path: Path) -> None:
        """Test scaffold to non-empty dir with force=True succeeds."""
        target = tmp_path / "existing"
        target.mkdir()
        (target / "somefile.txt").write_text("content")
        result = scaffold_project("minimal", "test_proj", str(target), force=True)
        assert result["success"] is True

    def test_empty_dir_works(self, tmp_path: Path) -> None:
        """Test scaffold to empty existing dir works without force."""
        target = tmp_path / "empty_dir"
        target.mkdir()
        result = scaffold_project("minimal", "test_proj", str(target))
        assert result["success"] is True

    def test_replaces_project_name_placeholder(self, tmp_path: Path) -> None:
        """Test scaffold replaces {{project_name}} in file content."""
        target = tmp_path / "my_app"
        scaffold_project("minimal", "my_app", str(target))
        config_content = (target / "attune.config.yml").read_text()
        assert "my_app" in config_content
        assert "{{project_name}}" not in config_content

    def test_replaces_project_name_class_placeholder(self, tmp_path: Path) -> None:
        """Test scaffold replaces {{project_name_class}} in python-agent template."""
        target = tmp_path / "my_agent"
        result = scaffold_project("python-agent", "my_agent", str(target))
        assert result["success"] is True
        agent_file = target / "my_agent" / "agent.py"
        assert agent_file.exists()
        content = agent_file.read_text()
        assert "MyAgent" in content
        assert "{{project_name_class}}" not in content

    def test_project_name_class_with_hyphens(self, tmp_path: Path) -> None:
        """Test project name with hyphens gets converted to CamelCase class name."""
        target = tmp_path / "my-cool-agent"
        result = scaffold_project("python-agent", "my-cool-agent", str(target))
        assert result["success"] is True
        agent_file = target / "my-cool-agent" / "agent.py"
        content = agent_file.read_text()
        assert "MyCoolAgent" in content

    def test_gitignore_additions_append_existing(self, tmp_path: Path) -> None:
        """Test scaffold appends .gitignore_additions to existing .gitignore."""
        target = tmp_path / "proj_with_gitignore"
        target.mkdir(parents=True)
        gitignore = target / ".gitignore"
        gitignore.write_text("# existing\n*.pyc\n")
        result = scaffold_project("minimal", "test_proj", str(target), force=True)
        assert result["success"] is True
        content = gitignore.read_text()
        assert "# existing" in content
        assert ".attune/" in content

    def test_gitignore_additions_create_new(self, tmp_path: Path) -> None:
        """Test scaffold creates .gitignore from additions when none exists."""
        target = tmp_path / "new_proj"
        result = scaffold_project("minimal", "new_proj", str(target))
        assert result["success"] is True
        assert ".gitignore" in result["files_created"]

    def test_python_cli_creates_cli_module(self, tmp_path: Path) -> None:
        """Test python-cli template creates the CLI module files."""
        target = tmp_path / "mycli"
        result = scaffold_project("python-cli", "mycli", str(target))
        assert result["success"] is True
        assert (target / "mycli" / "__init__.py").exists()
        assert (target / "mycli" / "cli.py").exists()
        assert (target / "pyproject.toml").exists()
        assert (target / "README.md").exists()

    def test_python_fastapi_creates_main_module(self, tmp_path: Path) -> None:
        """Test python-fastapi template creates main.py."""
        target = tmp_path / "myapi"
        result = scaffold_project("python-fastapi", "myapi", str(target))
        assert result["success"] is True
        assert (target / "myapi" / "main.py").exists()
        assert (target / "myapi" / "__init__.py").exists()

    def test_python_agent_creates_agent_and_tests(self, tmp_path: Path) -> None:
        """Test python-agent template creates agent.py and test files."""
        target = tmp_path / "mybot"
        result = scaffold_project("python-agent", "mybot", str(target))
        assert result["success"] is True
        assert (target / "mybot" / "agent.py").exists()
        assert (target / "tests" / "__init__.py").exists()
        assert (target / "tests" / "test_agent.py").exists()

    def test_returns_next_steps(self, tmp_path: Path) -> None:
        """Test scaffold result includes next_steps list."""
        target = tmp_path / "proj"
        result = scaffold_project("minimal", "proj", str(target))
        assert "next_steps" in result
        assert len(result["next_steps"]) > 0

    def test_returns_target_dir(self, tmp_path: Path) -> None:
        """Test scaffold result includes target_dir."""
        target = tmp_path / "proj"
        result = scaffold_project("minimal", "proj", str(target))
        assert result["target_dir"] == str(target)

    def test_default_target_dir_uses_project_name(self, tmp_path: Path, monkeypatch) -> None:
        """Test scaffold uses project_name as default target dir when none given."""
        monkeypatch.chdir(tmp_path)
        result = scaffold_project("minimal", "auto_dir")
        assert result["success"] is True
        assert result["target_dir"] == "auto_dir"

    def test_files_created_list_not_empty(self, tmp_path: Path) -> None:
        """Test files_created list is populated."""
        target = tmp_path / "proj"
        result = scaffold_project("minimal", "proj", str(target))
        assert len(result["files_created"]) > 0

    def test_invalid_template_structure_returns_error(self, tmp_path: Path) -> None:
        """Test invalid template files structure returns error."""
        with patch.dict(
            "attune.templates.TEMPLATES",
            {"bad": {"name": "Bad", "description": "Bad template", "files": "not_a_dict"}},
        ):
            result = scaffold_project("bad", "proj", str(tmp_path / "proj"))
            assert result["success"] is False
            assert "Invalid template structure" in result["error"]


class TestCmdNew:
    """Tests for cmd_new CLI command handler."""

    def test_list_only_prints_templates(self, capsys) -> None:
        """Test cmd_new with list=True prints templates and returns 0."""
        args = SimpleNamespace(template=None, name=None, output=None, force=False, list=True)
        result = cmd_new(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Available Templates" in captured.out

    def test_no_template_or_name_returns_1(self, capsys) -> None:
        """Test cmd_new without template or name returns 1."""
        args = SimpleNamespace(template=None, name=None, output=None, force=False, list=False)
        result = cmd_new(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_template_without_name_returns_1(self, capsys) -> None:
        """Test cmd_new with template but no name returns 1."""
        args = SimpleNamespace(template="minimal", name=None, output=None, force=False, list=False)
        result = cmd_new(args)
        assert result == 1

    def test_valid_args_returns_0(self, tmp_path: Path, capsys) -> None:
        """Test cmd_new with valid template and name returns 0."""
        args = SimpleNamespace(
            template="minimal",
            name="test_project",
            output=str(tmp_path / "test_project"),
            force=False,
            list=False,
        )
        result = cmd_new(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Project created" in captured.out
        assert "Files created" in captured.out
        assert "Next steps" in captured.out

    def test_unknown_template_returns_1(self, capsys) -> None:
        """Test cmd_new with unknown template returns 1 and shows error."""
        args = SimpleNamespace(
            template="nonexistent",
            name="proj",
            output=None,
            force=False,
            list=False,
        )
        result = cmd_new(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "Available templates" in captured.out

    def test_getattr_defaults_for_missing_attrs(self, capsys) -> None:
        """Test cmd_new handles SimpleNamespace without expected attributes."""
        args = SimpleNamespace()
        result = cmd_new(args)
        assert result == 1

    def test_list_only_shows_all_template_ids(self, capsys) -> None:
        """Test listing shows template IDs for each known template."""
        args = SimpleNamespace(template=None, name=None, output=None, force=False, list=True)
        cmd_new(args)
        captured = capsys.readouterr()
        assert "minimal" in captured.out
        assert "python-cli" in captured.out
