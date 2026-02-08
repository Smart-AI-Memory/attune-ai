"""Tests for routing/chain_executor.py using real data.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from datetime import datetime

from attune.routing.chain_executor import (
    ChainConfig,
    ChainExecution,
    ChainExecutor,
    ChainStep,
    ChainTrigger,
)


class TestChainTrigger:
    """Test ChainTrigger data class."""

    def test_chain_trigger_initialization(self):
        """Test ChainTrigger can be created."""
        trigger = ChainTrigger(
            condition="high_severity > 5",
            next_workflow="remediation-wizard",
            approval_required=True,
            reason="Critical security issues found",
        )

        assert trigger.condition == "high_severity > 5"
        assert trigger.next_workflow == "remediation-wizard"
        assert trigger.approval_required is True
        assert trigger.reason == "Critical security issues found"

    def test_chain_trigger_defaults(self):
        """Test ChainTrigger uses default values."""
        trigger = ChainTrigger(condition="always", next_workflow="follow-up")

        assert trigger.approval_required is False
        assert trigger.reason == ""


class TestChainConfig:
    """Test ChainConfig data class."""

    def test_chain_config_initialization(self):
        """Test ChainConfig can be created."""
        config = ChainConfig(
            workflow_name="security-audit",
            auto_chain=True,
            description="Security audit with auto-remediation",
        )

        assert config.workflow_name == "security-audit"
        assert config.auto_chain is True
        assert config.description == "Security audit with auto-remediation"
        assert config.triggers == []

    def test_chain_config_with_triggers(self):
        """Test ChainConfig with triggers."""
        trigger1 = ChainTrigger("severity > 3", "fix-wizard")
        trigger2 = ChainTrigger("coverage < 80", "test-wizard")

        config = ChainConfig(workflow_name="audit", triggers=[trigger1, trigger2])

        assert len(config.triggers) == 2
        assert config.triggers[0].next_workflow == "fix-wizard"
        assert config.triggers[1].next_workflow == "test-wizard"

    def test_chain_config_defaults(self):
        """Test ChainConfig default values."""
        config = ChainConfig(workflow_name="test")

        assert config.auto_chain is True
        assert config.description == ""
        assert config.triggers == []


class TestChainStep:
    """Test ChainStep data class."""

    def test_chain_step_initialization(self):
        """Test ChainStep can be created."""
        step = ChainStep(
            workflow_name="security-scan", triggered_by="manual", approval_required=False
        )

        assert step.workflow_name == "security-scan"
        assert step.triggered_by == "manual"
        assert step.approval_required is False
        assert step.approved is None
        assert step.result == {}

    def test_chain_step_with_result(self):
        """Test ChainStep with execution result."""
        result_data = {"issues_found": 3, "severity": "high", "status": "completed"}

        step = ChainStep(
            workflow_name="analyzer",
            triggered_by="auto",
            approval_required=False,
            result=result_data,
        )

        assert step.result["issues_found"] == 3
        assert step.result["severity"] == "high"

    def test_chain_step_with_timestamps(self):
        """Test ChainStep with timestamps."""
        start_time = datetime.now()

        step = ChainStep(
            workflow_name="processor",
            triggered_by="condition",
            approval_required=True,
            started_at=start_time,
        )

        assert step.started_at == start_time
        assert step.completed_at is None

    def test_chain_step_approval_states(self):
        """Test ChainStep approval states."""
        # Pending approval
        pending = ChainStep(workflow_name="test", triggered_by="auto", approval_required=True)
        assert pending.approved is None

        # Approved
        approved = ChainStep(
            workflow_name="test", triggered_by="auto", approval_required=True, approved=True
        )
        assert approved.approved is True

        # Rejected
        rejected = ChainStep(
            workflow_name="test", triggered_by="auto", approval_required=True, approved=False
        )
        assert rejected.approved is False


class TestChainExecution:
    """Test ChainExecution data class."""

    def test_chain_execution_initialization(self):
        """Test ChainExecution can be created."""
        execution = ChainExecution(chain_id="chain_123", initial_workflow="security-audit")

        assert execution.chain_id == "chain_123"
        assert execution.initial_workflow == "security-audit"
        assert execution.steps == []
        assert execution.status == "running"
        assert execution.current_step == 0

    def test_chain_execution_with_steps(self):
        """Test ChainExecution with multiple steps."""
        step1 = ChainStep(workflow_name="scan", triggered_by="manual", approval_required=False)
        step2 = ChainStep(workflow_name="fix", triggered_by="auto", approval_required=True)

        execution = ChainExecution(
            chain_id="chain_456", initial_workflow="scan", steps=[step1, step2]
        )

        assert len(execution.steps) == 2
        assert execution.steps[0].workflow_name == "scan"
        assert execution.steps[1].workflow_name == "fix"

    def test_chain_execution_status_values(self):
        """Test ChainExecution different status values."""
        statuses = ["running", "completed", "waiting_approval", "failed"]

        for status in statuses:
            execution = ChainExecution(
                chain_id=f"chain_{status}", initial_workflow="test", status=status
            )
            assert execution.status == status

    def test_chain_execution_timestamps(self):
        """Test ChainExecution has started_at timestamp."""
        execution = ChainExecution(chain_id="chain_789", initial_workflow="test")

        assert execution.started_at is not None
        assert isinstance(execution.started_at, datetime)
        assert execution.completed_at is None


class TestChainExecutorInitialization:
    """Test ChainExecutor initialization."""

    def test_chain_executor_can_be_created(self):
        """Test ChainExecutor can be instantiated."""
        executor = ChainExecutor()

        assert executor is not None
        assert isinstance(executor, ChainExecutor)

    def test_chain_executor_with_nonexistent_config(self, tmp_path):
        """Test ChainExecutor handles missing config gracefully."""
        config_path = tmp_path / "nonexistent.yaml"
        executor = ChainExecutor(config_path=config_path)

        # Should initialize without error
        assert executor is not None
        assert executor.config_path == config_path


class TestConfigurationLoading:
    """Test YAML configuration loading."""

    def test_load_config_from_yaml_file(self, tmp_path):
        """Test loading chain configuration from YAML."""
        config_file = tmp_path / "chains.yaml"
        config_data = """
