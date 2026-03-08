"""Bug Prediction Report Formatting and CLI Entry Point.

Extracted from bug_predict.py for maintainability.

Functions:
    format_bug_predict_report: Format prediction output as human-readable report
    main: CLI entry point for bug prediction workflow

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations


def format_bug_predict_report(result: dict, input_data: dict) -> str:
    """Format bug prediction output as a human-readable report.

    Args:
        result: The recommend stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    lines = []

    # Header with risk assessment
    risk_score = result.get("overall_risk_score", 0)
    if risk_score >= 0.8:
        risk_icon = "🔴"
        risk_text = "HIGH RISK"
    elif risk_score >= 0.5:
        risk_icon = "🟠"
        risk_text = "MODERATE RISK"
    elif risk_score >= 0.3:
        risk_icon = "🟡"
        risk_text = "LOW RISK"
    else:
        risk_icon = "🟢"
        risk_text = "MINIMAL RISK"

    lines.append("=" * 60)
    lines.append("BUG PREDICTION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Overall Risk: {risk_icon} {risk_text} ({risk_score:.0%})")
    lines.append("")

    # Scan summary
    file_count = input_data.get("file_count", 0)
    pattern_count = input_data.get("pattern_count", 0)
    lines.append("-" * 60)
    lines.append("SCAN SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Files Scanned: {file_count}")
    lines.append(f"Patterns Found: {pattern_count}")
    lines.append("")

    # Patterns found by severity
    patterns = input_data.get("patterns_found", [])
    if patterns:
        high = [p for p in patterns if p.get("severity") == "high"]
        medium = [p for p in patterns if p.get("severity") == "medium"]
        low = [p for p in patterns if p.get("severity") == "low"]

        lines.append("Pattern Breakdown:")
        lines.append(f"  🔴 High: {len(high)}")
        lines.append(f"  🟡 Medium: {len(medium)}")
        lines.append(f"  🟢 Low: {len(low)}")
        lines.append("")

    # High risk predictions
    predictions = input_data.get("predictions", [])
    high_risk = [p for p in predictions if float(p.get("risk_score", 0)) > 0.7]
    if high_risk:
        lines.append("-" * 60)
        lines.append("HIGH RISK FILES")
        lines.append("-" * 60)
        for pred in high_risk[:10]:
            file_path = pred.get("file", "unknown")
            score = pred.get("risk_score", 0)
            file_patterns = pred.get("patterns", [])
            lines.append(f"  🔴 {file_path} (risk: {score:.0%})")
            for p in file_patterns[:3]:
                lines.append(
                    f"      - {p.get('pattern', 'unknown')}: {p.get('severity', 'unknown')}",
                )
        lines.append("")

    # Correlations with historical bugs
    correlations = input_data.get("correlations", [])
    high_conf = [
        c for c in correlations if c.get("confidence", 0) > 0.6 and c.get("historical_bug")
    ]
    if high_conf:
        lines.append("-" * 60)
        lines.append("HISTORICAL BUG CORRELATIONS")
        lines.append("-" * 60)
        for corr in high_conf[:5]:
            current = corr.get("current_pattern", {})
            historical = corr.get("historical_bug", {})
            confidence = corr.get("confidence", 0)
            lines.append(
                f"  ⚠️ {current.get('pattern', 'unknown')} correlates with {historical.get('type', 'unknown')}",
            )
            lines.append(f"      Confidence: {confidence:.0%}")
            if historical.get("root_cause"):
                lines.append(f"      Root cause: {historical.get('root_cause')[:80]}")
        lines.append("")

    # Recommendations
    recommendations = result.get("recommendations", "")
    if recommendations:
        lines.append("-" * 60)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 60)
        lines.append(recommendations)
        lines.append("")

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    lines.append(f"Analysis completed using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    """CLI entry point for bug prediction workflow."""
    import asyncio

    async def run():
        """Run the bug prediction analysis stage."""
        from .bug_predict import BugPredictionWorkflow

        workflow = BugPredictionWorkflow()
        result = await workflow.execute(path=".", file_types=[".py"])

        print("\nBug Prediction Results")
        print("=" * 50)
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")
        print(f"Risk Score: {result.final_output.get('overall_risk_score', 0)}")
        print(f"Recommendations: {result.final_output.get('recommendation_count', 0)}")
        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())
