"""Tests for the home-page polish: KPI accessor, sparkline helper, recent-runs."""

from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops import data  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.runner import Run, RunnerService  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


def _empty_summary() -> data.TelemetrySummary:
    return data.TelemetrySummary(0, 0.0, 0.0, [], [], None)


def test_home_kpis_with_empty_summary_returns_seven_zero_days():
    kpis = data.home_kpis(_empty_summary(), today=date(2026, 5, 6))
    assert kpis.today_events == 0
    assert kpis.today_cost == 0.0
    assert kpis.seven_day_cost == 0.0
    assert len(kpis.sparkline) == 7
    assert kpis.sparkline[0].day == "2026-04-30"
    assert kpis.sparkline[-1].day == "2026-05-06"
    assert all(d.cost == 0.0 for d in kpis.sparkline)


def test_home_kpis_zero_fills_missing_days():
    """Days without telemetry rows must still appear at zero."""
    summary = data.TelemetrySummary(
        total_requests=2,
        total_cost=0.30,
        total_savings=0.10,
        by_workflow=[],
        by_day=[("2026-05-04", 1, 0.10), ("2026-05-06", 1, 0.20)],
        last_event_at=None,
    )
    kpis = data.home_kpis(summary, today=date(2026, 5, 6))
    assert kpis.today_events == 1
    assert kpis.today_cost == 0.20
    assert kpis.seven_day_cost == pytest.approx(0.30)
    days = [d.day for d in kpis.sparkline]
    assert days == [
        "2026-04-30",
        "2026-05-01",
        "2026-05-02",
        "2026-05-03",
        "2026-05-04",
        "2026-05-05",
        "2026-05-06",
    ]
    costs = {d.day: d.cost for d in kpis.sparkline}
    assert costs["2026-05-04"] == 0.10
    assert costs["2026-05-06"] == 0.20
    assert costs["2026-05-05"] == 0.0


def test_sparkline_points_returns_normalized_polyline():
    points = data.sparkline_points([0, 1, 2, 1, 4, 0, 0])
    coords = [tuple(map(float, p.split(","))) for p in points.split(" ")]
    # 7 entries, x spans width=240
    assert len(coords) == 7
    assert coords[0][0] == 0.0
    assert coords[-1][0] == pytest.approx(240.0)
    # Highest value (4) → y=0 (top); zero → y=40 (bottom)
    ys = [c[1] for c in coords]
    assert min(ys) == 0.0
    assert max(ys) == 40.0


def test_sparkline_points_empty_for_all_zero():
    assert data.sparkline_points([0, 0, 0, 0]) == ""
    assert data.sparkline_points([]) == ""


def test_home_renders_with_runner_recent_runs(tmp_path, monkeypatch):
    """Home page lists runs from the in-memory runner."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService()
    # Seed a completed run via the internal mapping (avoids subprocess)
    seeded = Run(id="abc123", workflow="code-review")
    seeded.status = "completed"
    seeded.exit_code = 0
    from datetime import datetime, timezone

    seeded.started_at = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    seeded.completed_at = datetime(2026, 5, 6, 12, 0, 5, tzinfo=timezone.utc)
    seeded.lines = ["line one", "line two"]
    runner._runs[seeded.id] = seeded  # noqa: SLF001 — test-only seeding

    app = create_app(config, runner=runner)
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "Recent runs" in resp.text
    assert "code-review" in resp.text
    assert "completed" in resp.text


def test_home_shows_empty_state_when_no_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(config)
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "No runs yet this session" in resp.text


def test_home_renders_sparkline_svg_when_costs_present(tmp_path, monkeypatch):
    """SVG with polyline points appears when at least one day has cost."""
    home = tmp_path / "attune-home"
    (home / "telemetry").mkdir(parents=True)
    log = home / "telemetry" / "usage.jsonl"
    today = date.today().isoformat()
    log.write_text(
        f'{{"workflow": "x", "total_cost": 0.42, "timestamp": "{today}T10:00:00+00:00"}}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("ATTUNE_HOME", str(home))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(config)
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "<polyline" in resp.text
    assert "$0.42" in resp.text or "0.4200" in resp.text


def test_home_renders_attune_ai_version_tile(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(config)
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    # Either we resolve a version (installed) or fall back to em-dash
    assert "attune-ai" in resp.text
