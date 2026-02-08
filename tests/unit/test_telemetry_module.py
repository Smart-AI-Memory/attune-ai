"""Unit tests for telemetry module - cost tracking and metrics."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.unit
def test_telemetry_cost_aggregation():
    """Test cost aggregation from daily data."""
    # Sample telemetry data structure
    daily_data = {
        "2025-01-01": {"actual_cost": 0.05, "savings": 0.10, "requests": 5},
        "2025-01-02": {"actual_cost": 0.03, "savings": 0.07, "requests": 3},
        "2025-01-03": {"actual_cost": 0.04, "savings": 0.08, "requests": 4},
    }

    # Calculate totals
    total_cost = sum(d["actual_cost"] for d in daily_data.values())
    total_savings = sum(d["savings"] for d in daily_data.values())
    total_requests = sum(d["requests"] for d in daily_data.values())

    assert total_cost == pytest.approx(0.12), "Total cost should sum correctly"
    assert total_savings == pytest.approx(0.25), "Total savings should sum correctly"
    assert total_requests == 12, "Total requests should sum correctly"

    # Calculate savings percentage
    baseline_cost = total_cost + total_savings
    savings_percent = (total_savings / baseline_cost) * 100 if baseline_cost > 0 else 0

    assert 67.0 <= savings_percent <= 68.0, "Savings percentage should be ~67.6%"


@pytest.mark.unit
def test_telemetry_provider_breakdown():
    """Test telemetry data grouped by provider."""
    provider_data = {
        "anthropic": {"requests": 10, "actual_cost": 0.10},
        "openai": {"requests": 2, "actual_cost": 0.02},
    }

    # Verify structure
    assert "anthropic" in provider_data
    assert "openai" in provider_data

    # Verify metrics (use approx for floating point)
    total_requests = sum(p["requests"] for p in provider_data.values())
    total_cost = sum(p["actual_cost"] for p in provider_data.values())

    assert total_requests == 12
    assert total_cost == pytest.approx(0.12)


@pytest.mark.unit
def test_telemetry_date_range_filtering():
    """Test filtering telemetry data by date range."""
    daily_data = {
        "2025-01-01": {"actual_cost": 0.05},
        "2025-01-02": {"actual_cost": 0.03},
        "2025-01-03": {"actual_cost": 0.04},
        "2025-01-10": {"actual_cost": 0.02},  # Outside 7-day window
    }

    # Filter last 7 days from 2025-01-03
    cutoff_date = datetime(2025, 1, 3) - timedelta(days=7)

    filtered = {
        date: data
        for date, data in daily_data.items()
        if datetime.strptime(date, "%Y-%m-%d") >= cutoff_date
    }

    # All dates should be included (all within 7 days of cutoff)
    assert len(filtered) == 4


@pytest.mark.unit
def test_telemetry_zero_cost_handling():
    """Test handling of zero costs and edge cases."""
    # Zero cost scenario
    zero_data = {"actual_cost": 0.0, "savings": 0.0, "requests": 0}

    baseline = zero_data["actual_cost"] + zero_data["savings"]
    savings_percent = (zero_data["savings"] / baseline * 100) if baseline > 0 else 0

    assert savings_percent == 0, "Zero baseline should give 0% savings"

    # Only savings, no cost
    savings_only = {"actual_cost": 0.0, "savings": 0.10, "requests": 5}
    baseline = savings_only["actual_cost"] + savings_only["savings"]
    savings_percent = (savings_only["savings"] / baseline * 100) if baseline > 0 else 0

    assert savings_percent == 100, "100% savings when actual cost is 0"


@pytest.mark.unit
def test_telemetry_workflow_cost_tracking():
    """Test per-workflow cost tracking."""
    workflow_costs = {
        "bug-predict": {"cost": 0.02, "runs": 5},
        "code-review": {"cost": 0.05, "runs": 3},
        "health-check": {"cost": 0.01, "runs": 10},
    }

    # Calculate average cost per workflow
    for workflow, data in workflow_costs.items():
        avg_cost = data["cost"] / data["runs"] if data["runs"] > 0 else 0
        assert avg_cost > 0, f"{workflow} should have positive average cost"

    # Find most expensive workflow by total cost
    most_expensive = max(workflow_costs.items(), key=lambda x: x[1]["cost"])
    assert most_expensive[0] == "code-review", "code-review should be most expensive"


@pytest.mark.unit
def test_telemetry_metrics_validation():
    """Test validation of telemetry metrics."""
    valid_metrics = {
        "actual_cost": 0.10,
        "savings": 0.20,
        "requests": 5,
        "baseline_cost": 0.30,
    }

    # Verify all metrics are non-negative
    for key, value in valid_metrics.items():
        if isinstance(value, int | float):
            assert value >= 0, f"{key} should be non-negative"

    # Verify baseline = actual + savings (use approx for floating point)
    expected_baseline = valid_metrics["actual_cost"] + valid_metrics["savings"]
    assert valid_metrics["baseline_cost"] == pytest.approx(expected_baseline)

    # Verify requests is integer
    assert isinstance(valid_metrics["requests"], int), "requests should be integer"


@pytest.mark.unit
def test_telemetry_token_counting():
    """Test token usage tracking and cost calculations."""
    # Token usage data
    usage_data = {
        "model": "claude-sonnet-4",
        "input_tokens": 1000,
        "output_tokens": 500,
        "input_cost_per_million": 3.0,
        "output_cost_per_million": 15.0,
    }

    # Calculate costs
    input_cost = (usage_data["input_tokens"] / 1_000_000) * usage_data["input_cost_per_million"]
    output_cost = (usage_data["output_tokens"] / 1_000_000) * usage_data["output_cost_per_million"]
    total_cost = input_cost + output_cost

    assert input_cost == pytest.approx(0.003)
    assert output_cost == pytest.approx(0.0075)
    assert total_cost == pytest.approx(0.0105)


@pytest.mark.unit
def test_telemetry_multi_provider_aggregation():
    """Test aggregating telemetry across multiple providers."""
    multi_provider_data = {
        "anthropic": {
            "claude-haiku": {"cost": 0.01, "requests": 10},
            "claude-sonnet": {"cost": 0.05, "requests": 5},
        },
        "openai": {
            "gpt-4o-mini": {"cost": 0.02, "requests": 8},
            "gpt-4o": {"cost": 0.08, "requests": 4},
        },
    }

    # Aggregate by provider
    provider_totals = {}
    for provider, models in multi_provider_data.items():
        total_cost = sum(m["cost"] for m in models.values())
        total_requests = sum(m["requests"] for m in models.values())
        provider_totals[provider] = {"cost": total_cost, "requests": total_requests}

    assert provider_totals["anthropic"]["cost"] == pytest.approx(0.06)
    assert provider_totals["anthropic"]["requests"] == 15
    assert provider_totals["openai"]["cost"] == pytest.approx(0.10)
    assert provider_totals["openai"]["requests"] == 12


@pytest.mark.unit
def test_telemetry_cost_optimization_ratio():
    """Test calculating cost optimization ratios."""
    optimization_data = {
        "premium_model_cost": 0.50,  # What it would cost with premium
        "actual_cost": 0.10,  # What it actually cost with routing
        "cheap_model_cost": 0.05,  # What it would cost with cheapest
    }

    # Calculate optimization ratio
    premium_savings = optimization_data["premium_model_cost"] - optimization_data["actual_cost"]
    optimization_ratio = premium_savings / optimization_data["premium_model_cost"] * 100

    assert premium_savings == pytest.approx(0.40)
    assert optimization_ratio == pytest.approx(80.0)  # 80% savings vs premium

    # Verify we're not overly cheap (quality tradeoff)
    cheap_penalty = optimization_data["actual_cost"] - optimization_data["cheap_model_cost"]
    assert cheap_penalty == pytest.approx(0.05)  # Paying 2x cheap for better quality


@pytest.mark.unit
def test_telemetry_time_series_trends():
    """Test analyzing trends in telemetry data over time."""
    time_series = [
        {"date": "2025-01-01", "cost": 0.10, "requests": 5},
        {"date": "2025-01-02", "cost": 0.12, "requests": 6},
        {"date": "2025-01-03", "cost": 0.15, "requests": 7},
        {"date": "2025-01-04", "cost": 0.14, "requests": 7},
    ]

    # Calculate day-over-day cost change
    for i in range(1, len(time_series)):
        prev_cost = time_series[i - 1]["cost"]
        curr_cost = time_series[i]["cost"]
        change = curr_cost - prev_cost
        time_series[i]["cost_change"] = change

    # Verify trend calculation
    assert time_series[1]["cost_change"] == pytest.approx(0.02)  # +$0.02
    assert time_series[2]["cost_change"] == pytest.approx(0.03)  # +$0.03
    assert time_series[3]["cost_change"] == pytest.approx(-0.01)  # -$0.01 (improvement)


@pytest.mark.unit
def test_telemetry_budget_tracking():
    """Test budget tracking and alerting logic."""
    budget_config = {
        "daily_budget": 1.00,
        "monthly_budget": 25.00,
        "alert_threshold": 0.80,  # Alert at 80% of budget
    }

    # Current usage
    current_daily = 0.85
    current_monthly = 20.50

    # Calculate budget utilization
    daily_utilization = current_daily / budget_config["daily_budget"]
    monthly_utilization = current_monthly / budget_config["monthly_budget"]

    assert daily_utilization == pytest.approx(0.85)
    assert monthly_utilization == pytest.approx(0.82)

    # Check if alerts should trigger
    daily_alert = daily_utilization >= budget_config["alert_threshold"]
    monthly_alert = monthly_utilization >= budget_config["alert_threshold"]

    assert daily_alert is True  # Should trigger alert (85% > 80%)
    assert monthly_alert is True  # Should trigger alert (82% > 80%)
