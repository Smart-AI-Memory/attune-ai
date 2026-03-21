"""Tests for spec-aware lifecycle context."""

from attune.voice.spec_context import _LIFECYCLE_ORDER, get_spec_next_action


class TestLifecycleOrdering:
    """Test lifecycle stage ordering via get_spec_next_action."""

    def test_code_review_to_security_audit(self, tmp_path, monkeypatch):
        """Code review is followed by security audit."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "test.md").write_text('<task id="1" name="t"><objective>x</objective></task>')
        monkeypatch.chdir(tmp_path)

        result = get_spec_next_action("code-review")
        assert len(result) == 1
        assert result[0].workflow_name == "security-audit"

    def test_release_prep_is_terminal(self, tmp_path, monkeypatch):
        """Release prep is the last stage — returns empty."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "test.md").write_text('<task id="1" name="t"><objective>x</objective></task>')
        monkeypatch.chdir(tmp_path)

        result = get_spec_next_action("release-prep")
        assert result == []

    def test_unknown_workflow_returns_empty(self, tmp_path, monkeypatch):
        """Workflows not in the lifecycle return empty."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "test.md").write_text('<task id="1" name="t"><objective>x</objective></task>')
        monkeypatch.chdir(tmp_path)

        result = get_spec_next_action("unknown-workflow")
        assert result == []

    def test_dependency_check_to_doc_gen(self, tmp_path, monkeypatch):
        """Dependency check is followed by doc gen."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "test.md").write_text('<task id="1" name="t"><objective>x</objective></task>')
        monkeypatch.chdir(tmp_path)

        result = get_spec_next_action("dependency-check")
        assert len(result) == 1
        assert result[0].workflow_name == "doc-gen"

    def test_lifecycle_order_has_expected_stages(self):
        """Lifecycle order includes key stages."""
        assert "code-review" in _LIFECYCLE_ORDER
        assert "release-prep" in _LIFECYCLE_ORDER
        assert _LIFECYCLE_ORDER[-1] == "release-prep"


class TestGetSpecNextAction:
    """Test spec-aware suggestion generation."""

    def test_no_plans_dir_returns_empty(self, tmp_path, monkeypatch):
        """Returns empty when no .claude/plans/ exists."""
        monkeypatch.chdir(tmp_path)
        result = get_spec_next_action("code-review")
        assert result == []

    def test_empty_plans_dir_returns_empty(self, tmp_path, monkeypatch):
        """Returns empty when plans dir has no spec files."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = get_spec_next_action("code-review")
        assert result == []

    def test_spec_with_tasks_generates_suggestion(self, tmp_path, monkeypatch):
        """Returns a suggestion when an active spec with tasks exists."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        spec = plans / "feature.md"
        spec.write_text(
            '# Feature\n\n<task id="1" name="setup">' "<objective>Do setup</objective></task>\n",
        )
        monkeypatch.chdir(tmp_path)

        result = get_spec_next_action("code-review")
        assert len(result) == 1
        assert result[0].workflow_name == "security-audit"
        assert "feature" in result[0].description.lower()

    def test_spec_without_tasks_returns_empty(self, tmp_path, monkeypatch):
        """Returns empty when spec exists but has no task blocks."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        spec = plans / "notes.md"
        spec.write_text("# Just some notes\n\nNo XML tasks here.\n")
        monkeypatch.chdir(tmp_path)

        result = get_spec_next_action("code-review")
        assert result == []

    def test_workspace_root_parameter(self, tmp_path):
        """Accepts explicit workspace_root instead of relying on cwd."""
        plans = tmp_path / ".claude" / "plans"
        plans.mkdir(parents=True)
        (plans / "spec.md").write_text(
            '<task id="1" name="t"><objective>x</objective></task>',
        )

        result = get_spec_next_action("code-review", workspace_root=tmp_path)
        assert len(result) == 1
        assert result[0].workflow_name == "security-audit"
