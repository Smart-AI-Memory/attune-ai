"""Tests for the in-memory UI interaction counters (Phase 6.1)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jinja2")

from fastapi.testclient import TestClient  # noqa: E402

from attune.ops.config import build_config  # noqa: E402
from attune.ops.interaction_counters import (  # noqa: E402
    EVENTS,
    InteractionCounters,
    _normalize_target,
)
from attune.ops.server import create_app  # noqa: E402

# ---------------------------------------------------------------
# Pure-Python counter store tests
# ---------------------------------------------------------------


def test_normalize_target_accepts_workflow_name_shape():
    assert _normalize_target("security-audit") == "security-audit"
    assert _normalize_target("code-review") == "code-review"
    assert _normalize_target("next-workflow") == "next-workflow"
    assert _normalize_target("a/b/c.py") == "a/b/c.py"


def test_normalize_target_rejects_html_collapses_to_unknown():
    assert _normalize_target("<script>x</script>") == "(unknown)"
    assert _normalize_target("name with space") == "(unknown)"
    assert _normalize_target("name;rm -rf") == "(unknown)"
    assert _normalize_target("") == "(unknown)"
    assert _normalize_target(None) == "(unknown)"


def test_normalize_target_caps_length_at_64_chars():
    # 64 char ok; 65 char rejected
    long_ok = "a" * 64
    long_no = "a" * 65
    assert _normalize_target(long_ok) == long_ok
    assert _normalize_target(long_no) == "(unknown)"


def test_record_known_event_returns_true_and_increments():
    counters = InteractionCounters()
    assert counters.record("pill_click", "security-audit") is True
    assert counters.record("pill_click", "security-audit") is True
    assert counters.record("pill_click", "code-review") is True
    snap = counters.snapshot()
    assert snap["pill_clicks"] == {"security-audit": 2, "code-review": 1}


def test_record_unknown_event_returns_false_and_is_a_noop():
    counters = InteractionCounters()
    assert counters.record("bogus_event", "anything") is False
    assert counters.totals() == {
        "pill_clicks": 0,
        "rec_card_clicks": 0,
        "scope_picker_changes": 0,
    }


def test_record_each_event_kind_lands_in_its_bucket():
    counters = InteractionCounters()
    counters.record("pill_click", "a")
    counters.record("rec_card_click", "next-workflow")
    counters.record("scope_picker_change", "b")
    snap = counters.snapshot()
    assert snap["pill_clicks"] == {"a": 1}
    assert snap["rec_card_clicks"] == {"next-workflow": 1}
    assert snap["scope_picker_changes"] == {"b": 1}


def test_totals_sums_across_targets_per_bucket():
    counters = InteractionCounters()
    for name in ("a", "a", "b"):
        counters.record("pill_click", name)
    counters.record("rec_card_click", "next-workflow")
    assert counters.totals() == {
        "pill_clicks": 3,
        "rec_card_clicks": 1,
        "scope_picker_changes": 0,
    }


def test_top_returns_most_common_targets_descending():
    counters = InteractionCounters()
    for name in ("a", "a", "a", "b", "b", "c"):
        counters.record("pill_click", name)
    top = counters.top("pill_click", limit=2)
    assert top == [("a", 3), ("b", 2)]


def test_top_returns_empty_for_unknown_event():
    counters = InteractionCounters()
    assert counters.top("bogus", limit=5) == []


def test_record_does_not_raise_on_garbage_target_types():
    """Non-string targets bucket as ``(unknown)`` rather than raising."""
    counters = InteractionCounters()
    # mypy would catch this in real callers; the API takes str | None
    # but defends against runtime garbage anyway.
    assert counters.record("pill_click", 123) is True  # type: ignore[arg-type]
    assert counters.record("pill_click", ["a", "b"]) is True  # type: ignore[arg-type]
    snap = counters.snapshot()
    # Both calls bucketed under "(unknown)" — count is 2.
    assert snap["pill_clicks"] == {"(unknown)": 2}


def test_events_constant_lists_supported_events():
    assert "pill_click" in EVENTS
    assert "rec_card_click" in EVENTS
    assert "scope_picker_change" in EVENTS


# ---------------------------------------------------------------
# HTTP API tests
# ---------------------------------------------------------------


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    config = build_config(
        project_root=tmp_path,
        trusted_hosts=("testserver", "test"),
    )
    app = create_app(config)
    return TestClient(app)


def test_get_interactions_empty_snapshot(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.get("/api/telemetry/interactions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"] == {
        "pill_clicks": 0,
        "rec_card_clicks": 0,
        "scope_picker_changes": 0,
    }
    assert body["pill_clicks"] == {}
    assert body["rec_card_clicks"] == {}
    assert body["scope_picker_changes"] == {}


def test_post_interaction_returns_204_and_increments(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/telemetry/interaction",
        json={"event": "pill_click", "target": "security-audit"},
    )
    assert resp.status_code == 204
    assert resp.content == b""

    body = client.get("/api/telemetry/interactions").json()
    assert body["pill_clicks"] == {"security-audit": 1}
    assert body["totals"]["pill_clicks"] == 1


def test_post_interaction_unknown_event_still_returns_204(tmp_path, monkeypatch):
    """Resilience: stale clients must not see a 4xx for new events."""
    client = _client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/telemetry/interaction",
        json={"event": "future_event_kind", "target": "x"},
    )
    assert resp.status_code == 204
    # No bucket was incremented.
    body = client.get("/api/telemetry/interactions").json()
    assert body["totals"] == {
        "pill_clicks": 0,
        "rec_card_clicks": 0,
        "scope_picker_changes": 0,
    }


def test_post_interaction_html_target_buckets_as_unknown(tmp_path, monkeypatch):
    """XSS-like targets are normalized; never lands in HTML un-escaped."""
    client = _client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/telemetry/interaction",
        json={"event": "pill_click", "target": "<script>alert(1)</script>"},
    )
    assert resp.status_code == 204
    body = client.get("/api/telemetry/interactions").json()
    assert body["pill_clicks"] == {"(unknown)": 1}


def test_post_interaction_missing_target_buckets_as_unknown(tmp_path, monkeypatch):
    """``target`` is optional; missing it buckets as ``(unknown)``."""
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/telemetry/interaction", json={"event": "rec_card_click"})
    assert resp.status_code == 204
    body = client.get("/api/telemetry/interactions").json()
    assert body["rec_card_clicks"] == {"(unknown)": 1}


def test_post_interaction_missing_event_returns_422(tmp_path, monkeypatch):
    """Missing required field: pydantic catches it (422)."""
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/telemetry/interaction", json={"target": "x"})
    assert resp.status_code == 422


def test_telemetry_page_renders_interaction_section_when_empty(tmp_path, monkeypatch):
    """Telemetry page always renders the section header, even when
    no events have been recorded — empty-state message appears."""
    client = _client(tmp_path, monkeypatch)
    resp = client.get("/telemetry")
    assert resp.status_code == 200
    assert "Dashboard interactions" in resp.text
    assert "No dashboard interactions recorded yet" in resp.text


def test_telemetry_page_renders_top_tables_after_events(tmp_path, monkeypatch):
    """After events land, the top-N tables surface in the rendered HTML."""
    client = _client(tmp_path, monkeypatch)
    for target in ("security-audit", "security-audit", "code-review"):
        client.post(
            "/api/telemetry/interaction",
            json={"event": "pill_click", "target": target},
        )
    client.post(
        "/api/telemetry/interaction",
        json={"event": "scope_picker_change", "target": "code-review"},
    )

    html = client.get("/telemetry").text
    assert "Top pills clicked" in html
    assert "Scope picker changes by workflow" in html
    # The KPI tile should show the totals (3 pill clicks, 1 scope change).
    # ``{:,}`` formatting renders 3 as "3" so a simple substring check
    # is enough.
    assert "security-audit" in html
    assert "code-review" in html


def test_telemetry_page_escapes_unknown_targets(tmp_path, monkeypatch):
    """The ``(unknown)`` sentinel renders literally — no script tag
    bleed-through even if a malicious target was posted."""
    client = _client(tmp_path, monkeypatch)
    client.post(
        "/api/telemetry/interaction",
        json={"event": "pill_click", "target": "<script>alert(1)</script>"},
    )
    html = client.get("/telemetry").text
    assert "(unknown)" in html
    # The escaped form must NOT appear as a live tag.
    assert "<script>alert(1)</script>" not in html


def test_counters_persist_across_requests_on_same_app(tmp_path, monkeypatch):
    """Counters are process-lifetime — multiple requests against the
    same app instance accumulate, not reset."""
    client = _client(tmp_path, monkeypatch)
    for _ in range(5):
        client.post(
            "/api/telemetry/interaction",
            json={"event": "pill_click", "target": "security-audit"},
        )
    body = client.get("/api/telemetry/interactions").json()
    assert body["totals"]["pill_clicks"] == 5


def test_counters_lazy_attach_when_app_state_missing():
    """Defensive shim: if an app was constructed without the counter
    pre-attached (e.g. a custom test fixture or pre-Phase-6.1 app
    instance), the route's ``_counters()`` helper lazily attaches a
    fresh ``InteractionCounters`` so the endpoint never 500s.

    Exercises lines 55-57 of ``routes/interaction_counters.py`` —
    the ``app.state.interaction_counters is None`` branch — which
    ``create_app()`` skips because it wires the counter upfront.
    """
    from fastapi import FastAPI

    from attune.ops.routes import interaction_counters as routes_mod

    # Bare app — NO ``create_app``, NO ``app.state.interaction_counters``
    # set. This is the exact pre-condition the defensive shim guards
    # against.
    app = FastAPI()
    app.include_router(routes_mod.router)

    assert not hasattr(app.state, "interaction_counters")

    client = TestClient(app)
    resp = client.post(
        "/api/telemetry/interaction",
        json={"event": "pill_click", "target": "security-audit"},
    )
    assert resp.status_code == 204

    # The shim should have populated ``app.state.interaction_counters``
    # AND the record should have landed.
    assert isinstance(app.state.interaction_counters, InteractionCounters)
    snapshot = app.state.interaction_counters.snapshot()
    assert snapshot["pill_clicks"] == {"security-audit": 1}

    # Second request reuses the lazily-attached counters; not a fresh one.
    client.post(
        "/api/telemetry/interaction",
        json={"event": "pill_click", "target": "security-audit"},
    )
    snapshot = app.state.interaction_counters.snapshot()
    assert snapshot["pill_clicks"] == {"security-audit": 2}


def test_record_interaction_helper_exported_from_runner_js():
    """Drift guard: the JS helper must remain on the
    ``window.__attuneRunner`` export so run_view.js can find it."""
    from pathlib import Path

    js = Path(__file__).parents[3] / "src/attune/ops/static/js/runner.js"
    text = js.read_text(encoding="utf-8")
    assert "recordInteraction: recordInteraction" in text
    assert "function recordInteraction(" in text
