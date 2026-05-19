"""Phase 2 of anthropic-cost-integration — home page wiring.

The spec (docs/specs/anthropic-cost-integration/tasks.md, task 2.4)
specifies four scenarios this file covers:

1. No admin key → CTA tile, no traceback, dashboard otherwise functional
2. Valid CostSummary → all three account KPI tiles populated
3. Auth-failed error → friendly notice, dashboard otherwise functional
4. ?refresh=1 query param → fetch called with refresh=True

The fetch_summary call is mocked at its import site in dashboard.py
(not at its definition site) so the dispatch in the home route picks
up the mock. See CLAUDE.md lesson "Real project files on disk override
test mocks" for the rationale.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.anthropic_cost import CostFetchError, CostSummary  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(config)
    return TestClient(app)


def _valid_summary() -> CostSummary:
    return CostSummary(
        today_usd=4.72,
        seven_day_usd=18.31,
        month_to_date_usd=42.50,
        thirty_day_usd=42.50,
        by_day=[(date(2026, 5, 19), 4.72)],
        by_model=[("claude-sonnet-4-5", 4.72)],
        by_cost_type=[("input_tokens", 1.10), ("output_tokens", 3.62)],
        fetched_at=datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc),
        source="live",
    )


def test_home_renders_cta_when_no_admin_key(tmp_path, monkeypatch):
    """Home page shows the no-key CTA, no traceback, dashboard renders."""
    err = CostFetchError(kind="no_key", message="no admin key configured")
    with patch(
        "attune.ops.anthropic_cost.fetch_summary",
        return_value=(None, err),
    ):
        with _client(tmp_path, monkeypatch) as client:
            resp = client.get("/")

    assert resp.status_code == 200
    # CTA copy and class are present.
    assert "Set up cost reporting" in resp.text
    assert "Connect billing" in resp.text
    assert "kpi-cluster-account" in resp.text
    # Telemetry tiles still render — dashboard is otherwise functional.
    assert "Today's events" in resp.text
    assert "7-day spend" in resp.text


def test_home_renders_three_tiles_with_valid_summary(tmp_path, monkeypatch):
    """All three account-spend KPI tiles populated with formatted USD."""
    summary = _valid_summary()
    with patch(
        "attune.ops.anthropic_cost.fetch_summary",
        return_value=(summary, None),
    ):
        with _client(tmp_path, monkeypatch) as client:
            resp = client.get("/")

    assert resp.status_code == 200
    # Three tile labels.
    assert "Today (account)" in resp.text
    assert "7d (account)" in resp.text
    assert "MTD (account)" in resp.text
    # Formatted dollar values.
    assert "$4.72" in resp.text
    assert "$18.31" in resp.text
    assert "$42.50" in resp.text
    # Source indicator visible on the today tile.
    assert "live" in resp.text


def test_home_renders_notice_on_auth_failed(tmp_path, monkeypatch):
    """auth_failed surfaces a friendly notice; dashboard stays functional."""
    err = CostFetchError(kind="auth_failed", message="key rejected (HTTP 401)")
    with patch(
        "attune.ops.anthropic_cost.fetch_summary",
        return_value=(None, err),
    ):
        with _client(tmp_path, monkeypatch) as client:
            resp = client.get("/")

    assert resp.status_code == 200
    assert "Key rejected" in resp.text
    assert "kpi-notice" in resp.text
    # Friendly notice — no raw HTTP status or stack trace surfaced.
    assert "HTTP 401" not in resp.text
    # Workflow and version tiles still render.
    assert "Workflows" in resp.text


def test_home_passes_refresh_true_when_query_param_set(tmp_path, monkeypatch):
    """?refresh=1 → fetch_summary called with refresh=True."""
    summary = _valid_summary()
    with patch(
        "attune.ops.anthropic_cost.fetch_summary",
        return_value=(summary, None),
    ) as mock_fetch:
        with _client(tmp_path, monkeypatch) as client:
            resp = client.get("/?refresh=1")

    assert resp.status_code == 200
    mock_fetch.assert_called_once()
    # Keyword arg, per the helper's keyword-only signature.
    assert mock_fetch.call_args.kwargs.get("refresh") is True


def test_home_default_call_passes_refresh_false(tmp_path, monkeypatch):
    """Without ?refresh=1, fetch_summary is called with refresh=False."""
    summary = _valid_summary()
    with patch(
        "attune.ops.anthropic_cost.fetch_summary",
        return_value=(summary, None),
    ) as mock_fetch:
        with _client(tmp_path, monkeypatch) as client:
            resp = client.get("/")

    assert resp.status_code == 200
    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.kwargs.get("refresh") is False


def test_home_degrades_silently_on_fetch_exception(tmp_path, monkeypatch):
    """Unexpected fetch exception → no tile cluster, dashboard renders.

    Defensive try/except in the home route should swallow surprises and
    let the rest of the page render. The cost-cluster simply doesn't
    appear; no traceback bleeds into the HTML.
    """
    with patch(
        "attune.ops.anthropic_cost.fetch_summary",
        side_effect=RuntimeError("anthropic edge melted"),
    ):
        with _client(tmp_path, monkeypatch) as client:
            resp = client.get("/")

    assert resp.status_code == 200
    # No tile cluster rendered.
    assert "kpi-cluster-account" not in resp.text
    # No traceback / exception text leaked.
    assert "anthropic edge melted" not in resp.text
    assert "Traceback" not in resp.text
    # Dashboard otherwise functional.
    assert "attune ops" in resp.text  # hero title
