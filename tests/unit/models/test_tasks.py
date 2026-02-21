"""Tests for tasks module.

Covers TaskType enum, TaskInfo dataclass, task-tier mappings,
batch eligibility, and helper functions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.models.registry import ModelTier
from attune.models.tasks import (
    BATCH_ELIGIBLE_TASKS,
    CAPABLE_TASKS,
    CHEAP_TASKS,
    PREMIUM_TASKS,
    REALTIME_REQUIRED_TASKS,
    TASK_INFO,
    TASK_TIER_MAP,
    TaskInfo,
    TaskType,
    get_all_tasks,
    get_tasks_for_tier,
    get_tier_for_task,
    is_known_task,
    normalize_task_type,
)


@pytest.mark.unit
class TestTaskType:
    """Tests for TaskType enum."""

    def test_cheap_tier_tasks_exist(self):
        """Test that cheap tier tasks are defined."""
        cheap_tasks = [
            TaskType.SUMMARIZE,
            TaskType.CLASSIFY,
            TaskType.TRIAGE,
            TaskType.MATCH_PATTERN,
            TaskType.EXTRACT_TOPICS,
            TaskType.LINT_CHECK,
            TaskType.FORMAT_CODE,
            TaskType.SIMPLE_QA,
            TaskType.CATEGORIZE,
        ]

        for task in cheap_tasks:
            assert task.value in CHEAP_TASKS

    def test_capable_tier_tasks_exist(self):
        """Test that capable tier tasks are defined."""
        capable_tasks = [
            TaskType.GENERATE_CODE,
            TaskType.FIX_BUG,
            TaskType.REVIEW_SECURITY,
            TaskType.ANALYZE_PERFORMANCE,
            TaskType.WRITE_TESTS,
            TaskType.REFACTOR,
            TaskType.EXPLAIN_CODE,
            TaskType.DOCUMENT_CODE,
            TaskType.ANALYZE_ERROR,
            TaskType.SUGGEST_FIX,
        ]

        for task in capable_tasks:
            assert task.value in CAPABLE_TASKS

    def test_premium_tier_tasks_exist(self):
        """Test that premium tier tasks are defined."""
        premium_tasks = [
            TaskType.COORDINATE,
            TaskType.SYNTHESIZE_RESULTS,
            TaskType.ARCHITECTURAL_DECISION,
            TaskType.NOVEL_PROBLEM,
            TaskType.FINAL_REVIEW,
            TaskType.COMPLEX_REASONING,
            TaskType.MULTI_STEP_PLANNING,
            TaskType.CRITICAL_DECISION,
        ]

        for task in premium_tasks:
            assert task.value in PREMIUM_TASKS

    def test_task_type_values_are_strings(self):
        """Test that all TaskType values are strings."""
        for task in TaskType:
            assert isinstance(task.value, str)
            assert "_" in task.value or task.value.islower()

    def test_task_count(self):
        """Test that we have expected number of tasks."""
        total_tasks = len(CHEAP_TASKS) + len(CAPABLE_TASKS) + len(PREMIUM_TASKS)
        assert total_tasks == len(TaskType)


@pytest.mark.unit
class TestTaskInfo:
    """Tests for TaskInfo dataclass."""

    def test_task_info_creation(self):
        """Test creating a TaskInfo instance."""
        info = TaskInfo(
            task_type=TaskType.SUMMARIZE,
            tier=ModelTier.CHEAP,
            description="Summarize text",
        )

        assert info.task_type == TaskType.SUMMARIZE
        assert info.tier == ModelTier.CHEAP
        assert info.description == "Summarize text"

    def test_task_info_is_frozen(self):
        """Test that TaskInfo is immutable."""
        info = TaskInfo(
            task_type=TaskType.SUMMARIZE,
            tier=ModelTier.CHEAP,
            description="Test",
        )

        with pytest.raises(AttributeError):
            info.description = "New description"

    def test_task_info_registry_has_entries(self):
        """Test that TASK_INFO registry has entries."""
        assert len(TASK_INFO) > 0

    def test_task_info_registry_tiers_correct(self):
        """Test that TASK_INFO has correct tier assignments."""
        for task_type, task_info in TASK_INFO.items():
            expected_tier = get_tier_for_task(task_type)
            assert task_info.tier == expected_tier

    def test_task_info_has_descriptions(self):
        """Test that all TaskInfo entries have descriptions."""
        for _task_type, task_info in TASK_INFO.items():
            assert task_info.description
            assert len(task_info.description) > 5


@pytest.mark.unit
class TestTaskTierMappings:
    """Tests for task-tier mapping sets."""

    def test_cheap_tasks_is_frozenset(self):
        """Test CHEAP_TASKS is immutable."""
        assert isinstance(CHEAP_TASKS, frozenset)

    def test_capable_tasks_is_frozenset(self):
        """Test CAPABLE_TASKS is immutable."""
        assert isinstance(CAPABLE_TASKS, frozenset)

    def test_premium_tasks_is_frozenset(self):
        """Test PREMIUM_TASKS is immutable."""
        assert isinstance(PREMIUM_TASKS, frozenset)

    def test_no_overlap_between_tiers(self):
        """Test that tiers don't have overlapping tasks."""
        assert CHEAP_TASKS.isdisjoint(CAPABLE_TASKS)
        assert CHEAP_TASKS.isdisjoint(PREMIUM_TASKS)
        assert CAPABLE_TASKS.isdisjoint(PREMIUM_TASKS)

    def test_task_tier_map_completeness(self):
        """Test TASK_TIER_MAP contains all tasks."""
        all_tasks = CHEAP_TASKS | CAPABLE_TASKS | PREMIUM_TASKS
        for task in all_tasks:
            assert task in TASK_TIER_MAP


