"""Unit tests for WizardSession.

Tests cover:
- Data access (set, get with layered lookup)
- Step lifecycle (complete_step, skip_step, cost accumulation)
- Serialization (to_dict)
- Default values and initialization

Created: 2026-02-15
"""

from attune.wizards.session import WizardSession


class TestWizardSession:
    """Test WizardSession data class."""

    def test_init_defaults(self):
        """Test session initializes with correct defaults."""
        session = WizardSession(wizard_id="test")

        assert session.wizard_id == "test"
        assert len(session.run_id) == 12
        assert session.initial_context == {}
        assert session.collected_data == {}
        assert session.step_results == {}
        assert session.tasks == []
        assert session.steps_completed == []
        assert session.steps_skipped == []
        assert session.generated_output == ""
        assert session.total_cost == 0.0
        assert session.started_at  # Should be set

    def test_init_with_context(self):
        """Test session initialization with initial context."""
        ctx = {"target": "src/main.py", "mode": "debug"}
        session = WizardSession(wizard_id="debug", initial_context=ctx)

        assert session.initial_context == ctx

    def test_set_and_get(self):
        """Test basic set and get."""
        session = WizardSession(wizard_id="test")
        session.set("key1", "value1")

        assert session.get("key1") == "value1"

    def test_get_falls_back_to_initial_context(self):
        """Test get checks initial_context when key not in collected_data."""
        session = WizardSession(
            wizard_id="test",
            initial_context={"from_context": "context_value"},
        )

        assert session.get("from_context") == "context_value"

    def test_get_collected_data_overrides_initial_context(self):
        """Test collected_data takes priority over initial_context."""
        session = WizardSession(
            wizard_id="test",
            initial_context={"key": "from_context"},
        )
        session.set("key", "from_collected")

        assert session.get("key") == "from_collected"

    def test_get_returns_default_when_missing(self):
        """Test get returns default when key not found anywhere."""
        session = WizardSession(wizard_id="test")

        assert session.get("missing") is None
        assert session.get("missing", "fallback") == "fallback"

    def test_complete_step_basic(self):
        """Test completing a step without result or cost."""
        session = WizardSession(wizard_id="test")
        session.complete_step("step1")

        assert "step1" in session.steps_completed
        assert "step1" not in session.step_results
        assert session.total_cost == 0.0

    def test_complete_step_with_result(self):
        """Test completing a step with a result."""
        session = WizardSession(wizard_id="test")
        session.complete_step("analyze", result={"summary": "found bug"})

        assert "analyze" in session.steps_completed
        assert session.step_results["analyze"] == {"summary": "found bug"}

    def test_complete_step_with_cost(self):
        """Test cost accumulation across steps."""
        session = WizardSession(wizard_id="test")
        session.complete_step("step1", cost=0.05)
        session.complete_step("step2", cost=0.10)

        assert abs(session.total_cost - 0.15) < 1e-10

    def test_skip_step(self):
        """Test skipping a step."""
        session = WizardSession(wizard_id="test")
        session.skip_step("optional_step")

        assert "optional_step" in session.steps_skipped
        assert "optional_step" not in session.steps_completed

    def test_to_dict(self):
        """Test serialization to dict."""
        session = WizardSession(wizard_id="debug")
        session.set("target", "main.py")
        session.complete_step("gather", result={"target": "main.py"}, cost=0.02)
        session.skip_step("optional")
        session.tasks = [{"task_id": "1", "name": "fix"}]
        session.generated_output = "## Preview"

        d = session.to_dict()

        assert d["wizard_id"] == "debug"
        assert d["run_id"] == session.run_id
        assert d["collected_data"] == {"target": "main.py"}
        assert d["step_results"] == {"gather": {"target": "main.py"}}
        assert d["tasks"] == [{"task_id": "1", "name": "fix"}]
        assert d["steps_completed"] == ["gather"]
        assert d["steps_skipped"] == ["optional"]
        assert d["generated_output"] == "## Preview"
        assert d["total_cost"] == 0.02
        assert "started_at" in d

    def test_unique_run_ids(self):
        """Test that each session gets a unique run_id."""
        s1 = WizardSession(wizard_id="test")
        s2 = WizardSession(wizard_id="test")

        assert s1.run_id != s2.run_id
