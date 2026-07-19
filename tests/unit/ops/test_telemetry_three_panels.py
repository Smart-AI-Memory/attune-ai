"""US-6 three-panel receipt tests — reach, freshness, spend TOGETHER.

usage-signals US-6: verification exercises the dashboard through its
REAL file-to-render boundary — representative persisted artifacts on
disk (snapshot JSONs, usage.jsonl), rendered via the actual FastAPI
route + Jinja template — not only mocked helpers.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops import data  # noqa: E402
from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402

PACKAGES = list(data.REACH_PACKAGES)
STATS = {"last_day": 3, "last_week": 21, "last_month": 90}


def _client(tmp_path: Path) -> TestClient:
    config = build_config(project_root=tmp_path, trusted_hosts=("testserver", "test"))
    return TestClient(create_app(config))


def _write_snapshot(
    tmp_path: Path,
    date: str,
    packages: list[str],
    *,
    complete: bool | None = None,
) -> Path:
    """Write a snapshot artifact shaped like scripts/reach_snapshot.py's."""
    snap_dir = tmp_path / "docs" / "specs" / "usage-signals" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    pypi = {pkg: dict(STATS) for pkg in packages}
    missing = [p for p in PACKAGES if p not in packages]
    payload = {
        "date": date,
        "taken_at": f"{date}T12:00:00+00:00",
        "pypi_recent": pypi,
        "github": {},
        "manifest": {
            "expected": PACKAGES,
            "captured": packages,
            "missing": missing,
            "source": "pypistats.org/api/recent",
            "observed_at": f"{date}T12:00:00+00:00",
            "complete": complete if complete is not None else not missing,
        },
    }
    path = snap_dir / f"{date}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_usage(age_hours: float) -> Path:
    """Write a real usage.jsonl under ATTUNE_HOME, aged via mtime."""
    home = Path(os.environ["ATTUNE_HOME"])
    usage = home / "telemetry" / "usage.jsonl"
    usage.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "v": "1.0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": 1,
        "workflow": "code-review",
        "tier": "SDK",
        "model": "agent-sdk",
        "provider": "anthropic",
        "cost": 0.42,
    }
    usage.write_text(json.dumps(event) + "\n", encoding="utf-8")
    stamp = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).timestamp()
    os.utime(usage, (stamp, stamp))
    return usage


class TestReachPanel:
    def test_complete_snapshot_renders_per_package_values(self, tmp_path):
        _write_snapshot(tmp_path, "2026-08-01", PACKAGES)
        _write_usage(age_hours=1)
        html = _client(tmp_path).get("/telemetry").text
        assert "Reach — latest complete snapshot" in html
        assert "2026-08-01" in html
        for pkg in PACKAGES:
            assert pkg in html
        assert html.count(">21<") >= len(PACKAGES)  # last_week per package

    def test_newer_incomplete_labeled_and_does_not_replace_complete(self, tmp_path):
        _write_snapshot(tmp_path, "2026-08-01", PACKAGES)
        _write_snapshot(tmp_path, "2026-08-03", PACKAGES[:2])  # newer, partial
        _write_usage(age_hours=1)
        html = _client(tmp_path).get("/telemetry").text
        # The complete snapshot stays the rendered one…
        assert "Snapshot <code>2026-08-01</code>" in html
        # …and the newer partial is unmistakably labeled, with missing names.
        assert "INCOMPLETE" in html
        assert "2026-08-03" in html
        for pkg in PACKAGES[2:]:
            assert html.count(pkg) >= 2  # complete table + missing list

    def test_no_snapshots_renders_empty_state(self, tmp_path):
        _write_usage(age_hours=1)
        html = _client(tmp_path).get("/telemetry").text
        assert "No complete reach snapshot yet." in html


class TestFreshnessPanel:
    @pytest.mark.parametrize(
        ("age_hours", "stale"),
        [(47.5, False), (48.5, True)],
    )
    def test_flag_changes_at_48_hour_boundary(self, tmp_path, age_hours, stale):
        _write_usage(age_hours=age_hours)
        html = _client(tmp_path).get("/telemetry").text
        assert "Freshness — usage.jsonl last write" in html
        if stale:
            assert "STALE" in html
        else:
            assert "STALE" not in html
            assert "Fresh (under the 48-hour threshold)." in html

    def test_missing_usage_file_reads_stale(self, tmp_path):
        html = _client(tmp_path).get("/telemetry").text
        assert "usage.jsonl not found" in html

    def test_data_layer_boundary_values(self, tmp_path):
        usage = _write_usage(age_hours=10)
        cfg = build_config(project_root=tmp_path)
        assert cfg.telemetry_path == usage
        fresh = data.read_usage_freshness(cfg)
        assert fresh.exists and not fresh.stale
        assert fresh.age_hours == pytest.approx(10.0, abs=0.2)


class TestSpendPanel:
    def test_spend_alarm_renders_with_local_source(self, tmp_path):
        _write_usage(age_hours=1)
        html = _client(tmp_path).get("/telemetry").text
        assert "API spend watch" in html
        assert "local telemetry only" in html  # D13 source honesty line

    def test_three_panels_render_together(self, tmp_path):
        """The US-6 receipt condition: reach + freshness + spend on one page."""
        _write_snapshot(tmp_path, "2026-08-01", PACKAGES)
        _write_usage(age_hours=1)
        html = _client(tmp_path).get("/telemetry").text
        assert "Reach — latest complete snapshot" in html
        assert "Freshness — usage.jsonl last write" in html
        assert "API spend watch" in html
