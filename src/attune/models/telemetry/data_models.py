"""Telemetry data models.

Data classes for tracking LLM calls, workflows, tests, and agent assignments.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class LLMCallRecord:
    """Record of a single LLM API call.

    Captures all relevant metrics for cost tracking, performance analysis,
    and debugging.
    """

    # Identification
    call_id: str
    timestamp: str  # ISO format

    # Context
    workflow_name: str | None = None
    step_name: str | None = None
    user_id: str | None = None
    session_id: str | None = None

    # Task routing
    task_type: str = "unknown"
    provider: str = "anthropic"
    tier: str = "capable"
    model_id: str = ""

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    # Cost (in USD)
    estimated_cost: float = 0.0
    actual_cost: float | None = None

    # Performance
    latency_ms: int = 0

    # Fallback and resilience tracking
    fallback_used: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    original_provider: str | None = None
    original_model: str | None = None
    retry_count: int = 0  # Number of retries before success
    circuit_breaker_state: str | None = None  # "closed", "open", "half-open"

    # Error tracking
    success: bool = True
    error_type: str | None = None
    error_message: str | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMCallRecord":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class WorkflowStageRecord:
    """Record of a single workflow stage execution."""

    stage_name: str
    tier: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    success: bool = True
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None


@dataclass
class WorkflowRunRecord:
    """Record of a complete workflow execution.

    Aggregates stage-level metrics and provides workflow-level analytics.
    """

    # Identification
    run_id: str
    workflow_name: str
    started_at: str  # ISO format
    completed_at: str | None = None

    # Context
    user_id: str | None = None
    session_id: str | None = None

    # Corpus provenance (docs/specs/run-record-corpus/ RC-3) — additive
    # and optional so pre-RC-3 records keep loading via ``from_dict``.
    # ``trigger``: "manual" | "attune-rec"; None means unknown provenance
    # (miners weight it as auto per pipeline-learner RR-3).
    trigger: str | None = None
    # Stable project identifier (repo-root name; worktree runs resolve
    # to the parent repo). None when resolution fails or predates RC-3.
    project: str | None = None

    # Stages
    stages: list[WorkflowStageRecord] = field(default_factory=list)

    # Aggregated metrics
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    baseline_cost: float = 0.0  # If all stages used premium
    savings: float = 0.0
    savings_percent: float = 0.0

    # Performance
    total_duration_ms: int = 0

    # Status
    success: bool = True
    error: str | None = None

    # Provider usage
    providers_used: list[str] = field(default_factory=list)
    tiers_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["stages"] = [asdict(s) for s in self.stages]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowRunRecord":
        """Create from dictionary."""
        stages = [WorkflowStageRecord(**s) for s in data.pop("stages", [])]
        return cls(stages=stages, **data)


@dataclass
class DiagnosisEvidence:
    """One evidence entry in a diagnosis (advanced-debugging-plugin RR-1).

    ``kind`` separates recalled lesson priors from evidence observed in
    the failed run itself (RR-4: priors are never merged with observed
    evidence).
    """

    kind: str  # "prior" | "observed"
    source: str  # lesson ref, file path, "run-record", "log-tail", ...
    content: str = ""


@dataclass
class DiagnosisHypothesis:
    """One ranked root-cause hypothesis."""

    statement: str
    rank: int = 1
    confidence: str = "low"  # values from config_used["confidence_scale"]
    supporting: list[str] = field(default_factory=list)  # evidence sources
    contradicting: list[str] = field(default_factory=list)


@dataclass
class DiagnosisRecord:
    """Record of one diagnosis of a failed workflow run.

    The core artifact of docs/specs/advanced-debugging-plugin/ (RR-1):
    symptom -> evidence chain -> hypotheses -> synthesis -> proposed
    fix -> verification, persisted beside the run corpus. Later phases
    fill ``panel`` (RR-5) and ``proposed_fix`` (RR-6) — both are plain
    dicts so Phase A ships no speculative schema for them
    (``schema_version`` exists for hardening later).
    """

    # Identification
    diagnosis_id: str
    source_run_id: str
    workflow_name: str
    created_at: str  # ISO format
    schema_version: int = 1

    # Lifecycle: open | fix-proposed | verified | rejected | graduated
    status: str = "open"

    # Symptom + priors (RR-4)
    symptom: str = ""
    prior_lessons: list[str] = field(default_factory=list)
    priors_degraded: str | None = None  # reason recall was unavailable

    # Evidence and reasoning
    evidence: list[DiagnosisEvidence] = field(default_factory=list)
    hypotheses: list[DiagnosisHypothesis] = field(default_factory=list)
    synthesis: str | None = None
    dissent: list[str] = field(default_factory=list)

    # Panel receipts (RR-5, Phase B) and fix proposal (RR-6, Phase D)
    panel: dict[str, Any] = field(default_factory=dict)
    proposed_fix: dict[str, Any] = field(default_factory=dict)

    # Policy is data (dissent register): the confidence scale and fix
    # threshold used for THIS diagnosis, never hard-coded elsewhere.
    config_used: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagnosisRecord":
        """Create from dictionary.

        Tolerant in both directions: missing fields fall back to
        defaults (pre-v1 records), unknown keys are dropped (records
        written by a NEWER schema still load).
        """
        evidence = [DiagnosisEvidence(**e) for e in data.pop("evidence", []) if isinstance(e, dict)]
        hypotheses = [
            DiagnosisHypothesis(**h) for h in data.pop("hypotheses", []) if isinstance(h, dict)
        ]
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(evidence=evidence, hypotheses=hypotheses, **kwargs)


@dataclass
class TaskRoutingRecord:
    """Record of task routing decision for Tier 1 automation.

    Tracks which agent/workflow handles each task, routing strategy,
    and execution outcome for automation monitoring.
    """

    # Identification (required)
    routing_id: str
    timestamp: str  # ISO format

    # Task context (required)
    task_description: str
    task_type: str  # "code_review", "test_gen", "bug_fix", "refactor", etc.
    task_complexity: str  # "simple", "moderate", "complex"

    # Routing decision (required)
    assigned_agent: str  # "test_gen_workflow", "code_review_workflow", etc.
    assigned_tier: str  # "cheap", "capable", "premium"
    routing_strategy: str  # "rule_based", "ml_predicted", "manual_override"

    # Optional fields with defaults
    task_dependencies: list[str] = field(default_factory=list)  # Task IDs this depends on
    confidence_score: float = 1.0  # 0.0-1.0 for ML predictions

    # Execution tracking
    status: str = "pending"  # "pending", "running", "completed", "failed"
    started_at: str | None = None
    completed_at: str | None = None

    # Outcome
    success: bool = False
    quality_score: float | None = None  # 0.0-1.0 if applicable
    retry_count: int = 0
    error_type: str | None = None
    error_message: str | None = None

    # Cost tracking
    estimated_cost: float = 0.0
    actual_cost: float | None = None

    # Metadata
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRoutingRecord":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TestExecutionRecord:
    """Record of test execution for Tier 1 QA automation.

    Tracks test execution results, coverage metrics, and failure details
    for quality assurance monitoring.
    """

    # Identification (required)
    execution_id: str
    timestamp: str  # ISO format

    # Test context (required)
    test_suite: str  # "unit", "integration", "e2e", "all"

    # Optional fields with defaults
    test_files: list[str] = field(default_factory=list)  # Specific test files executed
    triggered_by: str = "manual"  # "workflow", "manual", "ci", "pre_commit"

    # Execution details
    command: str = ""
    working_directory: str = ""
    duration_seconds: float = 0.0

    # Results
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0

    # Coverage (if available)
    coverage_percentage: float | None = None
    coverage_report_path: str | None = None

    # Failures
    failed_tests: list[dict[str, Any]] = field(
        default_factory=list,
    )  # [{name, file, error, traceback}]

    # Status
    success: bool = False  # True if all tests passed
    exit_code: int = 0

    # Metadata
    workflow_id: str | None = None  # Link to workflow that triggered this
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestExecutionRecord":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CoverageRecord:
    """Record of test coverage metrics for Tier 1 QA monitoring.

    Tracks coverage percentage, trends, and critical gaps for
    continuous quality improvement.
    """

    # Identification (required)
    record_id: str
    timestamp: str  # ISO format

    # Coverage metrics (required)
    overall_percentage: float
    lines_total: int
    lines_covered: int

    # Optional fields with defaults
    branches_total: int = 0
    branches_covered: int = 0

    # File-level breakdown
    files_total: int = 0
    files_well_covered: int = 0  # >= 80%
    files_critical: int = 0  # < 50%
    untested_files: list[str] = field(default_factory=list)

    # Critical gaps
    critical_gaps: list[dict[str, Any]] = field(
        default_factory=list,
    )  # [{file, coverage, priority}]

    # Trend data
    previous_percentage: float | None = None
    trend: str | None = None  # "improving", "declining", "stable"

    # Source
    coverage_format: str = "xml"  # "xml", "json", "lcov"
    coverage_file: str = ""

    # Metadata
    workflow_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoverageRecord":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AgentAssignmentRecord:
    """Record of agent assignment for simple tasks (Tier 1).

    Tracks task assignments to agents/workflows with clear specs
    and no complex dependencies for automation monitoring.
    """

    # Identification (required)
    assignment_id: str
    timestamp: str  # ISO format

    # Task details (required)
    task_id: str
    task_title: str
    task_description: str

    # Assignment (required)
    assigned_agent: str  # Agent/workflow name

    # Optional fields with defaults
    task_spec_clarity: float = 0.0  # 0.0-1.0, higher = clearer spec
    assignment_reason: str = ""  # Why this agent was chosen
    estimated_duration_hours: float = 0.0

    # Criteria checks
    has_clear_spec: bool = False
    has_dependencies: bool = False
    requires_human_review: bool = False
    automated_eligible: bool = False  # True for Tier 1

    # Execution tracking
    status: str = "assigned"  # "assigned", "in_progress", "completed", "blocked"
    started_at: str | None = None
    completed_at: str | None = None
    actual_duration_hours: float | None = None

    # Outcome
    success: bool = False
    quality_check_passed: bool = False
    human_review_required: bool = False

    # Metadata
    workflow_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentAssignmentRecord":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class FileTestRecord:
    """Record of test execution for a specific source file.

    Tracks when tests for an individual file were last run, results,
    and coverage - enabling per-file test status tracking.

    This complements TestExecutionRecord (suite-level) by providing
    granular file-level test tracking for better test maintenance.
    """

    # Identification (required)
    file_path: str  # Source file path (relative to project root)
    timestamp: str  # ISO format - when tests were run

    # Test results (required)
    last_test_result: str  # "passed", "failed", "error", "skipped", "no_tests"
    test_count: int  # Number of tests for this file

    # Detailed results with defaults
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0

    # Timing
    duration_seconds: float = 0.0

    # Coverage for this file (if available)
    coverage_percent: float | None = None
    lines_total: int = 0
    lines_covered: int = 0

    # Test file info
    test_file_path: str | None = None  # Associated test file

    # Failure details (if any)
    failed_tests: list[dict[str, Any]] = field(default_factory=list)

    # Staleness tracking
    source_modified_at: str | None = None  # When source file was last modified
    tests_modified_at: str | None = None  # When test file was last modified
    is_stale: bool = False  # Tests haven't been run since source changed

    # Link to execution
    execution_id: str | None = None  # Link to TestExecutionRecord
    workflow_id: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileTestRecord":
        """Create from dictionary."""
        return cls(**data)

    @property
    def success(self) -> bool:
        """Check if all tests passed."""
        return self.last_test_result == "passed" and self.failed == 0 and self.errors == 0