global:
  auto_chain_enabled: true
  max_chain_depth: 5

chains:
  security-audit:
    auto_chain: true
    description: "Security audit chain"
    triggers:
      - condition: "high_severity > 0"
        next: "remediation"
        approval_required: true
        reason: "High severity issues found"

templates:
  full-audit:
    steps:
      - security-audit
      - code-review
      - remediation
"""
        config_file.write_text(config_data)

        executor = ChainExecutor(config_path=config_file)

        # Verify global settings loaded
        assert executor._global_settings["auto_chain_enabled"] is True
        assert executor._global_settings["max_chain_depth"] == 5

        # Verify chain config loaded
        config = executor.get_chain_config("security-audit")
        assert config is not None
        assert config.workflow_name == "security-audit"
        assert config.auto_chain is True
        assert len(config.triggers) == 1
        assert config.triggers[0].condition == "high_severity > 0"
        assert config.triggers[0].next_workflow == "remediation"

        # Verify template loaded
        template = executor.get_template("full-audit")
        assert template == ["security-audit", "code-review", "remediation"]

    def test_load_config_handles_invalid_yaml(self, tmp_path):
        """Test that invalid YAML is handled gracefully."""
        config_file = tmp_path / "bad_chains.yaml"
        config_file.write_text("{ invalid yaml }")

        # Should not crash
        executor = ChainExecutor(config_path=config_file)
        assert executor is not None


class TestTriggerEvaluation:
    """Test condition evaluation for chain triggers."""

    def test_evaluate_numeric_greater_than(self, tmp_path):
        """Test numeric > comparison."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  test-wizard:
    triggers:
      - condition: "severity > 5"
        next: "next-wizard"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        # Should trigger when severity > 5
        result = {"severity": 10}
        triggers = executor.get_triggered_chains("test-wizard", result)
        assert len(triggers) == 1
        assert triggers[0].next_workflow == "next-wizard"

        # Should not trigger when severity <= 5
        result = {"severity": 5}
        triggers = executor.get_triggered_chains("test-wizard", result)
        assert len(triggers) == 0

    def test_evaluate_equality_condition(self, tmp_path):
        """Test equality == comparison."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  test-wizard:
    triggers:
      - condition: "status == 'failed'"
        next: "error-handler"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        result = {"status": "failed"}
        triggers = executor.get_triggered_chains("test-wizard", result)
        assert len(triggers) == 1

        result = {"status": "passed"}
        triggers = executor.get_triggered_chains("test-wizard", result)
        assert len(triggers) == 0

    def test_evaluate_not_equal_condition(self, tmp_path):
        """Test != comparison."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  test-wizard:
    triggers:
      - condition: "result != null"
        next: "processor"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        result = {"result": "data"}
        triggers = executor.get_triggered_chains("test-wizard", result)
        assert len(triggers) == 1

    def test_evaluate_handles_missing_variable(self, tmp_path):
        """Test condition with missing variable returns False."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  test-wizard:
    triggers:
      - condition: "nonexistent > 5"
        next: "next-wizard"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        result = {"other_var": 10}
        triggers = executor.get_triggered_chains("test-wizard", result)
        assert len(triggers) == 0

    def test_should_trigger_chain(self, tmp_path):
        """Test should_trigger_chain returns correct tuple."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  test-wizard:
    triggers:
      - condition: "count > 0"
        next: "next-wizard"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        # Should trigger
        result = {"count": 5}
        should_trigger, triggers = executor.should_trigger_chain("test-wizard", result)
        assert should_trigger is True
        assert len(triggers) == 1

        # Should not trigger
        result = {"count": 0}
        should_trigger, triggers = executor.should_trigger_chain("test-wizard", result)
        assert should_trigger is False
        assert len(triggers) == 0


