"""Chart spec v1 validation tests — all five types, field-level errors,
and the pydantic/JSON-Schema sync contract.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.widgets.chart_spec import (
    CHART_TYPES,
    ChartSpecError,
    validate_chart_spec,
)

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "src/attune/widgets/chartkit/spec.schema.json"


def _spec(chart_type: str) -> dict:
    spec: dict = {
        "v": 1,
        "type": chart_type,
        "data": [{"x": "a", "y": 1}, {"x": "b", "y": 2}],
        "encodings": {
            "x": {"field": "x", "type": "nominal"},
            "y": {"field": "y", "type": "quantitative"},
        },
    }
    if chart_type == "heatmap":
        spec["encodings"]["color"] = {"field": "y", "type": "quantitative"}
    if chart_type == "box":
        spec["data"] = [
            {"x": "a", "y": 3, "min": 1, "q1": 2, "median": 3, "q3": 4, "max": 5},
            {"x": "b", "y": 8, "min": 4, "q1": 6, "median": 8, "q3": 10, "max": 12},
        ]
    return spec


@pytest.mark.parametrize("chart_type", CHART_TYPES)
def test_valid_spec_per_type(chart_type: str) -> None:
    validated = validate_chart_spec(_spec(chart_type))
    assert validated.type == chart_type
    assert validated.options.legend is True


def test_missing_encoding_reports_field_level_path() -> None:
    spec = _spec("bar")
    del spec["encodings"]["x"]
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any(p.startswith("encodings.x") for p in exc.value.problems)


def test_unknown_type_lists_the_valid_ones() -> None:
    spec = _spec("bar")
    spec["type"] = "pie"
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any("type" in p for p in exc.value.problems)


def test_extra_keys_are_rejected() -> None:
    spec = _spec("line")
    spec["renderer"] = "custom"
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any("renderer" in p for p in exc.value.problems)


def test_empty_data_is_rejected() -> None:
    spec = _spec("bar")
    spec["data"] = []
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any(p.startswith("data") for p in exc.value.problems)


def test_heatmap_requires_color_channel() -> None:
    spec = _spec("heatmap")
    del spec["encodings"]["color"]
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any("color" in p for p in exc.value.problems)


def test_box_rows_require_numeric_summary_stats() -> None:
    spec = _spec("box")
    spec["data"][1]["median"] = "oops"
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any("data.1.median" in p for p in exc.value.problems)


def test_value_charts_require_quantitative_y() -> None:
    for chart_type in ("donut", "waterfall", "treemap"):
        spec = _spec(chart_type)
        spec["encodings"]["y"]["type"] = "nominal"
        with pytest.raises(ChartSpecError) as exc:
            validate_chart_spec(spec)
        assert any("encodings.y.type" in p for p in exc.value.problems)


def test_horizontal_only_valid_for_bar() -> None:
    spec = _spec("line")
    spec["options"] = {"horizontal": True}
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any("options.horizontal" in p for p in exc.value.problems)
    ok = _spec("bar")
    ok["options"] = {"horizontal": True}
    assert validate_chart_spec(ok).options.horizontal is True


def test_total_only_valid_for_waterfall() -> None:
    spec = _spec("donut")
    spec["options"] = {"total": "net"}
    with pytest.raises(ChartSpecError) as exc:
        validate_chart_spec(spec)
    assert any("options.total" in p for p in exc.value.problems)
    ok = _spec("waterfall")
    ok["options"] = {"total": "net"}
    assert validate_chart_spec(ok).options.total == "net"


class TestSchemaSync:
    """The handwritten JSON Schema must agree with the pydantic mirror."""

    def _schema(self) -> dict:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_chart_type_enums_match(self) -> None:
        schema = self._schema()
        assert tuple(schema["properties"]["type"]["enum"]) == CHART_TYPES

    def test_required_top_level_fields_match(self) -> None:
        schema = self._schema()
        assert set(schema["required"]) == {"v", "type", "data", "encodings"}

    def test_encoding_field_types_match(self) -> None:
        schema = self._schema()
        enum = schema["$defs"]["encoding"]["properties"]["type"]["enum"]
        assert set(enum) == {"quantitative", "nominal", "temporal"}
