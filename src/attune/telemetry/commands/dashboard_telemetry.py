"""Telemetry cost dashboard - interactive HTML visualization.

Generates an HTML dashboard showing LLM API costs, tier distribution,
and savings from tier routing.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import tempfile
import webbrowser
from collections import Counter
from datetime import datetime
from typing import Any

from ..usage_tracker import UsageTracker


def cmd_telemetry_dashboard(args: Any) -> int:
    """Open interactive telemetry dashboard in browser.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)

    """
    tracker = UsageTracker.get_instance()
    entries = tracker.export_to_dict(days=getattr(args, "days", 30))

    if not entries:
        print("No telemetry data available.")
        return 0

    # Calculate statistics
    total_cost = sum(e.get("cost", 0) for e in entries)
    total_calls = len(entries)
    avg_duration = (
        sum(e.get("duration_ms", 0) for e in entries) / total_calls if total_calls > 0 else 0
    )

    # Tier distribution
    tiers = [e.get("tier", "UNKNOWN") for e in entries]
    tier_counts = Counter(tiers)
    tier_distribution = {tier: (count / total_calls) * 100 for tier, count in tier_counts.items()}

    # Calculate savings (baseline: all PREMIUM tier)
    premium_input_cost = 0.015 / 1000  # per token
    premium_output_cost = 0.075 / 1000  # per token

    baseline_cost = sum(
        (e.get("tokens", {}).get("input", 0) * premium_input_cost)
        + (e.get("tokens", {}).get("output", 0) * premium_output_cost)
        for e in entries
    )

    saved = baseline_cost - total_cost
    savings_pct = (saved / baseline_cost * 100) if baseline_cost > 0 else 0

    # Generate HTML
    html_content = _build_telemetry_html(
        entries=entries,
        total_cost=total_cost,
        total_calls=total_calls,
        avg_duration=avg_duration,
        tier_distribution=tier_distribution,
        saved=saved,
        savings_pct=savings_pct,
        baseline_cost=baseline_cost,
    )

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_content)
        temp_path = f.name

    print(f"\U0001f4ca Opening dashboard in browser: {temp_path}")
    webbrowser.open(f"file://{temp_path}")

    return 0


def _build_telemetry_html(
    *,
    entries: list[dict],
    total_cost: float,
    total_calls: int,
    avg_duration: float,
    tier_distribution: dict[str, float],
    saved: float,
    savings_pct: float,
    baseline_cost: float,
) -> str:
    """Build the telemetry dashboard HTML string.

    Args:
        entries: Telemetry entries
        total_cost: Sum of all costs
        total_calls: Number of API calls
        avg_duration: Average duration in ms
        tier_distribution: Tier name -> percentage
        saved: Dollar amount saved
        savings_pct: Savings percentage
        baseline_cost: Baseline cost (all premium)

    Returns:
        Complete HTML string

    """
    tier_bars = "".join(
        f'<div class="tier-bar tier-{tier.lower()}">{tier}: {pct:.1f}%</div>'
        for tier, pct in tier_distribution.items()
    )

    table_rows = "".join(
        f"""<tr>
            <td>{datetime.fromisoformat(e.get("ts", "").replace("Z", "+00:00")).strftime("%H:%M:%S")}</td>
            <td>{e.get("workflow", "")}</td>
            <td>{e.get("stage", "")}</td>
            <td><span class="tier-badge badge-{e.get("tier", "").lower()}">{e.get("tier", "")}</span></td>
            <td>${e.get("cost", 0):.4f}</td>
            <td>{e.get("tokens", {}).get("input", 0)}/{e.get("tokens", {}).get("output", 0)}</td>
            <td class="cache-{"hit" if e.get("cache", {}).get("hit") else "miss"}">
                {"HIT" if e.get("cache", {}).get("hit") else "MISS"}
            </td>
            <td>{e.get("duration_ms", 0) / 1000:.1f}s</td>
        </tr>"""
        for e in list(reversed(entries))[:20]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Empathy Telemetry Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ color: white; text-align: center; margin-bottom: 40px; }}
        .header h1 {{ font-size: 48px; font-weight: 700; margin-bottom: 10px; }}
        .header p {{ font-size: 18px; opacity: 0.9; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .savings-card {{
            grid-column: span 2;
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
            color: white;
        }}
        .stat-label {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            opacity: 0.8;
        }}
        .stat-value {{ font-size: 56px; font-weight: 700; margin-bottom: 5px; }}
        .stat-sublabel {{ font-size: 16px; opacity: 0.7; }}
        .tier-distribution {{ display: flex; gap: 10px; margin-top: 15px; height: 50px; }}
        .tier-bar {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            font-weight: 600;
            color: white;
            font-size: 14px;
        }}
        .tier-premium {{ background: linear-gradient(135deg, #9c27b0, #7b1fa2); }}
        .tier-capable {{ background: linear-gradient(135deg, #2196f3, #1976d2); }}
        .tier-cheap {{ background: linear-gradient(135deg, #4caf50, #388e3c); }}
        table {{
            width: 100%;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        th, td {{ padding: 16px; text-align: left; }}
        th {{
            background: #f5f5f5;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #666;
        }}
        tr:hover {{ background: #f9f9f9; }}
        .tier-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            color: white;
        }}
        .badge-premium {{ background: #9c27b0; }}
        .badge-capable {{ background: #2196f3; }}
        .badge-cheap {{ background: #4caf50; }}
        .cache-hit {{ color: #4caf50; font-weight: 600; }}
        .cache-miss {{ color: #999; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>\U0001f4ca Empathy Telemetry Dashboard</h1>
            <p>Last {len(entries)} LLM API calls \u2022 Real-time cost tracking</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card savings-card">
                <div class="stat-label">Cost Savings (Tier Routing)</div>
                <div class="stat-value">${saved:.2f}</div>
                <div class="stat-sublabel">
                    {savings_pct:.1f}% saved \u2022 Baseline: ${baseline_cost:.2f} \u2022 Actual: ${total_cost:.2f}
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Total Cost</div>
                <div class="stat-value">${total_cost:.2f}</div>
                <div class="stat-sublabel">{total_calls} API calls</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Avg Duration</div>
                <div class="stat-value">{avg_duration / 1000:.1f}s</div>
                <div class="stat-sublabel">Per API call</div>
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Tier Distribution</div>
            <div class="tier-distribution">
                {tier_bars}
            </div>
        </div>

        <h2 style="color: white; margin: 40px 0 20px 0; font-size: 28px;">Recent LLM Calls</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Workflow</th>
                    <th>Stage</th>
                    <th>Tier</th>
                    <th>Cost</th>
                    <th>Tokens</th>
                    <th>Cache</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>"""