class TestChainExecutionManagement:
    """Test chain execution creation and management."""

    def test_create_execution_with_initial_workflow(self):
        """Test creating a new chain execution."""
        executor = ChainExecutor()

        execution = executor.create_execution("test-wizard")

        assert execution.chain_id.startswith("chain_")
        assert execution.initial_workflow == "test-wizard"
        assert execution.status == "running"
        assert len(execution.steps) == 1
        assert execution.steps[0].workflow_name == "test-wizard"
        assert execution.steps[0].triggered_by == "manual"

    def test_create_execution_with_triggered_steps(self):
        """Test creating execution with pre-triggered steps."""
        executor = ChainExecutor()

        trigger1 = ChainTrigger("count > 0", "step2", approval_required=False)
        trigger2 = ChainTrigger("errors > 0", "step3", approval_required=True)

        execution = executor.create_execution(
            "initial-wizard", triggered_steps=[trigger1, trigger2]
        )

        assert len(execution.steps) == 3
        assert execution.steps[0].workflow_name == "initial-wizard"
        assert execution.steps[1].workflow_name == "step2"
        assert execution.steps[1].triggered_by == "count > 0"
        assert execution.steps[2].workflow_name == "step3"
        assert execution.steps[2].approval_required is True

    def test_approve_step(self):
        """Test approving a pending step."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        # Add a step requiring approval
        execution.steps.append(ChainStep("approval-wizard", "auto", approval_required=True))

        success = executor.approve_step(execution, 1)

        assert success is True
        assert execution.steps[1].approved is True

    def test_reject_step(self):
        """Test rejecting a pending step."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        execution.steps.append(ChainStep("approval-wizard", "auto", approval_required=True))

        success = executor.reject_step(execution, 1)

        assert success is True
        assert execution.steps[1].approved is False

    def test_approve_invalid_step_index(self):
        """Test approving invalid step index returns False."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        success = executor.approve_step(execution, 999)
        assert success is False

    def test_get_next_step_returns_first_incomplete(self):
        """Test get_next_step returns first incomplete step."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        # Mark first step complete
        execution.steps[0].completed_at = datetime.now()

        # Add incomplete step
        execution.steps.append(ChainStep("step2", "auto", approval_required=False, approved=True))

        next_step = executor.get_next_step(execution)

        assert next_step is not None
        assert next_step.workflow_name == "step2"

    def test_get_next_step_waits_for_approval(self, tmp_path):
        """Test get_next_step waits when approval required."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text("global:\n  max_chain_depth: 5")
        executor = ChainExecutor(config_path=config_file)

        execution = executor.create_execution("test-wizard")
        # Mark initial step as complete
        execution.steps[0].completed_at = datetime.now()

        # Add step requiring approval
        execution.steps.append(
            ChainStep("approval-step", "auto", approval_required=True, approved=None)
        )

        next_step = executor.get_next_step(execution)

        assert next_step is None
        assert execution.status == "waiting_approval"

    def test_get_next_step_skips_rejected(self):
        """Test get_next_step skips rejected steps."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        # Mark initial step as complete
        execution.steps[0].completed_at = datetime.now()

        # Add rejected step
        execution.steps.append(
            ChainStep("rejected-step", "auto", approval_required=True, approved=False)
        )

        # Add approved step
        execution.steps.append(
            ChainStep("approved-step", "auto", approval_required=False, approved=True)
        )

        next_step = executor.get_next_step(execution)

        # Should skip rejected and return approved
        assert next_step is not None
        assert next_step.workflow_name == "approved-step"

    def test_complete_step_marks_complete(self):
        """Test complete_step marks step as complete."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        step = execution.steps[0]
        result = {"status": "success", "data": [1, 2, 3]}

        executor.complete_step(execution, step, result)

        assert step.completed_at is not None
        assert step.result == result

    def test_complete_step_triggers_new_chains(self, tmp_path):
        """Test complete_step checks for new triggered chains."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  step1:
    triggers:
      - condition: "success == true"
        next: "step2"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        execution = executor.create_execution("step1")
        step = execution.steps[0]

        result = {"success": True}
        new_triggers = executor.complete_step(execution, step, result)

        assert len(new_triggers) == 1
        assert new_triggers[0].next_workflow == "step2"
        # New step should be added to execution
        assert len(execution.steps) == 2
        assert execution.steps[1].workflow_name == "step2"

    def test_complete_step_does_not_duplicate_wizards(self, tmp_path):
        """Test complete_step doesn't add duplicate wizards."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
chains:
  step1:
    triggers:
      - condition: "success == true"
        next: "step2"
"""
        )
        executor = ChainExecutor(config_path=config_file)

        execution = executor.create_execution("step1")
        # Manually add step2 already
        execution.steps.append(ChainStep("step2", "manual", approval_required=False))

        step = execution.steps[0]
        result = {"success": True}

        executor.complete_step(execution, step, result)

        # Should not add duplicate step2
        step2_count = sum(1 for s in execution.steps if s.workflow_name == "step2")
        assert step2_count == 1

    def test_complete_step_completes_execution(self):
        """Test complete_step marks execution complete when all done."""
        executor = ChainExecutor()
        execution = executor.create_execution("test-wizard")

        step = execution.steps[0]
        executor.complete_step(execution, step, {})

        assert execution.status == "completed"
        assert execution.completed_at is not None


