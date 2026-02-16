"""Markdown report generator for benchmark results.

Produces comparison tables, per-workflow breakdowns, and recommendations
based on benchmark data.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime

from benchmarks.xml_vs_plain.config import BenchmarkResult, QualityScore


def generate_report(
    results: list[BenchmarkResult],
    workflows: list[str],
    models: list[str],
) -> str:
    """Generate a full markdown comparison report.

    Args:
        results: All benchmark results (with quality_score populated).
        workflows: Workflow names tested.
        models: Model IDs tested.

    Returns:
        Markdown report string.
    """
    lines: list[str] = []
    lines.append("# XML vs Plain Text Benchmark Results\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Models:** {', '.join(models)}")
    lines.append(f"**Workflows:** {', '.join(workflows)}")
    lines.append(f"**Total calls:** {len(results)}")

    total_cost = sum(r.estimated_cost_usd for r in results)
    lines.append(f"**Total cost:** ${total_cost:.4f}\n")

    # Split by XML vs plain
    xml_results = [r for r in results if r.xml_enabled]
    plain_results = [r for r in results if not r.xml_enabled]

    lines.append("---\n")
    lines.append("## Summary\n")
    lines.append(_summary_table(xml_results, plain_results))

    lines.append("\n---\n")
    lines.append("## Per-Workflow Breakdown\n")
    for workflow in workflows:
        wf_xml = [r for r in xml_results if r.workflow == workflow]
        wf_plain = [r for r in plain_results if r.workflow == workflow]
        if wf_xml or wf_plain:
            lines.append(f"\n### {workflow}\n")
            lines.append(_workflow_table(wf_xml, wf_plain))

    if len(models) > 1:
        lines.append("\n---\n")
        lines.append("## Per-Model Breakdown\n")
        for model in models:
            m_xml = [r for r in xml_results if r.model == model]
            m_plain = [r for r in plain_results if r.model == model]
            if m_xml or m_plain:
                short_name = model.split("-")[1] if "-" in model else model
                lines.append(f"\n### {short_name}\n")
                lines.append(_summary_table(m_xml, m_plain))

    lines.append("\n---\n")
    lines.append("## Cost Analysis\n")
    lines.append(_cost_analysis(xml_results, plain_results))

    lines.append("\n---\n")
    lines.append("## Recommendation\n")
    lines.append(_recommendation(xml_results, plain_results, workflows))

    return "\n".join(lines)


def _summary_table(xml_results: list[BenchmarkResult], plain_results: list[BenchmarkResult]) -> str:
    """Generate the summary comparison table."""
    xml_stats = _compute_stats(xml_results)
    plain_stats = _compute_stats(plain_results)

    rows = [
        "| Metric | XML | Plain | Delta |",
        "|--------|-----|-------|-------|",
    ]

    metrics = [
        ("Parse success rate", "parse_rate", "%"),
        ("Avg prompt tokens", "avg_prompt_tokens", ""),
        ("Avg completion tokens", "avg_completion_tokens", ""),
        ("Avg cost per call", "avg_cost", "$"),
        ("Avg latency (ms)", "avg_latency", ""),
        ("Avg completeness", "avg_completeness", ""),
        ("Avg precision", "avg_precision", ""),
        ("Avg actionability", "avg_actionability", ""),
        ("Avg consistency", "avg_consistency", ""),
        ("Avg overall quality", "avg_overall", ""),
    ]

    for label, key, fmt in metrics:
        xml_val = xml_stats.get(key, 0.0)
        plain_val = plain_stats.get(key, 0.0)
        delta = xml_val - plain_val

        if fmt == "%":
            xml_str = f"{xml_val:.0%}"
            plain_str = f"{plain_val:.0%}"
            delta_str = f"{delta:+.0%}"
        elif fmt == "$":
            xml_str = f"${xml_val:.4f}"
            plain_str = f"${plain_val:.4f}"
            pct = (delta / plain_val * 100) if plain_val else 0
            delta_str = f"{pct:+.0f}%"
        else:
            xml_str = f"{xml_val:.2f}"
            plain_str = f"{plain_val:.2f}"
            if plain_val:
                pct = delta / plain_val * 100
                delta_str = f"{pct:+.0f}%"
            else:
                delta_str = "N/A"

        rows.append(f"| {label} | {xml_str} | {plain_str} | {delta_str} |")

    return "\n".join(rows)


def _workflow_table(
    xml_results: list[BenchmarkResult], plain_results: list[BenchmarkResult]
) -> str:
    """Generate a per-workflow comparison table."""
    xml_stats = _compute_stats(xml_results)
    plain_stats = _compute_stats(plain_results)

    rows = [
        "| Format | Parse % | Completeness | Precision | Actionability | Cost/call |",
        "|--------|---------|-------------|-----------|---------------|-----------|",
    ]

    rows.append(
        f"| XML | {xml_stats.get('parse_rate', 0):.0%} "
        f"| {xml_stats.get('avg_completeness', 0):.2f} "
        f"| {xml_stats.get('avg_precision', 0):.2f} "
        f"| {xml_stats.get('avg_actionability', 0):.2f} "
        f"| ${xml_stats.get('avg_cost', 0):.4f} |"
    )
    rows.append(
        f"| Plain | {plain_stats.get('parse_rate', 0):.0%} "
        f"| {plain_stats.get('avg_completeness', 0):.2f} "
        f"| {plain_stats.get('avg_precision', 0):.2f} "
        f"| {plain_stats.get('avg_actionability', 0):.2f} "
        f"| ${plain_stats.get('avg_cost', 0):.4f} |"
    )

    return "\n".join(rows)


def _cost_analysis(xml_results: list[BenchmarkResult], plain_results: list[BenchmarkResult]) -> str:
    """Generate cost analysis section."""
    xml_total = sum(r.estimated_cost_usd for r in xml_results)
    plain_total = sum(r.estimated_cost_usd for r in plain_results)
    xml_avg = xml_total / len(xml_results) if xml_results else 0
    plain_avg = plain_total / len(plain_results) if plain_results else 0

    overhead = ((xml_avg - plain_avg) / plain_avg * 100) if plain_avg else 0

    lines = [
        f"- XML total cost: ${xml_total:.4f} ({len(xml_results)} calls)",
        f"- Plain total cost: ${plain_total:.4f} ({len(plain_results)} calls)",
        f"- XML avg cost/call: ${xml_avg:.4f}",
        f"- Plain avg cost/call: ${plain_avg:.4f}",
        f"- **XML cost overhead: {overhead:+.1f}%**",
    ]

    if overhead > 25:
        lines.append("\nXML cost overhead exceeds 25% threshold.")
    elif overhead > 0:
        lines.append(
            f"\nXML adds {overhead:.1f}% cost overhead — within acceptable range if quality improves."
        )
    else:
        lines.append("\nXML is cost-neutral or cheaper (likely due to more concise responses).")

    return "\n".join(lines)


def _recommendation(
    xml_results: list[BenchmarkResult],
    plain_results: list[BenchmarkResult],
    workflows: list[str],
) -> str:
    """Generate per-workflow recommendations."""
    lines: list[str] = []

    for workflow in workflows:
        wf_xml = [r for r in xml_results if r.workflow == workflow]
        wf_plain = [r for r in plain_results if r.workflow == workflow]

        if not wf_xml or not wf_plain:
            lines.append(f"- **{workflow}**: Insufficient data")
            continue

        xml_stats = _compute_stats(wf_xml)
        plain_stats = _compute_stats(wf_plain)

        quality_delta = xml_stats.get("avg_overall", 0) - plain_stats.get("avg_overall", 0)
        cost_overhead = 0.0
        if plain_stats.get("avg_cost", 0) > 0:
            cost_overhead = (
                (xml_stats.get("avg_cost", 0) - plain_stats.get("avg_cost", 0))
                / plain_stats["avg_cost"]
                * 100
            )

        if quality_delta > 0.10 and cost_overhead < 25:
            verdict = "ENABLE XML"
            reason = f"+{quality_delta:.0%} quality, {cost_overhead:+.0f}% cost"
        elif quality_delta < 0.05:
            verdict = "KEEP PLAIN"
            reason = f"Only {quality_delta:+.0%} quality difference"
        elif cost_overhead > 25:
            verdict = "KEEP PLAIN"
            reason = f"Cost overhead too high ({cost_overhead:+.0f}%)"
        else:
            verdict = "INCONCLUSIVE"
            reason = f"{quality_delta:+.0%} quality, {cost_overhead:+.0f}% cost — needs more data"

        lines.append(f"- **{workflow}**: {verdict} ({reason})")

    return "\n".join(lines)


def _compute_stats(results: list[BenchmarkResult]) -> dict[str, float]:
    """Compute aggregate statistics for a set of results."""
    if not results:
        return {}

    n = len(results)
    parse_successes = sum(1 for r in results if r.xml_parse_success)

    quality_scores = [r.quality_score for r in results if r.quality_score]

    return {
        "parse_rate": parse_successes / n,
        "avg_prompt_tokens": sum(r.prompt_tokens for r in results) / n,
        "avg_completion_tokens": sum(r.completion_tokens for r in results) / n,
        "avg_cost": sum(r.estimated_cost_usd for r in results) / n,
        "avg_latency": sum(r.latency_ms for r in results) / n,
        "avg_completeness": (
            sum(q.completeness_score for q in quality_scores) / len(quality_scores)
            if quality_scores
            else 0.0
        ),
        "avg_precision": (
            sum(q.precision_score for q in quality_scores) / len(quality_scores)
            if quality_scores
            else 0.0
        ),
        "avg_actionability": (
            sum(q.actionability_score for q in quality_scores) / len(quality_scores)
            if quality_scores
            else 0.0
        ),
        "avg_consistency": (
            sum(q.consistency_score for q in quality_scores) / len(quality_scores)
            if quality_scores
            else 0.0
        ),
        "avg_overall": (
            sum(q.overall for q in quality_scores) / len(quality_scores) if quality_scores else 0.0
        ),
    }
