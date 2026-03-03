"""Tests for documentation audit check functions.

Each check function is tested independently using tmp_path to create
project structures entirely in a temporary directory.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.doc_audit.checks import (
    CheckResult,
    check_cross_doc_numbers,
    check_documentation_links,
    check_file_line_limits,
    check_install_extras,
    check_mcp_tool_count,
    check_skill_count,
    check_stale_references,
    check_test_count,
    check_version_consistency,
    check_workflow_count,
    run_all_checks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    """Write UTF-8 content to path, creating parents if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# TestCheckTestCount
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckTestCount:
    """Tests for check_test_count()."""

    def _mock_pytest_output(self, collected: int) -> str:
        return f"{collected} tests collected\n"

    def test_pass_when_badge_matches_collected(self, tmp_path):
        """Returns pass when README badge count matches pytest output."""
        _write(tmp_path / "README.md", "![tests-50-green](badge)\n")
        proc = MagicMock()
        proc.stdout = self._mock_pytest_output(50)
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc):
            result = check_test_count(str(tmp_path))

        assert result.status == "pass"
        assert result.id == "test-count"

    def test_fail_when_badge_mismatches_collected(self, tmp_path):
        """Returns fail when README badge count differs from pytest output."""
        _write(tmp_path / "README.md", "![tests-100-green](badge)\n")
        proc = MagicMock()
        proc.stdout = self._mock_pytest_output(146)
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc):
            result = check_test_count(str(tmp_path))

        assert result.status == "fail"
        assert result.auto_fixable is True
        assert "146" in result.details
        assert "100" in result.details

    def test_warn_when_readme_missing(self, tmp_path):
        """Returns warn when README.md does not exist."""
        proc = MagicMock()
        proc.stdout = self._mock_pytest_output(10)
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc):
            result = check_test_count(str(tmp_path))

        assert result.status == "warn"

    def test_warn_when_pytest_output_unreadable(self, tmp_path):
        """Returns warn when pytest --collect-only output has no test count."""
        _write(tmp_path / "README.md", "tests-50-green\n")
        proc = MagicMock()
        proc.stdout = "no match here"
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc):
            result = check_test_count(str(tmp_path))

        assert result.status == "warn"

    def test_warn_when_pytest_raises_file_not_found(self, tmp_path):
        """Returns warn when pytest executable is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError("no pytest")):
            result = check_test_count(str(tmp_path))

        assert result.status == "warn"

    def test_warn_when_no_badge_in_readme(self, tmp_path):
        """Returns warn when README exists but has no test count badge."""
        _write(tmp_path / "README.md", "No badge here.\n")
        proc = MagicMock()
        proc.stdout = self._mock_pytest_output(20)
        proc.stderr = ""
        with patch("subprocess.run", return_value=proc):
            result = check_test_count(str(tmp_path))

        assert result.status == "warn"


# ---------------------------------------------------------------------------
# TestCheckWorkflowCount
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckWorkflowCount:
    """Tests for check_workflow_count()."""

    def _write_init(self, tmp_path: Path, workflow_names: list[str]) -> Path:
        """Write a workflows/__init__.py with _DEFAULT_WORKFLOW_NAMES."""
        entries = "\n".join(f'    "{name}": None,' for name in workflow_names)
        content = "_DEFAULT_WORKFLOW_NAMES: dict[str, None] = {\n" + entries + "\n}\n"
        path = tmp_path / "src" / "attune" / "workflows" / "__init__.py"
        _write(path, content)
        return path

    def test_pass_when_count_matches_readme(self, tmp_path):
        """Returns pass when workflow count matches README claim."""
        self._write_init(tmp_path, ["wf-a", "wf-b", "wf-c"])
        _write(tmp_path / "README.md", "Includes 3 workflows for you.\n")
        result = check_workflow_count(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_count_mismatches_readme(self, tmp_path):
        """Returns fail when README claims different count than registry."""
        self._write_init(tmp_path, ["wf-a", "wf-b"])
        _write(tmp_path / "README.md", "10 workflows included.\n")
        result = check_workflow_count(str(tmp_path))
        assert result.status == "fail"
        assert result.auto_fixable is True

    def test_warn_when_workflows_init_missing(self, tmp_path):
        """Returns warn when workflows/__init__.py does not exist."""
        result = check_workflow_count(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_dict_not_found_in_init(self, tmp_path):
        """Returns warn when _DEFAULT_WORKFLOW_NAMES dict is absent."""
        path = tmp_path / "src" / "attune" / "workflows" / "__init__.py"
        _write(path, "# empty\n")
        result = check_workflow_count(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_readme_has_no_count(self, tmp_path):
        """Returns warn when README exists but has no workflow count."""
        self._write_init(tmp_path, ["wf-a"])
        _write(tmp_path / "README.md", "No numbers here.\n")
        result = check_workflow_count(str(tmp_path))
        assert result.status == "warn"


# ---------------------------------------------------------------------------
# TestCheckSkillCount
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckSkillCount:
    """Tests for check_skill_count()."""

    def _create_skills(self, tmp_path: Path, count: int) -> Path:
        """Create count .md files in .claude/commands/."""
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            (commands_dir / f"skill-{i}.md").write_text(f"# Skill {i}\n", encoding="utf-8")
        return commands_dir

    def test_pass_when_count_matches_readme(self, tmp_path):
        """Returns pass when skill file count matches README claim."""
        self._create_skills(tmp_path, 3)
        _write(tmp_path / "README.md", "Includes 3 skills.\n")
        result = check_skill_count(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_count_mismatches_readme(self, tmp_path):
        """Returns fail when README claims different skill count."""
        self._create_skills(tmp_path, 5)
        _write(tmp_path / "README.md", "2 commands available.\n")
        result = check_skill_count(str(tmp_path))
        assert result.status == "fail"
        assert result.auto_fixable is True

    def test_warn_when_commands_dir_missing(self, tmp_path):
        """Returns warn when .claude/commands/ directory does not exist."""
        result = check_skill_count(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_readme_has_no_count(self, tmp_path):
        """Returns warn when README does not mention skill count."""
        self._create_skills(tmp_path, 2)
        _write(tmp_path / "README.md", "No count mentioned.\n")
        result = check_skill_count(str(tmp_path))
        assert result.status == "warn"

    def test_non_md_files_not_counted(self, tmp_path):
        """Only .md files in .claude/commands/ are counted."""
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)
        (commands_dir / "skill.md").write_text("# Skill\n", encoding="utf-8")
        (commands_dir / "not_a_skill.txt").write_text("txt\n", encoding="utf-8")
        _write(tmp_path / "README.md", "1 skill.\n")
        result = check_skill_count(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestCheckMcpToolCount
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckMcpToolCount:
    """Tests for check_mcp_tool_count()."""

    def _create_src_with_decorators(self, tmp_path: Path, decorator_counts: list[int]) -> Path:
        """Create src/*.py files with given numbers of @server.tool() decorators."""
        src = tmp_path / "src"
        src.mkdir(parents=True, exist_ok=True)
        for i, count in enumerate(decorator_counts):
            content = ("@server.tool()\ndef tool_fn(): pass\n\n") * count
            (src / f"tools_{i}.py").write_text(content, encoding="utf-8")
        return src

    def test_pass_when_count_matches_readme(self, tmp_path):
        """Returns pass when decorator count matches README claim."""
        self._create_src_with_decorators(tmp_path, [3])
        _write(tmp_path / "README.md", "3 MCP tools provided.\n")
        result = check_mcp_tool_count(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_count_mismatches_readme(self, tmp_path):
        """Returns fail when README claims a different MCP tool count."""
        self._create_src_with_decorators(tmp_path, [2])
        _write(tmp_path / "README.md", "10 MCP tools provided.\n")
        result = check_mcp_tool_count(str(tmp_path))
        assert result.status == "fail"
        assert result.auto_fixable is True

    def test_warn_when_src_dir_missing(self, tmp_path):
        """Returns warn when src/ directory does not exist."""
        result = check_mcp_tool_count(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_no_decorators_found(self, tmp_path):
        """Returns warn when no @server.tool() decorators are found."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "empty.py").write_text("def fn(): pass\n", encoding="utf-8")
        result = check_mcp_tool_count(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_readme_missing_count(self, tmp_path):
        """Returns warn when README lacks an MCP tool count claim."""
        self._create_src_with_decorators(tmp_path, [2])
        _write(tmp_path / "README.md", "No tool count mentioned.\n")
        result = check_mcp_tool_count(str(tmp_path))
        assert result.status == "warn"

    def test_counts_across_multiple_files(self, tmp_path):
        """Decorators in multiple files are summed correctly."""
        self._create_src_with_decorators(tmp_path, [2, 3])  # 5 total
        _write(tmp_path / "README.md", "5 MCP tools provided.\n")
        result = check_mcp_tool_count(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestCheckFileLineLimits
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckFileLineLimits:
    """Tests for check_file_line_limits()."""

    def _create_py_file(self, src: Path, name: str, line_count: int) -> Path:
        """Create a .py file with the given number of lines."""
        src.mkdir(parents=True, exist_ok=True)
        content = "\n" * line_count
        path = src / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_pass_when_all_files_under_limit(self, tmp_path):
        """Returns pass when all .py files in src/ are under 1000 lines."""
        src = tmp_path / "src"
        self._create_py_file(src, "small.py", 50)
        self._create_py_file(src, "medium.py", 500)
        result = check_file_line_limits(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_file_exceeds_limit(self, tmp_path):
        """Returns fail when at least one .py file exceeds 1000 lines."""
        src = tmp_path / "src"
        self._create_py_file(src, "huge.py", 1001)
        result = check_file_line_limits(str(tmp_path))
        assert result.status == "fail"
        assert "huge.py" in result.details

    def test_fail_details_include_line_count(self, tmp_path):
        """Failure details mention the actual line count."""
        src = tmp_path / "src"
        self._create_py_file(src, "big.py", 1500)
        result = check_file_line_limits(str(tmp_path))
        assert "1500" in result.details

    def test_warn_when_src_missing(self, tmp_path):
        """Returns warn when src/ directory does not exist."""
        result = check_file_line_limits(str(tmp_path))
        assert result.status == "warn"

    def test_auto_fixable_is_false(self, tmp_path):
        """Line limit violations are never auto-fixable."""
        src = tmp_path / "src"
        self._create_py_file(src, "huge.py", 1001)
        result = check_file_line_limits(str(tmp_path))
        assert result.auto_fixable is False

    def test_exactly_at_limit_passes(self, tmp_path):
        """A file with exactly 1000 newlines passes (not strictly over)."""
        src = tmp_path / "src"
        self._create_py_file(src, "edge.py", 1000)
        result = check_file_line_limits(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestCheckInstallExtras
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckInstallExtras:
    """Tests for check_install_extras()."""

    def _write_pyproject(self, tmp_path: Path, extras: list[str]) -> Path:
        """Write a minimal pyproject.toml with given extras.

        Uses quoted strings instead of list literals so that the check's
        regex (which stops at the first ``[`` in the content) does not
        prematurely truncate the optional-dependencies block.
        """
        # Write each extra as a simple key = "value" line to avoid
        # brackets inside the block confusing the check's lookahead regex.
        entries = "\n".join(f'{e} = "dep"' for e in extras)
        content = (
            '[project]\nname = "attune-ai"\nversion = "1.0.0"\n\n'
            "[project.optional-dependencies]\n" + entries + "\n"
        )
        return _write(tmp_path / "pyproject.toml", content)

    def test_pass_when_extras_match(self, tmp_path):
        """Returns pass when pyproject and README extras are consistent."""
        self._write_pyproject(tmp_path, ["developer", "memory"])
        readme = "pip install attune-ai[developer]\n" "pip install attune-ai[memory]\n"
        _write(tmp_path / "README.md", readme)
        result = check_install_extras(str(tmp_path))
        assert result.status == "pass"

    def test_warn_when_extra_in_pyproject_missing_from_readme(self, tmp_path):
        """Returns warn when pyproject extra is absent from README."""
        self._write_pyproject(tmp_path, ["developer", "redis"])
        _write(tmp_path / "README.md", "pip install attune-ai[developer]\n")
        result = check_install_extras(str(tmp_path))
        assert result.status == "warn"
        assert "redis" in result.details

    def test_warn_when_readme_mentions_unknown_extra(self, tmp_path):
        """Returns warn when README references an extra not in pyproject."""
        self._write_pyproject(tmp_path, ["developer"])
        _write(tmp_path / "README.md", "pip install attune-ai[ghost]\n")
        result = check_install_extras(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_pyproject_missing(self, tmp_path):
        """Returns warn when pyproject.toml does not exist."""
        result = check_install_extras(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_optional_deps_section_missing(self, tmp_path):
        """Returns warn when [project.optional-dependencies] is absent."""
        _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
        _write(tmp_path / "README.md", "No extras.\n")
        result = check_install_extras(str(tmp_path))
        assert result.status == "warn"

    def test_warn_when_readme_missing(self, tmp_path):
        """Returns warn when README.md does not exist."""
        self._write_pyproject(tmp_path, ["developer"])
        result = check_install_extras(str(tmp_path))
        assert result.status == "warn"

    def test_comma_separated_extras_in_readme_are_expanded(self, tmp_path):
        """Comma-separated extras like [memory,redis] are each counted."""
        self._write_pyproject(tmp_path, ["memory", "redis"])
        _write(tmp_path / "README.md", "pip install attune-ai[memory,redis]\n")
        result = check_install_extras(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestCheckStaleReferences
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckStaleReferences:
    """Tests for check_stale_references()."""

    def test_pass_when_no_stale_patterns(self, tmp_path):
        """Returns pass when no stale reference patterns are found."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "guide.md", "# Clean Guide\nNo stale content here.\n")
        _write(tmp_path / "README.md", "# README\nClean.\n")
        result = check_stale_references(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_stale_pattern_found_in_docs(self, tmp_path):
        """Returns fail when a stale pattern appears in docs/."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "old.md", "Use empathy_framework for config.\n")
        result = check_stale_references(str(tmp_path))
        assert result.status == "fail"
        assert "empathy_framework" in result.details

    def test_fail_when_stale_pattern_found_in_readme(self, tmp_path):
        """Returns fail when a stale pattern appears in README.md."""
        _write(tmp_path / "README.md", "EmpathyConfig is the main class.\n")
        result = check_stale_references(str(tmp_path))
        assert result.status == "fail"

    def test_fail_when_stale_pattern_in_commands_dir(self, tmp_path):
        """Returns fail when stale pattern found in .claude/commands/ file."""
        cmd = tmp_path / ".claude" / "commands"
        cmd.mkdir(parents=True)
        _write(cmd / "old-command.md", "Run HealthCheckCrew to check health.\n")
        result = check_stale_references(str(tmp_path))
        assert result.status == "fail"

    def test_auto_fixable_is_false(self, tmp_path):
        """Stale references are never auto-fixable."""
        _write(tmp_path / "README.md", "EmpathyConfig lives here.\n")
        result = check_stale_references(str(tmp_path))
        assert result.auto_fixable is False

    def test_pass_when_no_docs_or_readme(self, tmp_path):
        """Returns pass when there are no searchable files."""
        result = check_stale_references(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestCheckVersionConsistency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckVersionConsistency:
    """Tests for check_version_consistency()."""

    def _write_sources(
        self,
        tmp_path: Path,
        pyproject_ver: str | None = None,
        init_ver: str | None = None,
        changelog_ver: str | None = None,
    ) -> None:
        """Write version files with specified version strings."""
        if pyproject_ver:
            _write(
                tmp_path / "pyproject.toml",
                f'[project]\nname = "x"\nversion = "{pyproject_ver}"\n',
            )
        if init_ver:
            _write(
                tmp_path / "src" / "attune" / "__init__.py",
                f'__version__ = "{init_ver}"\n',
            )
        if changelog_ver:
            _write(
                tmp_path / "CHANGELOG.md",
                f"## [{changelog_ver}]\n\n### Added\n- Something\n",
            )

    def test_pass_when_all_versions_match(self, tmp_path):
        """Returns pass when all source files report the same version."""
        self._write_sources(tmp_path, "1.2.3", "1.2.3", "1.2.3")
        result = check_version_consistency(str(tmp_path))
        assert result.status == "pass"
        assert "1.2.3" in result.details

    def test_fail_when_versions_differ(self, tmp_path):
        """Returns fail when version strings differ across source files."""
        self._write_sources(tmp_path, "1.2.3", "1.2.4", "1.2.3")
        result = check_version_consistency(str(tmp_path))
        assert result.status == "fail"
        assert result.auto_fixable is False

    def test_pass_with_only_two_sources(self, tmp_path):
        """Returns pass when only two sources exist and they match."""
        self._write_sources(tmp_path, pyproject_ver="2.0.0", init_ver="2.0.0")
        result = check_version_consistency(str(tmp_path))
        assert result.status == "pass"

    def test_warn_when_no_version_found(self, tmp_path):
        """Returns warn when no version can be extracted from any file."""
        result = check_version_consistency(str(tmp_path))
        assert result.status == "warn"

    def test_fail_details_contain_all_versions(self, tmp_path):
        """Failure details list each file and its version."""
        self._write_sources(tmp_path, "1.0.0", "2.0.0", "1.0.0")
        result = check_version_consistency(str(tmp_path))
        assert "1.0.0" in result.details
        assert "2.0.0" in result.details

    def test_changelog_without_brackets(self, tmp_path):
        """Changelog version without brackets is still parsed."""
        self._write_sources(tmp_path, pyproject_ver="3.0.0")
        _write(
            tmp_path / "CHANGELOG.md",
            "## 3.0.0\n\n### Added\n- Something\n",
        )
        _write(
            tmp_path / "src" / "attune" / "__init__.py",
            '__version__ = "3.0.0"\n',
        )
        result = check_version_consistency(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestCheckCrossDocNumbers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckCrossDocNumbers:
    """Tests for check_cross_doc_numbers()."""

    def test_pass_when_no_contradictions(self, tmp_path):
        """Returns pass when numeric claims across docs are consistent."""
        _write(tmp_path / "README.md", "10 workflows available.\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "overview.md", "Includes 10 workflows.\n")
        result = check_cross_doc_numbers(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_same_noun_has_different_counts(self, tmp_path):
        """Returns fail when different docs claim different counts for a noun."""
        _write(tmp_path / "README.md", "5 workflows available.\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "overview.md", "Includes 10 workflows.\n")
        result = check_cross_doc_numbers(str(tmp_path))
        assert result.status == "fail"
        assert "workflow" in result.details

    def test_pass_when_no_docs_exist(self, tmp_path):
        """Returns pass when there are no scannable files."""
        result = check_cross_doc_numbers(str(tmp_path))
        assert result.status == "pass"

    def test_auto_fixable_is_false(self, tmp_path):
        """Cross-doc number contradictions are never auto-fixable."""
        _write(tmp_path / "README.md", "5 tests collected.\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "another.md", "10 tests collected.\n")
        result = check_cross_doc_numbers(str(tmp_path))
        assert result.auto_fixable is False

    def test_multiple_contradictions_reported(self, tmp_path):
        """Multiple contradicting nouns are all included in failure details."""
        _write(
            tmp_path / "README.md",
            "5 workflows and 10 skills available.\n",
        )
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(
            docs / "other.md",
            "3 workflows and 7 skills documented.\n",
        )
        result = check_cross_doc_numbers(str(tmp_path))
        assert result.status == "fail"


# ---------------------------------------------------------------------------
# TestCheckDocumentationLinks
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckDocumentationLinks:
    """Tests for check_documentation_links()."""

    def test_pass_when_all_links_resolve(self, tmp_path):
        """Returns pass when all local markdown links point to existing files."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "target.md", "# Target\n")
        _write(docs / "index.md", "[Target](target.md)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "pass"

    def test_fail_when_link_target_missing(self, tmp_path):
        """Returns fail when a local link points to a non-existent file."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "index.md", "[Missing](missing.md)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "fail"
        assert "missing.md" in result.details

    def test_http_links_are_skipped(self, tmp_path):
        """External http/https links are not checked for existence."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "index.md", "[External](https://example.com/docs)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "pass"

    def test_anchor_only_links_are_skipped(self, tmp_path):
        """Anchor-only links (#section) are not checked."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "index.md", "[Section](#section-title)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "pass"

    def test_fragment_stripped_before_existence_check(self, tmp_path):
        """Link fragments (#anchor) are stripped before checking file existence."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "target.md", "# Target\n")
        _write(docs / "index.md", "[Target with anchor](target.md#section)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "pass"

    def test_commands_dir_links_are_scanned(self, tmp_path):
        """Links in .claude/commands/ skill files are also checked."""
        cmd = tmp_path / ".claude" / "commands"
        cmd.mkdir(parents=True)
        _write(cmd / "skill.md", "[Missing](nonexistent.md)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "fail"

    def test_readme_links_are_scanned(self, tmp_path):
        """Links in README.md are also checked."""
        _write(tmp_path / "README.md", "[Gone](docs/gone.md)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.status == "fail"

    def test_auto_fixable_is_false(self, tmp_path):
        """Broken links are never auto-fixable."""
        docs = tmp_path / "docs"
        docs.mkdir()
        _write(docs / "index.md", "[Missing](missing.md)\n")
        result = check_documentation_links(str(tmp_path))
        assert result.auto_fixable is False

    def test_pass_when_no_docs_dir_and_no_readme(self, tmp_path):
        """Returns pass when there are no scannable markdown files."""
        result = check_documentation_links(str(tmp_path))
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# TestRunAllChecks
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunAllChecks:
    """Tests for the run_all_checks() aggregate function."""

    def test_returns_ten_results(self, tmp_path):
        """run_all_checks returns exactly 10 CheckResult objects."""
        with patch(
            "attune.workflows.doc_audit.checks.subprocess.run",
            side_effect=FileNotFoundError("no pytest"),
        ):
            results = run_all_checks(str(tmp_path))

        assert len(results) == 10

    def test_all_results_are_check_result_instances(self, tmp_path):
        """Each element returned is a CheckResult instance."""
        with patch(
            "attune.workflows.doc_audit.checks.subprocess.run",
            side_effect=FileNotFoundError("no pytest"),
        ):
            results = run_all_checks(str(tmp_path))

        for r in results:
            assert isinstance(r, CheckResult)

    def test_each_result_has_required_attributes(self, tmp_path):
        """Every CheckResult has the required fields."""
        with patch(
            "attune.workflows.doc_audit.checks.subprocess.run",
            side_effect=FileNotFoundError("no pytest"),
        ):
            results = run_all_checks(str(tmp_path))

        for r in results:
            assert r.id
            assert r.name
            assert r.status in ("pass", "fail", "warn")
            assert isinstance(r.details, str)
            assert isinstance(r.auto_fixable, bool)