class TestTemplateManagement:
    """Test chain template operations."""

    def test_get_template_returns_steps(self, tmp_path):
        """Test get_template returns template steps."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
templates:
  full-scan:
    steps:
      - security-scan
      - code-analysis
      - report-generation
"""
        )
        executor = ChainExecutor(config_path=config_file)

        template = executor.get_template("full-scan")

        assert template == ["security-scan", "code-analysis", "report-generation"]

    def test_get_nonexistent_template_returns_none(self):
        """Test get_template with nonexistent template."""
        executor = ChainExecutor()

        template = executor.get_template("nonexistent")
        assert template is None

    def test_list_templates_returns_all(self, tmp_path):
        """Test list_templates returns all templates."""
        config_file = tmp_path / "chains.yaml"
        config_file.write_text(
            """
templates:
  template1:
    steps: ["step1", "step2"]
  template2:
    steps: ["step3", "step4"]
"""
        )
        executor = ChainExecutor(config_path=config_file)

        templates = executor.list_templates()

        assert len(templates) == 2
        assert "template1" in templates
        assert "template2" in templates


class TestHelperFunctions:
    """Test helper functions."""

    def test_is_numeric_with_int(self):
        """Test _is_numeric with integer."""
        from attune.routing.chain_executor import _is_numeric

        assert _is_numeric(42) is True

    def test_is_numeric_with_float(self):
        """Test _is_numeric with float."""
        from attune.routing.chain_executor import _is_numeric

        assert _is_numeric(3.14) is True

    def test_is_numeric_with_numeric_string(self):
        """Test _is_numeric with numeric string."""
        from attune.routing.chain_executor import _is_numeric

        assert _is_numeric("123") is True
        assert _is_numeric("45.67") is True

    def test_is_numeric_with_non_numeric(self):
        """Test _is_numeric with non-numeric values."""
        from attune.routing.chain_executor import _is_numeric

        assert _is_numeric("abc") is False
        assert _is_numeric(None) is False
        assert _is_numeric([]) is False

    def test_parse_value_boolean(self):
        """Test _parse_value with boolean strings."""
        from attune.routing.chain_executor import _parse_value

        assert _parse_value("true") is True
        assert _parse_value("false") is False
        assert _parse_value("TRUE") is True
        assert _parse_value("FALSE") is False

    def test_parse_value_null(self):
        """Test _parse_value with null."""
        from attune.routing.chain_executor import _parse_value

        assert _parse_value("null") is None
        assert _parse_value("NULL") is None

    def test_parse_value_numbers(self):
        """Test _parse_value with numbers."""
        from attune.routing.chain_executor import _parse_value

        assert _parse_value("42") == 42
        assert _parse_value("3.14") == 3.14
        assert _parse_value("-10") == -10

    def test_parse_value_strings(self):
        """Test _parse_value with strings."""
        from attune.routing.chain_executor import _parse_value

        assert _parse_value("'hello'") == "hello"
        assert _parse_value('"world"') == "world"
        assert _parse_value("text") == "text"

    def test_get_nested_simple(self):
        """Test _get_nested with simple path."""
        from attune.routing.chain_executor import _get_nested

        data = {"key": "value"}
        assert _get_nested(data, "key") == "value"

    def test_get_nested_deep_path(self):
        """Test _get_nested with nested path."""
        from attune.routing.chain_executor import _get_nested

        data = {"level1": {"level2": {"level3": "deep_value"}}}
        assert _get_nested(data, "level1.level2.level3") == "deep_value"

    def test_get_nested_missing_path(self):
        """Test _get_nested with missing path."""
        from attune.routing.chain_executor import _get_nested

        data = {"key": "value"}
        assert _get_nested(data, "nonexistent") is None
        assert _get_nested(data, "key.nested") is None


