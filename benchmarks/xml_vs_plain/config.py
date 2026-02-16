"""Benchmark configuration and data classes.

Defines the config, sample, and result structures for the XML vs plain text
benchmark suite.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExpectedFinding:
    """A known finding in a benchmark sample for quality evaluation.

    Attributes:
        category: Finding category (e.g., "eval_usage", "sql_injection").
        severity: Expected severity level.
        location_hint: Approximate location (e.g., "line 5", "function run_cmd").
        required: Whether this finding must be detected for completeness credit.
    """

    category: str
    severity: str  # "critical", "high", "medium", "low"
    location_hint: str
    required: bool = True


@dataclass
class BenchmarkSample:
    """A single benchmark test case.

    Attributes:
        id: Unique identifier (e.g., "security-001").
        workflow: Target workflow name.
        name: Human-readable description.
        input_code: The code to analyze.
        input_type: Input type ("code" or "diff").
        expected_findings: Ground truth for quality evaluation.
        difficulty: Sample difficulty ("easy", "medium", "hard").
    """

    id: str
    workflow: str
    name: str
    input_code: str
    input_type: str = "code"
    expected_findings: list[ExpectedFinding] = field(default_factory=list)
    difficulty: str = "medium"  # "easy", "medium", "hard"


@dataclass
class QualityScore:
    """Automated quality metrics for a single benchmark result.

    Each metric is 0.0-1.0 where higher is better.

    Attributes:
        parsing_score: Did the response parse into structured format?
        completeness_score: Fraction of expected findings detected.
        precision_score: Fraction of reported findings that are real.
        actionability_score: Fraction of findings with location AND fix.
        consistency_score: Cross-run similarity (set after multiple runs).
        overall: Weighted average of all metrics.
    """

    parsing_score: float = 0.0
    completeness_score: float = 0.0
    precision_score: float = 0.0
    actionability_score: float = 0.0
    consistency_score: float = 0.0

    @property
    def overall(self) -> float:
        """Weighted average: parsing 20%, completeness 25%, precision 25%, actionability 20%, consistency 10%."""
        return (
            self.parsing_score * 0.20
            + self.completeness_score * 0.25
            + self.precision_score * 0.25
            + self.actionability_score * 0.20
            + self.consistency_score * 0.10
        )


@dataclass
class BenchmarkResult:
    """Result of a single benchmark LLM call.

    Attributes:
        sample_id: ID of the benchmark sample.
        workflow: Workflow name.
        model: Model ID used.
        xml_enabled: Whether XML prompts were used.
        run_number: Run index (for consistency measurement).
        prompt_tokens: Input token count from API response.
        completion_tokens: Output token count from API response.
        estimated_cost_usd: Calculated cost based on model pricing.
        latency_ms: Wall-clock time for the API call.
        xml_parse_success: Whether XmlResponseParser parsed successfully.
        findings_count: Number of findings extracted.
        findings_by_severity: Findings grouped by severity.
        rendered_prompt: The prompt sent to the LLM.
        raw_response: The raw response text.
        quality_score: Automated quality evaluation (set after evaluation).
    """

    sample_id: str
    workflow: str
    model: str
    xml_enabled: bool
    run_number: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    xml_parse_success: bool = False
    findings_count: int = 0
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    rendered_prompt: str = ""
    raw_response: str = ""
    quality_score: QualityScore | None = None


@dataclass
class BenchmarkConfig:
    """Configuration for the benchmark suite.

    Attributes:
        workflows: Workflow names to benchmark.
        models: Model IDs to test.
        samples_per_workflow: Number of samples per workflow.
        runs_per_sample: Repeat count for consistency measurement.
        use_mock: Use mock LLM backend (no API calls).
        output_dir: Directory for results and reports.
        temperature: LLM temperature (0.0 for reproducibility).
        max_tokens: Max output tokens per call.
        max_concurrent: Max concurrent API calls.
    """

    workflows: list[str] = field(
        default_factory=lambda: ["security-audit", "code-review", "perf-audit"]
    )
    models: list[str] = field(default_factory=lambda: ["claude-sonnet-4-5-20250929"])
    samples_per_workflow: int = 10
    runs_per_sample: int = 3
    use_mock: bool = False
    output_dir: str = "benchmarks/xml_vs_plain/results"
    temperature: float = 0.0
    max_tokens: int = 4096
    max_concurrent: int = 2

    @classmethod
    def quick(cls) -> BenchmarkConfig:
        """Quick benchmark: 5 samples, 1 run, Sonnet only (~30 calls, ~$0.32)."""
        return cls(
            samples_per_workflow=5,
            runs_per_sample=1,
            models=["claude-sonnet-4-5-20250929"],
        )

    @classmethod
    def full(cls) -> BenchmarkConfig:
        """Full benchmark: 10 samples, 3 runs, Sonnet + Opus (~360 calls, ~$11)."""
        return cls(
            samples_per_workflow=10,
            runs_per_sample=3,
            models=["claude-sonnet-4-5-20250929", "claude-opus-4-6"],
        )

    @classmethod
    def mock(cls) -> BenchmarkConfig:
        """Mock benchmark: uses mock LLM, no API calls."""
        return cls(
            use_mock=True,
            samples_per_workflow=5,
            runs_per_sample=1,
        )


# Model pricing per million tokens (input, output)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5-20250929": (3.0, 15.0),
    "claude-opus-4-6": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for an LLM call.

    Args:
        model: Model ID.
        prompt_tokens: Input token count.
        completion_tokens: Output token count.

    Returns:
        Estimated cost in USD.
    """
    input_price, output_price = MODEL_PRICING.get(model, (3.0, 15.0))
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000
