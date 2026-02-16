#!/usr/bin/env python
"""CLI entry point for XML vs Plain Text benchmarks.

Usage:
    # Mock mode (no API calls, validates pipeline)
    python benchmarks/xml_vs_plain/run_benchmark.py --mock

    # Quick mode (30 calls, ~$0.32, Sonnet only)
    python benchmarks/xml_vs_plain/run_benchmark.py --quick

    # Full mode (360 calls, ~$11, Sonnet + Opus)
    python benchmarks/xml_vs_plain/run_benchmark.py --full

    # Custom
    python benchmarks/xml_vs_plain/run_benchmark.py --workflows security-audit code-review --models claude-sonnet-4-5-20250929

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from benchmarks.xml_vs_plain.config import BenchmarkConfig, BenchmarkResult
from benchmarks.xml_vs_plain.evaluator import QualityEvaluator
from benchmarks.xml_vs_plain.harness import BenchmarkHarness
from benchmarks.xml_vs_plain.report import generate_report
from benchmarks.xml_vs_plain.samples import get_samples


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="XML vs Plain Text Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM backend (no API calls, validates pipeline)",
    )
    mode.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: 5 samples, 1 run, Sonnet only (~30 calls, ~$0.32)",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="Full mode: 10 samples, 3 runs, Sonnet + Opus (~360 calls, ~$11)",
    )

    parser.add_argument(
        "--workflows",
        nargs="+",
        default=None,
        help="Workflow names to benchmark (default: security-audit code-review perf-audit)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Model IDs to test (default depends on mode)",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks/xml_vs_plain/results",
        help="Output directory for results and reports",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    """Run the benchmark suite.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 for success).
    """
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("benchmark")

    # Build config
    if args.mock:
        config = BenchmarkConfig.mock()
    elif args.quick:
        config = BenchmarkConfig.quick()
    elif args.full:
        config = BenchmarkConfig.full()
    else:
        config = BenchmarkConfig.quick()  # Default to quick

    if args.workflows:
        config.workflows = args.workflows
    if args.models:
        config.models = args.models
    config.output_dir = args.output_dir

    # Estimate cost
    n_calls = (
        len(config.workflows)
        * config.samples_per_workflow
        * 2  # XML + plain
        * len(config.models)
        * config.runs_per_sample
    )
    logger.info(
        "Configuration: %d workflows, %d samples/wf, %d runs, %d models",
        len(config.workflows),
        config.samples_per_workflow,
        config.runs_per_sample,
        len(config.models),
    )
    logger.info("Estimated LLM calls: %d", n_calls)

    if not config.use_mock:
        from benchmarks.xml_vs_plain.config import estimate_cost as est

        # Rough cost estimate assuming ~1000 prompt + ~500 completion tokens
        per_call_costs = [est(m, 1000, 500) for m in config.models]
        total_est = sum(per_call_costs) / len(per_call_costs) * n_calls
        logger.info("Estimated cost: $%.2f", total_est)

    # Create backend
    if config.use_mock:
        from benchmarks.xml_vs_plain.mock_llm import MockLLMBackend

        backend = MockLLMBackend()
        logger.info("Using MOCK backend (no API calls)")
    else:
        from benchmarks.xml_vs_plain.harness import AnthropicBackend

        backend = AnthropicBackend()
        logger.info("Using Anthropic API backend")

    # Run benchmark
    harness = BenchmarkHarness(config, backend)
    results = await harness.run_all()

    # Build sample lookup for evaluation
    sample_lookup = {}
    for workflow in config.workflows:
        for sample in get_samples(workflow, config.samples_per_workflow):
            sample_lookup[sample.id] = sample

    # Evaluate quality
    evaluator = QualityEvaluator()
    results = evaluator.evaluate_all(results, sample_lookup)

    # Generate report
    report = generate_report(results, config.workflows, config.models)

    # Save results
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "benchmark_report.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info("Report saved to: %s", report_path)

    # Save raw results as JSON
    results_path = output_dir / "benchmark_results.json"
    results_data = []
    for r in results:
        entry = {
            "sample_id": r.sample_id,
            "workflow": r.workflow,
            "model": r.model,
            "xml_enabled": r.xml_enabled,
            "run_number": r.run_number,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "estimated_cost_usd": r.estimated_cost_usd,
            "latency_ms": r.latency_ms,
            "xml_parse_success": r.xml_parse_success,
            "findings_count": r.findings_count,
            "findings_by_severity": r.findings_by_severity,
        }
        if r.quality_score:
            entry["quality"] = {
                "parsing": r.quality_score.parsing_score,
                "completeness": r.quality_score.completeness_score,
                "precision": r.quality_score.precision_score,
                "actionability": r.quality_score.actionability_score,
                "consistency": r.quality_score.consistency_score,
                "overall": r.quality_score.overall,
            }
        results_data.append(entry)

    results_path.write_text(
        json.dumps(results_data, indent=2),
        encoding="utf-8",
    )
    logger.info("Raw results saved to: %s", results_path)

    # Print report to stdout
    print("\n" + report)

    return 0


def main() -> None:
    """Entry point."""
    args = parse_args()
    exit_code = asyncio.run(run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
