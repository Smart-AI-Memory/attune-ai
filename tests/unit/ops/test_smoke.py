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
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(config)
    return TestClient(app)


def test_home_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "attune ops" in response.text.lower()
    assert "workflows" in response.text.lower()


@pytest.mark.parametrize(
    "path",
    ["/workflows", "/telemetry", "/health"],
)
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "<html" in response.text.lower()


@pytest.mark.parametrize(
    "path",
    ["/memory", "/releases"],
)
def test_removed_pages_404(client, path):
    """Memory + Releases tabs were removed (family info still on Home)."""
    response = client.get(path)
    assert response.status_code == 404


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
                + '"timestamp": "2026-05-06T11:00:00+00:00"}',
                '{"workflow": "security-audit", "total_cost": 0.50, '
                + '"timestamp": "2026-05-06T12:00:00+00:00"}',
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


# ---------------------------------------------------------------------------
# Phase B3 — release-keyed cache-bust on static asset URLs
# ---------------------------------------------------------------------------


def test_static_assets_have_version_cache_bust(client):
    """Every ``<script src>`` and ``<link rel="stylesheet">`` URL on
    the dashboard carries a ``?v=<attune_version>`` query string.

    Regression guard for the dashboard-iteration problem documented
    in CLAUDE.md: a release that updates a JS file (e.g. adding a
    new export to runner.js) used to blank out for returning users
    because browsers held the old cached copy with no
    ``Cache-Control`` discipline to force a recheck. Version-keyed
    cache-bust solves it: the URL changes on release, the cached
    copy doesn't match, the browser fetches fresh — but stays
    cached BETWEEN releases for snappy navigation.

    The previous CSS rule used ``range(100000, 999999) | random``
    which busted every page render — useful for dev iteration,
    bad for production caching. That random buster is gone too.
    """
    import re

    from attune import __version__ as attune_version

    response = client.get("/workflows")
    assert response.status_code == 200
    body = response.text
    # All four pages share base.html so checking one is enough for
    # CSS; we also want JS specifically (one per page).
    # The random-buster antipattern must not return:
    assert "range(100000" not in body
    # CSS link carries the version
    css_link_re = re.compile(
        r'<link[^>]+rel="stylesheet"[^>]+href="[^"]+/css/main\.css\?v=([^"]+)"'
    )
    css_match = css_link_re.search(body)
    assert (
        css_match is not None
    ), "Expected <link rel=stylesheet> for main.css with ?v= query string"
    assert css_match.group(1) == attune_version
    # JS script tag carries the version (runner.js on the Workflows page)
    js_script_re = re.compile(r'<script[^>]+src="[^"]+/js/runner\.js\?v=([^"]+)"')
    js_match = js_script_re.search(body)
    assert js_match is not None, "Expected runner.js with ?v= query string"
    assert js_match.group(1) == attune_version


def test_specs_page_specs_js_has_version_cache_bust(client):
    """The Specs page's specs.js script tag carries the version too —
    distinct from runner.js since it only loads when allow_run is
    true on the Specs page."""
    import re

    from attune import __version__ as attune_version

    response = client.get("/specs")
    assert response.status_code == 200
    # Only assert if specs.js shows up — read-only mode omits it.
    if "specs.js" in response.text:
        m = re.search(
            r'<script[^>]+src="[^"]+/js/specs\.js\?v=([^"]+)"',
            response.text,
        )
        assert m is not None, "specs.js is referenced but without a ?v= cache-bust"
        assert m.group(1) == attune_version
