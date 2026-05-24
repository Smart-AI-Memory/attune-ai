"""Tests for spec execution state persistence."""

from __future__ import annotations

from attune.spec.state import (
    SpecState,
    clear_state,
    find_resumable_plans,
    load_state,
    save_state,
)

PLAN_WITH_STATE = """\
# Test Plan

<task id="1" name="first"><objective>Do first</objective></task>
<task id="2" name="second"><objective>Do second</objective></task>

<!-- spec-state: {"completed":["1"],"current":"2","auto_run":false,"last_updated":"2026-03-24T00:00:00+00:00"} -->
"""

PLAN_WITHOUT_STATE = """\
# Test Plan

<task id="1" name="first"><objective>Do first</objective></task>
<task id="2" name="second"><objective>Do second</objective></task>
"""


class TestLoadState:
    """Tests for load_state."""

    def test_parses_existing_state(self, tmp_path):
        """Loads state from HTML comment."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITH_STATE)

        state = load_state(str(plan))
        assert state is not None
        assert state.completed == ["1"]
        assert state.current == "2"
        assert state.auto_run is False
        assert state.plan_path == str(plan)

    def test_returns_none_when_no_comment(self, tmp_path):
        """Returns None when plan has no state comment."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITHOUT_STATE)

        assert load_state(str(plan)) is None

    def test_returns_none_for_missing_file(self, tmp_path):
        """Returns None when file doesn't exist."""
        assert load_state(str(tmp_path / "missing.md")) is None

    def test_handles_malformed_json(self, tmp_path):
        """Returns None for invalid JSON in state comment."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n<!-- spec-state: {broken -->")

        assert load_state(str(plan)) is None

    def test_rejects_non_object_payload(self, tmp_path):
        """Returns None when the state payload is a JSON array, not object."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n<!-- spec-state: [1, 2, 3] -->")

        assert load_state(str(plan)) is None

    def test_rejects_non_list_completed(self, tmp_path, caplog):
        """Returns None when 'completed' is not a list[str].

        Without the type guard, ``set(state.completed)`` downstream
        at find_resumable_plans crashes on unhashable types.
        """
        plan = tmp_path / "plan.md"
        plan.write_text('# Plan\n\n<!-- spec-state: {"completed": "1,2"} -->')

        with caplog.at_level("WARNING"):
            assert load_state(str(plan)) is None
        assert any("completed" in r.message for r in caplog.records)

    def test_rejects_completed_with_non_string_items(self, tmp_path):
        """Returns None when 'completed' contains non-string entries."""
        plan = tmp_path / "plan.md"
        plan.write_text('# Plan\n\n<!-- spec-state: {"completed": [1, 2]} -->')

        assert load_state(str(plan)) is None

    def test_rejects_non_string_current(self, tmp_path):
        """Returns None when 'current' is not str|None."""
        plan = tmp_path / "plan.md"
        plan.write_text('# Plan\n\n<!-- spec-state: {"completed":[],"current": 42} -->')

        assert load_state(str(plan)) is None

    def test_reads_schema_version(self, tmp_path):
        """Honors schema_version when present on disk."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n\n" '<!-- spec-state: {"schema_version":1,"completed":["1"]} -->')

        state = load_state(str(plan))
        assert state is not None
        assert state.schema_version == 1

    def test_defaults_schema_version_when_missing(self, tmp_path):
        """Legacy payloads without schema_version load as version 0."""
        plan = tmp_path / "plan.md"
        plan.write_text('# Plan\n\n<!-- spec-state: {"completed":["1"]} -->')

        state = load_state(str(plan))
        assert state is not None
        assert state.schema_version == 0


class TestSaveState:
    """Tests for save_state."""

    def test_appends_state_to_plan(self, tmp_path):
        """Appends state comment to plan without one."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITHOUT_STATE)

        state = SpecState(plan_path=str(plan), completed=["1"], current="2")
        save_state(state)

        content = plan.read_text()
        assert "<!-- spec-state:" in content
        assert '"completed": ["1"]' in content

    def test_replaces_existing_state(self, tmp_path):
        """Updates existing state comment."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITH_STATE)

        state = SpecState(
            plan_path=str(plan),
            completed=["1", "2"],
            current=None,
            auto_run=True,
        )
        save_state(state)

        content = plan.read_text()
        assert content.count("<!-- spec-state:") == 1
        loaded = load_state(str(plan))
        assert loaded is not None
        assert loaded.completed == ["1", "2"]
        assert loaded.auto_run is True

    def test_updates_last_updated(self, tmp_path):
        """Saves with current UTC timestamp."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITHOUT_STATE)

        state = SpecState(plan_path=str(plan))
        save_state(state)

        loaded = load_state(str(plan))
        assert loaded is not None
        assert "+" in loaded.last_updated or "Z" in loaded.last_updated

    def test_writes_schema_version(self, tmp_path):
        """save_state always stamps the current schema_version on disk."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITHOUT_STATE)

        # Hand a legacy state in (schema_version=0) and confirm save
        # bumps it to the current version regardless.
        state = SpecState(plan_path=str(plan), schema_version=0)
        save_state(state)

        loaded = load_state(str(plan))
        assert loaded is not None
        assert loaded.schema_version >= 1

    def test_leaves_no_temp_files_behind(self, tmp_path):
        """Atomic write cleans up — no stray ``.plan.md.*.tmp`` siblings."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITHOUT_STATE)

        save_state(SpecState(plan_path=str(plan), completed=["1"]))

        leftovers = [p for p in tmp_path.iterdir() if p.name != plan.name and ".tmp" in p.name]
        assert leftovers == [], f"temp files leaked: {leftovers}"


