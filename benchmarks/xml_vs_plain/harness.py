"""Benchmark harness for XML vs plain text comparison.

Runs benchmark samples through PromptService in both XML and plain text
modes, calls LLM (or mock), and collects structured results.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Protocol

from benchmarks.xml_vs_plain.config import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkSample,
    estimate_cost,
)
from benchmarks.xml_vs_plain.samples import get_samples

logger = logging.getLogger(__name__)


class LLMBackend(Protocol):
    """Protocol for LLM backends (real or mock)."""

    async def call(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Call the LLM and return response dict.

        Returns:
            Dict with keys: text, prompt_tokens, completion_tokens.
        """
        ...


class AnthropicBackend:
    """Real Anthropic API backend."""

    def __init__(self) -> None:
        try:
            import anthropic

            self._client = anthropic.AsyncAnthropic()
        except ImportError as e:
            raise ImportError("anthropic package required: pip install anthropic") from e

    async def call(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Call Anthropic API."""
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        return {
            "text": text,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
        }


class BenchmarkHarness:
    """Core A/B benchmark runner.

    Uses PromptService to render prompts in XML and plain text modes,
    sends to LLM, parses responses, and collects metrics.

    Args:
        config: Benchmark configuration.
        backend: LLM backend (real or mock).
    """

    def __init__(self, config: BenchmarkConfig, backend: LLMBackend) -> None:
        self._config = config
        self._backend = backend
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    async def run_single(
        self,
        sample: BenchmarkSample,
        xml_enabled: bool,
        model: str,
        run_number: int,
    ) -> BenchmarkResult:
        """Run one sample with one prompt format on one model.

        Args:
            sample: The benchmark sample to run.
            xml_enabled: Whether to use XML prompts.
            model: Model ID to use.
            run_number: Run index for consistency tracking.

        Returns:
            BenchmarkResult with all metrics populated.
        """
        from attune.workflows.services.prompt_service import PromptService

        # Create prompt service with appropriate config
        xml_config = {
            "enabled": xml_enabled,
            "template_name": sample.workflow,
            "enforce_response_xml": xml_enabled,
            "schema_version": "1.0",
        }
        prompt_svc = PromptService(sample.workflow, xml_config=xml_config)

        # Build prompt context based on workflow type
        role, goal, instructions, constraints = _get_workflow_params(sample.workflow)

        rendered = prompt_svc.render_xml(
            role=role,
            goal=goal,
            instructions=instructions,
            constraints=constraints,
            input_type=sample.input_type,
            input_payload=sample.input_code,
        )

        # Call LLM with rate limiting
        async with self._semaphore:
            start_ms = time.monotonic() * 1000
            try:
                response = await self._backend.call(
                    prompt=rendered,
                    model=model,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                )
            except Exception as e:
                logger.error("LLM call failed for %s: %s", sample.id, e)
                return BenchmarkResult(
                    sample_id=sample.id,
                    workflow=sample.workflow,
                    model=model,
                    xml_enabled=xml_enabled,
                    run_number=run_number,
                    raw_response=f"ERROR: {e}",
                )
            latency_ms = time.monotonic() * 1000 - start_ms

        raw_text = response.get("text", "")
        prompt_tokens = response.get("prompt_tokens", 0)
        completion_tokens = response.get("completion_tokens", 0)

        # Parse response
        parse_success = False
        findings_count = 0
        findings_by_severity: dict[str, int] = {}

        try:
            from attune.prompts.parser import XmlResponseParser

            parser = XmlResponseParser()
            parsed = parser.parse(raw_text)
            parse_success = parsed.success
            findings_count = len(parsed.findings)
            for finding in parsed.findings:
                sev = finding.severity or "unknown"
                findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1
        except Exception as e:
            logger.warning("Response parsing failed for %s: %s", sample.id, e)

        return BenchmarkResult(
            sample_id=sample.id,
            workflow=sample.workflow,
            model=model,
            xml_enabled=xml_enabled,
            run_number=run_number,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=estimate_cost(model, prompt_tokens, completion_tokens),
            latency_ms=latency_ms,
            xml_parse_success=parse_success,
            findings_count=findings_count,
            findings_by_severity=findings_by_severity,
            rendered_prompt=rendered,
            raw_response=raw_text,
        )

    async def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmark combinations.

        Iterates: workflows x samples x {xml, plain} x models x runs.

        Returns:
            List of all BenchmarkResult objects.
        """
        results: list[BenchmarkResult] = []
        total_calls = 0

        for workflow in self._config.workflows:
            samples = get_samples(workflow, self._config.samples_per_workflow)
            if not samples:
                logger.warning("No samples for workflow: %s", workflow)
                continue

            for sample in samples:
                for model in self._config.models:
                    for xml_enabled in [True, False]:
                        for run in range(self._config.runs_per_sample):
                            total_calls += 1

        logger.info("Starting benchmark: %d total LLM calls", total_calls)
        completed = 0

        for workflow in self._config.workflows:
            samples = get_samples(workflow, self._config.samples_per_workflow)

            for sample in samples:
                for model in self._config.models:
                    for xml_enabled in [True, False]:
                        for run in range(self._config.runs_per_sample):
                            result = await self.run_single(
                                sample=sample,
                                xml_enabled=xml_enabled,
                                model=model,
                                run_number=run,
                            )
                            results.append(result)
                            completed += 1
                            if completed % 10 == 0:
                                logger.info(
                                    "Progress: %d/%d calls (%.0f%%)",
                                    completed,
                                    total_calls,
                                    100 * completed / total_calls,
                                )

        logger.info("Benchmark complete: %d results collected", len(results))
        return results


def _get_workflow_params(
    workflow: str,
) -> tuple[str, str, list[str], list[str]]:
    """Get prompt parameters for a workflow type.

    Args:
        workflow: Workflow name.

    Returns:
        Tuple of (role, goal, instructions, constraints).
    """
    params: dict[str, tuple[str, str, list[str], list[str]]] = {
        "security-audit": (
            "application security engineer",
            "Identify security vulnerabilities and provide remediation guidance",
            [
                "Analyze the code for security vulnerabilities",
                "Focus on OWASP Top 10 categories",
                "Provide severity ratings (critical, high, medium, low)",
                "Include specific file and line references where applicable",
                "Suggest concrete remediation steps for each finding",
            ],
            [
                "Be specific and actionable",
                "Prioritize findings by severity",
                "Include code examples for fixes when helpful",
            ],
        ),
        "code-review": (
            "senior staff engineer performing code review",
            "Review code quality, identify issues, and suggest improvements",
            [
                "Identify bugs, security risks, and performance issues",
                "Evaluate code structure and maintainability",
                "Check for missing error handling",
                "Identify tests that should be added or updated",
                "Suggest improvements while respecting existing patterns",
            ],
            [
                "Be direct and technical",
                "Reference specific files and lines",
                "Keep feedback actionable",
                "Maximum 500 words",
            ],
        ),
        "perf-audit": (
            "senior performance engineer",
            "Identify performance bottlenecks and optimization opportunities",
            [
                "Analyze code for performance bottlenecks",
                "Identify algorithmic complexity issues (O(n^2), etc.)",
                "Check for memory inefficiencies and resource leaks",
                "Look for blocking operations in async code",
                "Suggest concrete optimizations with expected impact",
            ],
            [
                "Be specific about time and space complexity",
                "Prioritize by expected impact",
                "Include before/after code examples",
                "Rate each finding: critical, high, medium, low",
            ],
        ),
    }
    return params.get(workflow, params["code-review"])
