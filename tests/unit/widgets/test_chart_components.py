"""Component preset tests — every expansion is schema-valid, and every
full-spec example in the chartkit docs validates against the contract.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from attune.widgets.chart_components import COMPONENTS, expand_component
from attune.widgets.chart_spec import validate_chart_spec

DOCS_PATH = Path(__file__).resolve().parents[3] / "docs/chartkit.md"

SAMPLE_ARGS: dict[str, dict] = {
    "time_series": {
        "data": [
            {"date": "2026-07-01", "value": 3, "env": "prod"},
            {"date": "2026-07-02", "value": 5, "env": "prod"},
            {"date": "2026-07-01", "value": 1, "env": "staging"},
        ],
        "series_field": "env",
        "title": "Deploys per day",
    },
    "comparison_bars": {
        "data": [
            {"category": "north", "value": 12, "quarter": "Q1"},
            {"category": "north", "value": 15, "quarter": "Q2"},
            {"category": "south", "value": 9, "quarter": "Q1"},
        ],
        "series_field": "quarter",
        "stacked": True,
        "title": "Revenue by region",
    },
    "kpi_tile": {"label": "MRR", "value": 4200.0, "previous": 3900.0},
}


@pytest.mark.parametrize("name", sorted(COMPONENTS))
def test_every_preset_expands_to_a_schema_valid_spec(name: str) -> None:
    validated = expand_component(name, SAMPLE_ARGS[name])
    assert validated.v == 1
    assert validated.type in {"bar", "line"}


def test_sample_args_cover_every_registered_component() -> None:
    assert set(SAMPLE_ARGS) == set(COMPONENTS)


def test_kpi_tile_without_previous_is_a_single_bar() -> None:
    validated = expand_component("kpi_tile", {"label": "Users", "value": 87})
    assert len(validated.data) == 1
    assert validated.options.title == "Users"


def test_unknown_component_lists_the_valid_names() -> None:
    with pytest.raises(KeyError) as exc:
        expand_component("sparkline", {})
    for name in COMPONENTS:
        assert name in str(exc.value)


def test_docs_full_spec_examples_validate() -> None:
    text = DOCS_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
    specs = [json.loads(b) for b in blocks]
    full_specs = [s for s in specs if isinstance(s, dict) and "type" in s]
    assert full_specs, "docs must contain at least one full-spec example"
    for spec in full_specs:
        validate_chart_spec(spec)