@pytest.mark.unit
class TestNormalizeTaskType:
    """Tests for normalize_task_type function."""

    def test_lowercase_conversion(self):
        """Test that uppercase is converted to lowercase."""
        assert normalize_task_type("SUMMARIZE") == "summarize"
        assert normalize_task_type("FIX_BUG") == "fix_bug"

    def test_hyphen_to_underscore(self):
        """Test that hyphens are converted to underscores."""
        assert normalize_task_type("fix-bug") == "fix_bug"
        assert normalize_task_type("generate-code") == "generate_code"

    def test_space_to_underscore(self):
        """Test that spaces are converted to underscores."""
        assert normalize_task_type("fix bug") == "fix_bug"
        assert normalize_task_type("generate code") == "generate_code"

    def test_mixed_formats(self):
        """Test mixed format normalization."""
        assert normalize_task_type("Fix-Bug") == "fix_bug"
        assert normalize_task_type("GENERATE CODE") == "generate_code"
        assert normalize_task_type("Review-Security") == "review_security"

    def test_already_normalized(self):
        """Test that already normalized strings stay unchanged."""
        assert normalize_task_type("summarize") == "summarize"
        assert normalize_task_type("fix_bug") == "fix_bug"


@pytest.mark.unit
class TestGetTierForTask:
    """Tests for get_tier_for_task function."""

    def test_cheap_task_returns_cheap_tier(self):
        """Test that cheap tasks return CHEAP tier."""
        assert get_tier_for_task("summarize") == ModelTier.CHEAP
        assert get_tier_for_task("classify") == ModelTier.CHEAP
        assert get_tier_for_task("triage") == ModelTier.CHEAP

    def test_capable_task_returns_capable_tier(self):
        """Test that capable tasks return CAPABLE tier."""
        assert get_tier_for_task("generate_code") == ModelTier.CAPABLE
        assert get_tier_for_task("fix_bug") == ModelTier.CAPABLE
        assert get_tier_for_task("write_tests") == ModelTier.CAPABLE

    def test_premium_task_returns_premium_tier(self):
        """Test that premium tasks return PREMIUM tier."""
        assert get_tier_for_task("coordinate") == ModelTier.PREMIUM
        assert get_tier_for_task("architectural_decision") == ModelTier.PREMIUM
        assert get_tier_for_task("complex_reasoning") == ModelTier.PREMIUM

    def test_unknown_task_returns_capable_tier(self):
        """Test that unknown tasks default to CAPABLE tier."""
        assert get_tier_for_task("unknown_task") == ModelTier.CAPABLE
        assert get_tier_for_task("nonexistent") == ModelTier.CAPABLE

    def test_accepts_task_type_enum(self):
        """Test that function accepts TaskType enum."""
        assert get_tier_for_task(TaskType.SUMMARIZE) == ModelTier.CHEAP
        assert get_tier_for_task(TaskType.FIX_BUG) == ModelTier.CAPABLE
        assert get_tier_for_task(TaskType.COORDINATE) == ModelTier.PREMIUM

    def test_case_insensitive(self):
        """Test that lookup is case insensitive."""
        assert get_tier_for_task("SUMMARIZE") == ModelTier.CHEAP
        assert get_tier_for_task("Fix_Bug") == ModelTier.CAPABLE
        assert get_tier_for_task("COORDINATE") == ModelTier.PREMIUM


@pytest.mark.unit
class TestGetTasksForTier:
    """Tests for get_tasks_for_tier function."""

    def test_get_cheap_tier_tasks(self):
        """Test getting tasks for CHEAP tier."""
        tasks = get_tasks_for_tier(ModelTier.CHEAP)

        assert isinstance(tasks, list)
        assert len(tasks) == len(CHEAP_TASKS)
        assert "summarize" in tasks
        assert "classify" in tasks

    def test_get_capable_tier_tasks(self):
        """Test getting tasks for CAPABLE tier."""
        tasks = get_tasks_for_tier(ModelTier.CAPABLE)

        assert isinstance(tasks, list)
        assert len(tasks) == len(CAPABLE_TASKS)
        assert "fix_bug" in tasks
        assert "generate_code" in tasks

    def test_get_premium_tier_tasks(self):
        """Test getting tasks for PREMIUM tier."""
        tasks = get_tasks_for_tier(ModelTier.PREMIUM)

        assert isinstance(tasks, list)
        assert len(tasks) == len(PREMIUM_TASKS)
        assert "coordinate" in tasks
        assert "complex_reasoning" in tasks


