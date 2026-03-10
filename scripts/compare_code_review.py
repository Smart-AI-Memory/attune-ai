#!/usr/bin/env python3
"""Compare old vs new code review workflows side-by-side.

Runs CodeReviewWorkflow (mixin-based) and AgentCodeReviewWorkflow
(Agent SDK-based) against the same path and prints a markdown
comparison report.

Usage:
    python scripts/compare_code_review.py --path src/attune/

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import anyio

from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.code_review_agent_sdk import AgentCodeReviewWorkflow
from attune.workflows.data_classes import WorkflowResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPORT_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "plans" / "code-review-comparison.md"
)


@dataclass
class RunResult:
    """Capture of a single workflow run."""

    name: str
    result: WorkflowResult | None
    error: str | None
    elapsed_ms: int


def _count_findings(result: WorkflowResult) -> dict[str, int]:
    """Extract finding counts by category from final_output.

    Args:
        result: A completed WorkflowResult.

    Returns:
        Dict mapping category name to finding count.
    """
    output = result.final_output
    if output is None:
        return {}

    counts: dict[str, int] = {}

    # Handle dict-style output with a findings list
    if isinstance(output, dict):
        findings = output.get("findings", [])
        if isinstance(findings, list):
            for f in findings:
                cat = f.get("category", "uncategorized") if isinstance(f, dict) else "uncategorized"
                counts[cat] = counts.get(cat, 0) + 1
        # Also check for section-level counts
        for key in ("security", "quality", "performance", "architecture"):
            section = output.get(key)
            if isinstance(section, list):
                counts[key] = counts.get(key, 0) + len(section)
            elif isinstance(section, dict) and "findings" in section:
                counts[key] = counts.get(key, 0) + len(section["findings"])

    # Handle string output — count markdown heading sections
    if isinstance(output, str):
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                heading = stripped[3:].strip().lower()
                if heading in ("security", "quality", "performance", "architecture"):
                    counts[heading] = counts.get(heading, 0)

    return counts


async def _run_workflow(name: str, workflow: Any, path: str) -> RunResult:
    """Run a workflow and capture timing and result.

    Args:
        name: Human-readable label for this workflow.
        workflow: Workflow instance with an async execute() method.
        path: Target path to review.

    Returns:
        RunResult with timing and outcome data.
    """
    logger.info("Starting %s ...", name)
    start = time.monotonic()
    try:
        result = await workflow.execute(path=path)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("%s finished in %d ms (success=%s)", name, elapsed_ms, result.success)
        return RunResult(name=name, result=result, error=None, elapsed_ms=elapsed_ms)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: Catch-all so one workflow failing doesn't
        # prevent the other from running and reporting.
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("%s failed after %d ms: %s", name, elapsed_ms, exc)
        return RunResult(name=name, result=None, error=str(exc), elapsed_ms=elapsed_ms)


def _build_report(old: RunResult, new: RunResult, path: str) -> str:
    """Build a markdown comparison report.

    Args:
        old: RunResult from the mixin-based workflow.
        new: RunResult from the Agent SDK workflow.
        path: The target path that was reviewed.

    Returns:
        Markdown string.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []

    lines.append("# Code Review Workflow Comparison")
    lines.append("")
    lines.append(f"**Date:** {now}")
    lines.append(f"**Path:** `{path}`")
    lines.append("")

    # Execution time comparison
    lines.append("## Execution Time")
    lines.append("")
    lines.append("| Workflow | Time (ms) | Status |")
    lines.append("|----------|-----------|--------|")
    for run in (old, new):
        status = "FAILED" if run.error or (run.result and not run.result.success) else "OK"
        if run.error:
            status = f"ERROR: {run.error[:60]}"
        elif run.result and not run.result.success:
            status = f"FAILED: {(run.result.error or 'unknown')[:60]}"
        lines.append(f"| {run.name} | {run.elapsed_ms:,} | {status} |")
    lines.append("")

    faster = old.name if old.elapsed_ms < new.elapsed_ms else new.name
    diff_ms = abs(old.elapsed_ms - new.elapsed_ms)
    lines.append(f"**Faster:** {faster} (by {diff_ms:,} ms)")
    lines.append("")

    # Stages comparison
    lines.append("## Stages Executed")
    lines.append("")
    lines.append("| Workflow | Total Stages | Skipped | Executed |")
    lines.append("|----------|-------------|---------|----------|")
    for run in (old, new):
        if run.result:
            total = len(run.result.stages)
            skipped = sum(1 for s in run.result.stages if s.skipped)
            executed = total - skipped
            lines.append(f"| {run.name} | {total} | {skipped} | {executed} |")
        else:
            lines.append(f"| {run.name} | N/A | N/A | N/A |")
    lines.append("")

    # Summary from each
    lines.append("## Summaries")
    lines.append("")
    for run in (old, new):
        lines.append(f"### {run.name}")
        lines.append("")
        if run.error:
            lines.append(f"**Error:** {run.error}")
        elif run.result:
            summary = run.result.summary or "(no summary)"
            lines.append(summary)
        else:
            lines.append("(no result)")
        lines.append("")

    # Finding counts
    lines.append("## Findings by Category")
    lines.append("")
    old_counts = _count_findings(old.result) if old.result else {}
    new_counts = _count_findings(new.result) if new.result else {}
    all_cats = sorted(set(list(old_counts.keys()) + list(new_counts.keys())))

    if all_cats:
        lines.append("| Category | Old Workflow | New Workflow |")
        lines.append("|----------|-------------|-------------|")
        for cat in all_cats:
            lines.append(f"| {cat} | {old_counts.get(cat, 0)} | {new_counts.get(cat, 0)} |")
        lines.append("")

        old_total = sum(old_counts.values())
        new_total = sum(new_counts.values())
        lines.append(f"**Total findings:** Old={old_total}, New={new_total}")
    else:
        lines.append("No structured findings detected in either workflow output.")
    lines.append("")

    # Verdict
    lines.append("## Verdict")
    lines.append("")
    verdicts: list[str] = []

    if old.elapsed_ms < new.elapsed_ms:
        verdicts.append(
            f"- **Speed:** Old workflow was faster ({old.elapsed_ms:,} ms vs {new.elapsed_ms:,} ms)"
        )
    else:
        verdicts.append(
            f"- **Speed:** New workflow was faster ({new.elapsed_ms:,} ms vs {old.elapsed_ms:,} ms)"
        )

    if all_cats:
        old_total = sum(old_counts.values())
        new_total = sum(new_counts.values())
        if old_total > new_total:
            verdicts.append(
                f"- **Coverage:** Old workflow found more issues ({old_total} vs {new_total})"
            )
        elif new_total > old_total:
            verdicts.append(
                f"- **Coverage:** New workflow found more issues ({new_total} vs {old_total})"
            )
        else:
            verdicts.append(
                f"- **Coverage:** Both workflows found the same number of issues ({old_total})"
            )

    old_ok = old.result and old.result.success
    new_ok = new.result and new.result.success
    if old_ok and new_ok:
        verdicts.append("- **Reliability:** Both workflows completed successfully")
    elif old_ok and not new_ok:
        verdicts.append("- **Reliability:** Only the old workflow succeeded")
    elif new_ok and not old_ok:
        verdicts.append("- **Reliability:** Only the new workflow succeeded")
    else:
        verdicts.append("- **Reliability:** Both workflows failed")

    lines.extend(verdicts)
    lines.append("")

    return "\n".join(lines)


async def _main(path: str) -> None:
    """Run both workflows and produce the comparison report.

    Args:
        path: Directory or file to review.
    """
    old_wf = CodeReviewWorkflow(use_crew=False)
    new_wf = AgentCodeReviewWorkflow()

    old_run = await _run_workflow("CodeReviewWorkflow (mixin)", old_wf, path)
    new_run = await _run_workflow("AgentCodeReviewWorkflow (SDK)", new_wf, path)

    report = _build_report(old_run, new_run, path)

    # Print to stdout
    print("\n" + report)

    # Save to file
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    logger.info("Report saved to %s", REPORT_PATH)


def main() -> None:
    """Parse arguments and run the comparison."""
    parser = argparse.ArgumentParser(
        description="Compare old vs new code review workflows side-by-side.",
    )
    parser.add_argument(
        "--path",
        default="src/attune/",
        help="Directory or file to review (default: src/attune/)",
    )
    args = parser.parse_args()
    anyio.run(_main, args.path)


if __name__ == "__main__":
    main()
