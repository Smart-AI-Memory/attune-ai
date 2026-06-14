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


def test_home_kpis_default_today_uses_utc_not_local(monkeypatch):
    """Regression: when ``today`` is omitted, the default reference date is
    the UTC date — matching ``by_day``'s UTC keying (``_to_day``) — not local
    ``date.today()``.

    Bug class of #867: a local "today" reads the wrong bucket in the evening
    for non-UTC users (after ~20:00 US-Pacific, UTC is already tomorrow). We
    freeze ``datetime`` to 2026-06-14 06:30 UTC, which is still 2026-06-13
    local in any TZ behind UTC; the UTC bucket (06-14) must win.
    """
    from datetime import datetime as _dt
    from datetime import timezone as _tz

    fixed = _dt(2026, 6, 14, 6, 30, tzinfo=_tz.utc)

    class _FrozenDateTime(_dt):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(data, "datetime", _FrozenDateTime)

    summary = data.TelemetrySummary(
        total_requests=3,
        total_cost=0.30,
        total_savings=0.0,
        by_workflow=[],
        by_day=[("2026-06-14", 3, 0.30)],  # UTC-keyed bucket
        last_event_at=None,
    )
    kpis = data.home_kpis(summary)  # today=None -> exercises the default
    assert kpis.today_events == 3
    assert kpis.today_cost == 0.30
    assert kpis.sparkline[-1].day == "2026-06-14"


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


def test_home_recent_runs_each_cell_links_to_run_view(tmp_path, monkeypatch):
    """Phase B4: every cell in a Recent-runs row is clickable.

    Pre-B4, only the workflow-name and run-id cells had ``<a>``
    wrappers — clicking the status chip, duration, started-at, or
    line-count cells did nothing. Users who tried to "click the
    row" missed unless they hit one of the two link cells.

    Regression guard: each of the SIX cells must wrap its content
    in an ``<a class="row-link" href="/runs/<id>/view">`` so the
    entire row is mouse-clickable. Keyboard nav gets ONE focus
    stop per row (the first link); the rest use ``tabindex="-1"``
    to stay out of tab order while remaining mouse-clickable.
    """
    import re

    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    runner = RunnerService()
    seeded = Run(id="abc12345", workflow="code-review")
    seeded.status = "completed"
    seeded.exit_code = 0
    from datetime import datetime, timezone

    seeded.started_at = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    seeded.completed_at = datetime(2026, 5, 6, 12, 0, 5, tzinfo=timezone.utc)
    seeded.lines = ["line one", "line two"]
    runner._runs[seeded.id] = seeded  # noqa: SLF001

    app = create_app(config, runner=runner)
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text

    # Isolate the seeded run's <tr> — we only want THIS row, not other
    # runs the server might have surfaced. The row carries the
    # ``recent-run-row`` class added in B4.
    row_re = re.compile(
        r'<tr class="recent-run-row">(.*?)</tr>',
        re.DOTALL,
    )
    row_match = row_re.search(body)
    assert row_match is not None, (
        "Recent-runs table doesn't render a row with class "
        "``recent-run-row`` — the B4 click-target class is missing"
    )
    row_html = row_match.group(1)
    # Count <a class="row-link"> openings pointing at the run-view.
    # Attribute order on the rendered tag is template-author-dependent
    # (today: href first, class second), so match the tag opening then
    # check both attributes are present inside it, rather than
    # constraining their order in the regex.
    a_opens = re.findall(r"<a\b[^>]*>", row_html)
    row_links = [
        tag for tag in a_opens if 'class="row-link"' in tag and 'href="/runs/abc12345/view"' in tag
    ]
    assert len(row_links) == 6, (
        f"Expected 6 row-link <a> elements (one per cell) inside the "
        f"seeded run's row; found {len(row_links)}. Cells: workflow, "
        f"run id, status, duration, started, lines."
    )
    # Only the first link is in tab order. The other five carry
    # ``tabindex="-1"`` so keyboard nav doesn't have to stop 6 times
    # per row. This is the keyboard-accessibility part of the design.
    tabindex_neg = [tag for tag in row_links if 'tabindex="-1"' in tag]
    assert len(tabindex_neg) == 5, (
        "Expected 5 of the 6 row-link <a>s to carry tabindex='-1' "
        "(only the first stays in tab order); found a different count"
    )
    # The first cell-link is also the one carrying the descriptive
    # aria-label that screen readers announce for the row.
    assert (
        'aria-label="Open run abc12345 for code-review"' in row_html
    ), "First row-link should carry a descriptive aria-label"


def test_home_recent_runs_css_makes_row_clickable():
    """The CSS hook for B4 (``recent-runs-table tbody td a.row-link``)
    must exist in main.css. The visual cue (``cursor: pointer`` on
    the row) is part of the design promise — without it users don't
    discover the whole-row click target."""
    from pathlib import Path

    css_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "attune"
        / "ops"
        / "static"
        / "css"
        / "main.css"
    )
    text = css_path.read_text(encoding="utf-8")
    # The cursor cue
    assert "tr.recent-run-row" in text
    assert "cursor: pointer" in text
    # The link-styling rule that makes <a> fill the cell
    assert ".recent-runs-table tbody td a.row-link" in text
    assert "display: block" in text
    assert "color: inherit" in text
    assert "text-decoration: none" in text


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


def test_home_kpis_nonzero_when_telemetry_uses_ts_field(tmp_path, monkeypatch):
    """Regression guard for A1: usage.jsonl events use the ``ts`` key
    (v1.0 schema from UsageTracker._format_entry), not ``timestamp``.

    Without the dual-field lookup in read_telemetry_summary, every
    event silently misses by_day bucketing and Home's KPI tiles read
    zero even when the telemetry log is populated.
    """
    home = tmp_path / "attune-home"
    (home / "telemetry").mkdir(parents=True)
    log = home / "telemetry" / "usage.jsonl"
    today = date.today().isoformat()
    # Write with ``ts`` (the real v1.0 schema key), NOT ``timestamp``.
    log.write_text(
        f'{{"workflow": "x", "total_cost": 0.42, "ts": "{today}T10:00:00+00:00"}}\n',
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
    assert "<polyline" in resp.text, (
        "Sparkline polyline absent — ts-field events are being silently "
        "dropped from by_day bucketing (read_telemetry_summary must read "
        "event.get('ts') or event.get('timestamp'), not only 'timestamp')"
    )
    assert "$0.42" in resp.text or "0.4200" in resp.text, (
        "7-day cost shows zero despite a 0.42-cost ts-keyed event in "
        "usage.jsonl — ts-field lookup in read_telemetry_summary regressed"
    )


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