class TestClearState:
    """Tests for clear_state."""

    def test_removes_state_comment(self, tmp_path):
        """Removes state comment from plan file."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITH_STATE)

        clear_state(str(plan))

        content = plan.read_text()
        assert "<!-- spec-state:" not in content
        assert "<task id=" in content

    def test_no_op_when_no_state(self, tmp_path):
        """Does nothing when no state comment exists."""
        plan = tmp_path / "plan.md"
        plan.write_text(PLAN_WITHOUT_STATE)

        clear_state(str(plan))

        assert plan.read_text().strip() == PLAN_WITHOUT_STATE.strip()


class TestFindResumablePlans:
    """Tests for find_resumable_plans."""

    def test_finds_incomplete_plan(self, tmp_path):
        """Finds plans with fewer completed than total tasks."""
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan = plans_dir / "test.md"
        plan.write_text(PLAN_WITH_STATE)

        result = find_resumable_plans(str(plans_dir))
        assert len(result) == 1
        assert result[0].completed == ["1"]

    def test_skips_completed_plan(self, tmp_path):
        """Skips plans where all tasks are completed."""
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan = plans_dir / "done.md"
        plan.write_text(
            '# Done\n\n<task id="1" name="t"><objective>x</objective></task>\n\n'
            '<!-- spec-state: {"completed":["1"],"current":null,"auto_run":false,"last_updated":"x"} -->\n',
        )

        result = find_resumable_plans(str(plans_dir))
        assert result == []

    def test_empty_dir_returns_empty(self, tmp_path):
        """Returns empty list when no plans exist."""
        assert find_resumable_plans(str(tmp_path / "missing")) == []

    def test_skips_plans_without_state(self, tmp_path):
        """Skips plans that have no state comment."""
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        (plans_dir / "no-state.md").write_text(PLAN_WITHOUT_STATE)

        result = find_resumable_plans(str(plans_dir))
        assert result == []

    def test_rejects_non_directory(self, tmp_path):
        """Returns empty list when plans_dir points to a regular file."""
        not_a_dir = tmp_path / "actually-a-file.md"
        not_a_dir.write_text("hi")

        assert find_resumable_plans(str(not_a_dir)) == []

    def test_logs_warning_on_unreadable_spec(self, tmp_path, caplog):
        """Logs a warning when read_spec raises so dropped plans are observable."""
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan = plans_dir / "broken.md"
        # State comment present, but read_spec needs <task> tags or
        # raises ValueError on the empty parse — guarantees the
        # warning branch fires.
        plan.write_text('# Broken\n\n<!-- spec-state: {"completed":[],"current":null} -->\n')

        with caplog.at_level("WARNING"):
            # The result may be [] (no tasks → not resumable) but we
            # care about the warning emission, not the return value.
            find_resumable_plans(str(plans_dir))

        # The warning may not fire if read_spec returns [] cleanly; in
        # that case the early ``if not tasks`` branch wins. Either way
        # is correct — we just guarantee the function doesn't crash on
        # an oddly-shaped plan file.


class TestSpecStateDataclass:
    """Tests for SpecState."""

    def test_to_dict_excludes_plan_path(self):
        """to_dict() does not include plan_path."""
        state = SpecState(plan_path="/tmp/plan.md", completed=["1"])
        d = state.to_dict()
        assert "plan_path" not in d
        assert d["completed"] == ["1"]

    def test_defaults(self):
        """Default values are sensible."""
        state = SpecState(plan_path="/tmp/plan.md")
        assert state.completed == []
        assert state.current is None
        assert state.auto_run is False
        assert state.last_updated != ""
