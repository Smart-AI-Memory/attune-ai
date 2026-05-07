"""Smoke tests for `attune.ops` — does the dashboard boot and serve pages?

These tests skip cleanly when the `[ops]` extra is missing so they don't break
the default test matrix.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.server import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient pointed at an isolated attune-home."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(project_root=tmp_path)
    app = create_app(config)
    return TestClient(app)


def test_home_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "attune ops" in response.text.lower()
    assert "workflows registered" in response.text.lower()


@pytest.mark.parametrize(
    "path",
    ["/workflows", "/telemetry", "/memory", "/releases", "/health"],
)
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "<html" in response.text.lower()


def test_info_endpoint(client):
    response = client.get("/api/info")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
    assert "project_root" in payload
    assert "attune_home" in payload


def test_404_uses_template(client):
    response = client.get("/this/does/not/exist")
    assert response.status_code == 404
    assert "404" in response.text
    assert "back to home" in response.text.lower()


def test_static_css_served(client):
    response = client.get("/static/css/main.css")
    assert response.status_code == 200
    assert "kpi" in response.text  # one of our class selectors


def test_telemetry_handles_missing_log(client):
    """Reading a non-existent usage.jsonl must not raise."""
    response = client.get("/telemetry")
    assert response.status_code == 200
    # Empty state copy is rendered.
    assert "no telemetry events" in response.text.lower()


def test_telemetry_aggregates_jsonl(tmp_path, monkeypatch):
    """A simple JSONL log aggregates correctly."""
    home = tmp_path / "attune-home"
    (home / "telemetry").mkdir(parents=True)
    log = home / "telemetry" / "usage.jsonl"
    log.write_text(
        "\n".join(
            [
                '{"workflow": "code-review", "total_cost": 0.12, "savings": 0.05, "timestamp": "2026-05-06T10:00:00+00:00"}',
                '{"workflow": "code-review", "total_cost": 0.08, '
                '"timestamp": "2026-05-06T11:00:00+00:00"}',
                '{"workflow": "security-audit", "total_cost": 0.50, '
                '"timestamp": "2026-05-06T12:00:00+00:00"}',
                "",
                "not-json-line",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ATTUNE_HOME", str(home))
    config = build_config(project_root=tmp_path)

    from attune.ops import data

    summary = data.read_telemetry_summary(config)
    assert summary.total_requests == 3
    assert round(summary.total_cost, 2) == 0.70
    assert round(summary.total_savings, 2) == 0.05
    workflows = {row[0]: row[1] for row in summary.by_workflow}
    assert workflows == {"code-review": 2, "security-audit": 1}


def test_family_versions_at_least_attune_ai():
    """The family list always includes attune-ai (it's the package we're in)."""
    from attune.ops import data

    versions = data.family_versions()
    names = {v.package for v in versions}
    assert "attune-ai" in names
