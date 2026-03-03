"""Test Audit Workflow.

Autonomous test coverage audit and generation workflow.
Audits current test coverage, plans where to add tests,
executes test generation, and verifies results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from attune.models import ModelTier

from ..base import BaseWorkflow
from .coverage_parser import (
    ModuleCoverage,
    group_into_batches,
    parse_coverage_json,
    prioritize_modules,
)
from .prompts import BATCH_TASK_TEMPLATE, PLAN_SYSTEM_PROMPT


class TestAuditWorkflow(BaseWorkflow):
    """Autonomous test coverage audit and generation workflow.

    Runs a four-stage pipeline:

    1. **audit** — Run ``pytest --cov`` and parse the coverage
       report to produce a prioritized module list.
    2. **plan** — Group modules into batches by subsystem and
       generate XML-enhanced task prompts.
    3. **execute** — For each batch, produce test generation
       specs. Skipped in ``"quick"`` mode.
    4. **verify** — Run the full test suite and compare
       coverage before and after.

    Usage::

        workflow = TestAuditWorkflow()
        result = await workflow.execute(src_path="src/attune")

    """

    name = "test-audit"
    description = "Autonomous test coverage audit and generation"
    stages = ["audit", "plan", "execute", "verify"]
    tier_map = {
        "audit": ModelTier.CHEAP,
        "plan": ModelTier.CAPABLE,
        "execute": ModelTier.CAPABLE,
        "verify": ModelTier.CHEAP,
    }

    def __init__(
        self,
        target_coverage: float = 90.0,
        min_module_coverage: float = 50.0,
        max_batches: int = 5,
        batch_parallelism: int = 3,
        mode: str = "deep",
        **kwargs: Any,
    ):
        """Initialize the TestAuditWorkflow.

        Args:
            target_coverage: Overall coverage target percentage.
            min_module_coverage: Modules below this coverage
                percentage are included in the plan.
            max_batches: Maximum number of test-gen batches.
            batch_parallelism: Number of batches to process
                concurrently in execute stage.
            mode: ``"deep"`` (all 4 stages) or ``"quick"``
                (audit + verify only, skips execute).
            **kwargs: Additional arguments forwarded to
                BaseWorkflow.

        """
        super().__init__(**kwargs)
        self.target_coverage = target_coverage
        self.min_module_coverage = min_module_coverage
        self.max_batches = max_batches
        self.batch_parallelism = batch_parallelism
        self.mode = mode
        # Stored by audit stage for verify stage comparison
        self._coverage_before: float | None = None

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Route to the stage implementation.

        Args:
            stage_name: One of ``"audit"``, ``"plan"``,
                ``"execute"``, ``"verify"``.
            tier: Model tier assigned to this stage.
            input_data: Output from the previous stage.

        Returns:
            Tuple of (stage_output, input_tokens, output_tokens).

        Raises:
            ValueError: If stage_name is not recognized.

        """
        if stage_name == "audit":
            return await self._audit(input_data, tier)
        if stage_name == "plan":
            return await self._plan(input_data, tier)
        if stage_name == "execute":
            return await self._execute_stage(input_data, tier)
        if stage_name == "verify":
            return await self._verify(input_data, tier)
        raise ValueError(f"Unknown stage: {stage_name}")

    # ------------------------------------------------------------------
    # Stage: audit
    # ------------------------------------------------------------------

    async def _audit(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run pytest --cov and parse coverage.json.

        Produces a prioritized list of modules sorted by
        ``(1 - coverage%) * total_stmts`` descending.

        Args:
            input_data: Workflow input dict. Recognized keys:
                - ``src_path`` (str): Path passed to
                  ``--cov``. Default: ``"src/attune"``.
                - ``cov_report_path`` (str): Where to write
                  ``coverage.json``. Default: temp file.
            tier: Model tier (unused in this stage).

        Returns:
            Tuple of (output_dict, input_tokens, output_tokens).

        """
        src_path = input_data.get("src_path", "src/attune")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, prefix="attune_cov_") as tmp:
            cov_report_path = tmp.name

        try:
            modules = self._run_coverage(src_path, cov_report_path)
        except (FileNotFoundError, ValueError, subprocess.SubprocessError) as exc:
            self.logger.warning("Coverage collection failed: %s", exc)
            modules = []

        prioritized = prioritize_modules(modules, self.min_module_coverage)

        # Store overall coverage for verify stage
        if modules:
            total_stmts = sum(m.stmts for m in modules)
            total_covered = sum(m.covered for m in modules)
            if total_stmts > 0:
                self._coverage_before = (total_covered / total_stmts) * 100.0

        output = {
            "modules": [_module_to_dict(m) for m in prioritized],
            "total_modules": len(modules),
            "modules_below_threshold": len(prioritized),
            "coverage_before": self._coverage_before,
            **input_data,
        }

        in_tok = len(str(input_data)) // 4
        out_tok = len(str(output)) // 4
        return output, in_tok, out_tok

    def _run_coverage(self, src_path: str, cov_report_path: str) -> list[ModuleCoverage]:
        """Execute pytest --cov and return parsed modules.

        Args:
            src_path: Path to pass to ``--cov``.
            cov_report_path: File path for coverage.json output.

        Returns:
            List of ModuleCoverage objects.

        Raises:
            subprocess.SubprocessError: If pytest fails to run.
            FileNotFoundError: If coverage.json is not produced.
            ValueError: If coverage.json cannot be parsed.

        """
        cmd = [
            "python",
            "-m",
            "pytest",
            f"--cov={src_path}",
            f"--cov-report=json:{cov_report_path}",
            "-m",
            "not network",
            "-q",
            "--tb=no",
        ]

        self.logger.info("Running coverage: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode not in (0, 1):
            # Exit code 1 means tests ran but some failed — coverage
            # JSON is still produced. Anything else is a runner error.
            self.logger.warning(
                "pytest exited with code %d: %s",
                result.returncode,
                result.stderr[:500],
            )

        return parse_coverage_json(cov_report_path)

    # ------------------------------------------------------------------
    # Stage: plan
    # ------------------------------------------------------------------

    async def _plan(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Group modules into batches and build task specs.

        Args:
            input_data: Output from the audit stage.
            tier: Model tier (unused; planning is deterministic).

        Returns:
            Tuple of (output_dict, input_tokens, output_tokens).

        """
        raw_modules = input_data.get("modules", [])
        modules = [_dict_to_module(m) for m in raw_modules]

        batches = group_into_batches(modules, self.max_batches)

        batch_specs = []
        for batch in batches:
            spec = _build_batch_spec(
                batch,
                target_pct=self.target_coverage,
            )
            batch_specs.append(spec)

        output = {
            "batches": batch_specs,
            "total_batches": len(batch_specs),
            **input_data,
        }

        in_tok = len(PLAN_SYSTEM_PROMPT) // 4 + len(str(raw_modules)) // 4
        out_tok = len(str(batch_specs)) // 4
        return output, in_tok, out_tok

    # ------------------------------------------------------------------
    # Stage: execute
    # ------------------------------------------------------------------

    async def _execute_stage(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Produce test generation specs for each batch.

        In ``"quick"`` mode this stage is a no-op.

        Args:
            input_data: Output from the plan stage.
            tier: Model tier for this stage.

        Returns:
            Tuple of (output_dict, input_tokens, output_tokens).

        """
        if self.mode == "quick":
            self.logger.info("Quick mode: skipping execute stage")
            output = {
                "results": [],
                "mode": "quick",
                **input_data,
            }
            return output, 0, 0

        batches = input_data.get("batches", [])
        results = []

        for batch in batches:
            result = _build_batch_result(batch)
            results.append(result)
            self.logger.info(
                "Batch %s planned: %d modules",
                batch.get("batch_id"),
                len(batch.get("modules", [])),
            )

        output = {
            "results": results,
            "batches_processed": len(results),
            **input_data,
        }

        in_tok = len(str(batches)) // 4
        out_tok = len(str(results)) // 4
        return output, in_tok, out_tok

    # ------------------------------------------------------------------
    # Stage: verify
    # ------------------------------------------------------------------

    async def _verify(self, input_data: dict, tier: ModelTier) -> tuple[dict, int, int]:
        """Run pytest and compare coverage before and after.

        Args:
            input_data: Output from the execute stage.
            tier: Model tier (unused in this stage).

        Returns:
            Tuple of (output_dict, input_tokens, output_tokens).

        """
        src_path = input_data.get("src_path", "src/attune")

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="attune_cov_after_"
        ) as tmp:
            cov_report_path = tmp.name

        coverage_after: float | None = None
        tests_total: int = 0
        regressions: int = 0

        try:
            cmd = [
                "python",
                "-m",
                "pytest",
                f"--cov={src_path}",
                f"--cov-report=json:{cov_report_path}",
                "-q",
                "--tb=no",
            ]
            self.logger.info("Running verify: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            regressions = 1 if result.returncode not in (0, 1) else 0

            # Parse test counts from pytest output
            for line in result.stdout.splitlines():
                if "passed" in line or "failed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        stripped = part.rstrip(",")
                        if stripped in ("passed", "failed", "error") and i > 0:
                            try:
                                tests_total += int(parts[i - 1])
                            except ValueError:
                                pass

            modules = parse_coverage_json(cov_report_path)
            if modules:
                total_stmts = sum(m.stmts for m in modules)
                total_covered = sum(m.covered for m in modules)
                if total_stmts > 0:
                    coverage_after = (total_covered / total_stmts) * 100.0

        except (FileNotFoundError, ValueError, subprocess.SubprocessError) as exc:
            self.logger.warning("Verify coverage run failed: %s", exc)

        coverage_before = input_data.get("coverage_before", self._coverage_before)
        delta: float | None = None
        if coverage_before is not None and coverage_after is not None:
            delta = coverage_after - coverage_before

        output = {
            "before": coverage_before,
            "after": coverage_after,
            "delta": delta,
            "tests_total": tests_total,
            "regressions": regressions,
            **input_data,
        }

        in_tok = len(str(input_data)) // 4
        out_tok = len(str(output)) // 4
        return output, in_tok, out_tok


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _module_to_dict(m: ModuleCoverage) -> dict:
    """Serialize a ModuleCoverage to a plain dict."""
    return {
        "path": m.path,
        "stmts": m.stmts,
        "covered": m.covered,
        "missing_lines": m.missing_lines,
        "pct": m.pct,
        "priority": m.priority,
    }


def _dict_to_module(d: dict) -> ModuleCoverage:
    """Deserialize a plain dict to a ModuleCoverage."""
    return ModuleCoverage(
        path=d.get("path", ""),
        stmts=d.get("stmts", 0),
        covered=d.get("covered", 0),
        missing_lines=d.get("missing_lines", []),
        pct=d.get("pct", 0.0),
        priority=d.get("priority", 0.0),
    )


def _build_batch_spec(batch: dict, target_pct: float) -> dict:
    """Build a task spec dict for a batch.

    Args:
        batch: Batch dict from group_into_batches().
        target_pct: Coverage percentage to target.

    Returns:
        Dict with batch_id, subsystem, modules, and task_xml.

    """
    batch_id = batch["batch_id"]
    subsystem = batch["subsystem"]
    modules: list[ModuleCoverage] = batch["modules"]

    module_paths = [m.path for m in modules]
    missing_summary = _summarize_missing(modules)

    # Build a simple test path from the subsystem
    safe_subsystem = subsystem.replace("/", "_").replace(".", "_")
    test_path = f"tests/unit/{safe_subsystem}/test_generated.py"

    task_xml = BATCH_TASK_TEMPLATE.format(
        batch_id=batch_id,
        subsystem=subsystem,
        target_pct=int(target_pct),
        missing_lines_summary=missing_summary,
        source_path=subsystem,
        key_signatures="(see source files)",
        test_path=test_path,
        test_class_specs="(to be generated)",
        module=subsystem,
    )

    return {
        "batch_id": batch_id,
        "subsystem": subsystem,
        "modules": [m.path for m in modules],
        "module_paths": module_paths,
        "task_xml": task_xml,
    }


def _build_batch_result(batch: dict) -> dict:
    """Build an execute-stage result for a batch.

    This produces the spec for what tests should be written.
    Actual test writing is delegated to the agent/user.

    Args:
        batch: Batch spec dict from the plan stage.

    Returns:
        Dict describing the planned test additions.

    """
    return {
        "batch_id": batch.get("batch_id"),
        "subsystem": batch.get("subsystem"),
        "tests_added": 0,
        "files_created": [],
        "task_xml": batch.get("task_xml", ""),
        "status": "planned",
    }


def _summarize_missing(modules: list[ModuleCoverage]) -> str:
    """Produce a short summary of missing line counts.

    Args:
        modules: List of ModuleCoverage objects.

    Returns:
        Compact string like ``"module_a: 12 lines, module_b: 5 lines"``.

    """
    parts = []
    for m in modules[:5]:
        name = Path(m.path).name
        count = len(m.missing_lines)
        parts.append(f"{name}: {count} lines")
    summary = ", ".join(parts)
    if len(modules) > 5:
        summary += f" (+{len(modules) - 5} more)"
    return summary


def _parse_coverage_total(data: dict) -> float | None:
    """Extract overall coverage percentage from coverage.json data.

    Args:
        data: Parsed coverage.json dict.

    Returns:
        Coverage percentage as float, or None if unavailable.

    """
    totals = data.get("totals", {})
    pct = totals.get("percent_covered")
    if pct is not None:
        try:
            return float(pct)
        except (TypeError, ValueError):
            pass
    return None


def _load_json_safe(path: str) -> dict:
    """Load JSON from path, returning empty dict on failure.

    Args:
        path: File path to read.

    Returns:
        Parsed JSON dict, or empty dict on any error.

    """
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