@pytest.mark.unit
class TestGetAllTasks:
    """Tests for get_all_tasks function."""

    def test_returns_dict(self):
        """Test that function returns a dict."""
        result = get_all_tasks()
        assert isinstance(result, dict)

    def test_has_all_tiers(self):
        """Test that result has all three tiers."""
        result = get_all_tasks()

        assert "cheap" in result
        assert "capable" in result
        assert "premium" in result

    def test_correct_counts(self):
        """Test that each tier has correct task count."""
        result = get_all_tasks()

        assert len(result["cheap"]) == len(CHEAP_TASKS)
        assert len(result["capable"]) == len(CAPABLE_TASKS)
        assert len(result["premium"]) == len(PREMIUM_TASKS)

    def test_tasks_are_lists(self):
        """Test that tier values are lists."""
        result = get_all_tasks()

        for _tier, tasks in result.items():
            assert isinstance(tasks, list)


@pytest.mark.unit
class TestIsKnownTask:
    """Tests for is_known_task function."""

    def test_known_task_returns_true(self):
        """Test that known tasks return True."""
        assert is_known_task("summarize") is True
        assert is_known_task("fix_bug") is True
        assert is_known_task("coordinate") is True

    def test_unknown_task_returns_false(self):
        """Test that unknown tasks return False."""
        assert is_known_task("unknown_task") is False
        assert is_known_task("nonexistent") is False
        assert is_known_task("random_string") is False

    def test_case_insensitive(self):
        """Test that lookup is case insensitive."""
        assert is_known_task("SUMMARIZE") is True
        assert is_known_task("Fix_Bug") is True

    def test_normalizes_input(self):
        """Test that function normalizes input."""
        assert is_known_task("fix-bug") is True
        assert is_known_task("fix bug") is True


@pytest.mark.unit
class TestBatchEligibility:
    """Tests for batch API task classification."""

    def test_batch_eligible_tasks_is_frozenset(self):
        """Test BATCH_ELIGIBLE_TASKS is immutable."""
        assert isinstance(BATCH_ELIGIBLE_TASKS, frozenset)

    def test_realtime_required_tasks_is_frozenset(self):
        """Test REALTIME_REQUIRED_TASKS is immutable."""
        assert isinstance(REALTIME_REQUIRED_TASKS, frozenset)

    def test_no_overlap_between_batch_and_realtime(self):
        """Test that batch and realtime sets don't overlap."""
        assert BATCH_ELIGIBLE_TASKS.isdisjoint(REALTIME_REQUIRED_TASKS)

    def test_summarize_is_batch_eligible(self):
        """Test that summarize task is batch eligible."""
        assert TaskType.SUMMARIZE.value in BATCH_ELIGIBLE_TASKS

    def test_classify_is_batch_eligible(self):
        """Test that classify task is batch eligible."""
        assert TaskType.CLASSIFY.value in BATCH_ELIGIBLE_TASKS

    def test_document_code_is_batch_eligible(self):
        """Test that document_code task is batch eligible."""
        assert TaskType.DOCUMENT_CODE.value in BATCH_ELIGIBLE_TASKS

    def test_chat_is_realtime_required(self):
        """Test that chat is realtime required."""
        assert "chat" in REALTIME_REQUIRED_TASKS

    def test_critical_fix_is_realtime_required(self):
        """Test that critical_fix is realtime required."""
        assert "critical_fix" in REALTIME_REQUIRED_TASKS


@pytest.mark.unit
class TestTaskTypeCompleteness:
    """Tests for verifying task type completeness and consistency."""

    def test_all_task_types_have_tier_mapping(self):
        """Test that every TaskType has a tier mapping."""
        for task_type in TaskType:
            assert task_type.value in TASK_TIER_MAP

    def test_tier_mapping_values_are_model_tiers(self):
        """Test that all tier mapping values are ModelTier enums."""
        for _task, tier in TASK_TIER_MAP.items():
            assert isinstance(tier, ModelTier)

    @pytest.mark.parametrize(
        "task_type,expected_tier",
        [
            (TaskType.SUMMARIZE, ModelTier.CHEAP),
            (TaskType.CLASSIFY, ModelTier.CHEAP),
            (TaskType.GENERATE_CODE, ModelTier.CAPABLE),
            (TaskType.FIX_BUG, ModelTier.CAPABLE),
            (TaskType.COORDINATE, ModelTier.PREMIUM),
            (TaskType.COMPLEX_REASONING, ModelTier.PREMIUM),
        ],
    )
    def test_specific_task_tier_assignments(self, task_type, expected_tier):
        """Test specific task-tier assignments."""
        assert get_tier_for_task(task_type) == expected_tier
