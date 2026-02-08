"""Unit tests for telemetry functionality."""

import json
from pathlib import Path

import pytest


@pytest.mark.unit
def test_costs_file_structure():
    """Test that costs.json has expected structure if it exists."""
    costs_file = Path(".attune/costs.json")

    if costs_file.exists():
        with open(costs_file) as f:
            data = json.load(f)

        # Verify expected structure
        assert isinstance(data, dict), "Costs data should be a dictionary"

        # Check for expected top-level keys
        if "daily_totals" in data:
            assert isinstance(data["daily_totals"], dict)

        if "by_provider" in data:
            assert isinstance(data["by_provider"], dict)
    else:
        # If file doesn't exist, test passes (optional data)
        pytest.skip("Costs file doesn't exist yet")


@pytest.mark.unit
def test_health_file_structure():
    """Test that health.json has expected structure if it exists."""
    health_file = Path(".attune/health.json")

    if health_file.exists():
        with open(health_file) as f:
            data = json.load(f)

        # Verify it's a dictionary
        assert isinstance(data, dict), "Health data should be a dictionary"

        # Check for score if present
        if "score" in data:
            score = data["score"]
            assert isinstance(score, int | float)
            assert 0 <= score <= 100, "Health score should be between 0-100"
    else:
        pytest.skip("Health file doesn't exist yet")


@pytest.mark.unit
def test_workflow_runs_structure():
    """Test that workflow_runs.json has expected structure if it exists."""
    runs_file = Path(".attune/workflow_runs.json")

    if runs_file.exists():
        with open(runs_file) as f:
            data = json.load(f)

        # Should be a list of workflow runs
        assert isinstance(data, list), "Workflow runs should be a list"

        # If there are runs, check structure
        if data:
            first_run = data[0]
            assert isinstance(first_run, dict), "Each run should be a dictionary"

            # Check for expected fields
            if "workflow" in first_run:
                assert isinstance(first_run["workflow"], str)
            if "success" in first_run:
                assert isinstance(first_run["success"], bool)
    else:
        pytest.skip("Workflow runs file doesn't exist yet")
