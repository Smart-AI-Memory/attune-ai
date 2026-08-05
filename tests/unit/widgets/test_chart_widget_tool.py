"""chart_render_widget tests — create/patch round trips, legible
degradation without a backend, and injection-safe HTML.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.widgets.chart_widget_tool import (
    BACKEND_DOWN_MSG,
    merge_patch,
    render_chart_widget,
)


class DictBackend:
    """In-memory stand-in for the session memory backend."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def stash(self, key: str, value: dict, ttl: int | None = None) -> bool:
        self.store[key] = value
        return True

    def retrieve(self, key: str) -> dict | None:
        return self.store.get(key)


def _spec() -> dict:
    return {
        "v": 1,
        "type": "bar",
        "data": [{"m": "Jan", "n": 3}, {"m": "Feb", "n": 5}],
        "encodings": {
            "x": {"field": "m", "type": "nominal"},
            "y": {"field": "n", "type": "quantitative"},
        },
        "options": {"title": "Sales"},
    }


def test_create_returns_kernel_injected_html_and_persists() -> None:
    backend = DictBackend()
    out = render_chart_widget("sales-1", spec=_spec(), backend=backend)
    assert out["success"] is True
    assert "/* chartkit v" in out["html"]
    assert 'id="chartkit-sales-1"' in out["html"]
    assert out["persistence"].startswith("stored")
    assert backend.store["chart:sales-1"]["type"] == "bar"


def test_create_then_patch_then_patch_round_trip() -> None:
    backend = DictBackend()
    render_chart_widget("rt", spec=_spec(), backend=backend)
    out1 = render_chart_widget("rt", patch={"options": {"title": "Q3 sales"}}, backend=backend)
    assert out1["success"] is True
    out2 = render_chart_widget("rt", patch={"data": [{"m": "Mar", "n": 9}]}, backend=backend)
    assert out2["success"] is True
    final = backend.store["chart:rt"]
    assert final["options"]["title"] == "Q3 sales"
    assert final["data"] == [{"m": "Mar", "n": 9}]
    assert final["type"] == "bar"


def test_patch_without_backend_degrades_legibly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from attune.widgets import chart_widget_tool

    monkeypatch.setattr(chart_widget_tool, "_resolve_backend", lambda: None)
    out = render_chart_widget("orphan", patch={"options": {"title": "x"}})
    assert out["success"] is False
    assert out["error"] == BACKEND_DOWN_MSG
    assert "FULL chart spec" in out["error"]


def test_patch_with_expired_spec_names_the_chart() -> None:
    out = render_chart_widget("gone", patch={"options": {"title": "x"}}, backend=DictBackend())
    assert out["success"] is False
    assert "gone" in out["error"]
    assert "FULL chart spec" in out["error"]


def test_invalid_spec_returns_field_level_problems() -> None:
    spec = _spec()
    del spec["encodings"]["y"]
    out = render_chart_widget("bad", spec=spec, backend=DictBackend())
    assert out["success"] is False
    assert any(p.startswith("encodings.y") for p in out["problems"])


def test_hostile_strings_cannot_break_out_of_the_script_tag() -> None:
    spec = _spec()
    spec["options"]["title"] = "</script><script>alert(1)</script>"
    spec["data"] = [{"m": "<img src=x onerror=alert(1)>", "n": 1}]
    out = render_chart_widget("evil", spec=spec, backend=DictBackend())
    assert out["success"] is True
    html = out["html"]
    payload = html.split("ChartKit.render", 1)[1].rsplit("</script>", 1)[0]
    assert "</script" not in payload, "spec strings must not close the script tag"
    assert "\\u003c" in payload


def test_bad_chart_id_is_rejected() -> None:
    out = render_chart_widget("no/slashes here", spec=_spec(), backend=DictBackend())
    assert out["success"] is False
    assert "chart_id" in out["error"]


def test_neither_spec_nor_patch_is_an_error() -> None:
    out = render_chart_widget("empty", backend=DictBackend())
    assert out["success"] is False
    assert "spec" in out["error"] and "patch" in out["error"]


def test_merge_patch_semantics() -> None:
    assert merge_patch({"a": 1, "b": {"c": 2}}, {"b": {"c": None}, "d": 4}) == {
        "a": 1,
        "b": {},
        "d": 4,
    }
    assert merge_patch({"a": 1}, "scalar") == "scalar"


def test_no_stored_spec_type_confusion_is_handled() -> None:
    backend = DictBackend()
    backend.store["chart:odd"] = ["not", "a", "dict"]  # type: ignore[assignment]
    out = render_chart_widget("odd", patch={"options": {}}, backend=backend)
    assert out["success"] is False
    assert "FULL chart spec" in out["error"]


@pytest.mark.parametrize("chart_id", ["a", "A-1_b", "x" * 64])
def test_chart_id_edge_formats_accepted(chart_id: str) -> None:
    out = render_chart_widget(chart_id, spec=_spec(), backend=DictBackend())
    assert out["success"] is True