class TestChainDataClassIntegration:
    """Integration tests for chain data classes working together."""

    def test_complete_chain_workflow_structure(self):
        """Test complete chain workflow data structure."""
        # Create triggers
        trigger = ChainTrigger(
            condition="issues > 0",
            next_workflow="remediation",
            approval_required=True,
            reason="Issues need fixing",
        )

        # Create config
        config = ChainConfig(workflow_name="audit", auto_chain=True, triggers=[trigger])

        # Create steps
        step1 = ChainStep(
            workflow_name="audit",
            triggered_by="manual",
            approval_required=False,
            result={"issues": 5},
        )

        step2 = ChainStep(
            workflow_name="remediation", triggered_by="auto", approval_required=True, approved=True
        )

        # Create execution
        execution = ChainExecution(
            chain_id="full_chain_001",
            initial_workflow="audit",
            steps=[step1, step2],
            status="running",
        )

        # Verify structure
        assert config.triggers[0].next_workflow == "remediation"
        assert execution.steps[0].result["issues"] == 5
        assert execution.steps[1].approval_required is True
        assert execution.steps[1].approved is True

    def test_chain_execution_lifecycle(self):
        """Test chain execution lifecycle states."""
        start_time = datetime.now()

        # Start execution
        execution = ChainExecution(
            chain_id="lifecycle_001",
            initial_workflow="start",
            started_at=start_time,
            status="running",
        )

        assert execution.status == "running"
        assert execution.completed_at is None

        # Add first step
        step1 = ChainStep(
            workflow_name="start",
            triggered_by="manual",
            approval_required=False,
            started_at=start_time,
        )
        execution.steps.append(step1)

        assert len(execution.steps) == 1
        assert execution.current_step == 0

        # Complete execution
        execution.status = "completed"
        execution.completed_at = datetime.now()

        assert execution.status == "completed"
        assert execution.completed_at is not None
        assert execution.completed_at >= execution.started_at
