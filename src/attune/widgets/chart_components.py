"""Named chart components — semantic-role presets that expand to full specs.

The model can invoke a component by name plus data instead of authoring
a spec from scratch; expansion happens server-side and costs zero kernel
bytes. Every expansion is validated through the spec contract before it
leaves this module.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from attune.widgets.chart_spec import ChartSpec, validate_chart_spec


def time_series(
    data: list[dict[str, Any]],
    x_field: str = "date",
    y_field: str = "value",
    series_field: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """A line chart over time — temporal x, quantitative y, optional series."""
    encodings: dict[str, Any] = {
        "x": {"field": x_field, "type": "temporal"},
        "y": {"field": y_field, "type": "quantitative"},
    }
    if series_field:
        encodings["color"] = {"field": series_field, "type": "nominal"}
    spec: dict[str, Any] = {"v": 1, "type": "line", "data": data, "encodings": encodings}
    if title:
        spec["options"] = {"title": title}
    return spec


def comparison_bars(
    data: list[dict[str, Any]],
    category_field: str = "category",
    value_field: str = "value",
    series_field: str | None = None,
    stacked: bool = False,
    title: str | None = None,
) -> dict[str, Any]:
    """Bars comparing categories — optionally split into series."""
    encodings: dict[str, Any] = {
        "x": {"field": category_field, "type": "nominal"},
        "y": {"field": value_field, "type": "quantitative"},
    }
    if series_field:
        encodings["color"] = {"field": series_field, "type": "nominal"}
    options: dict[str, Any] = {}
    if stacked:
        options["stacked"] = True
    if title:
        options["title"] = title
    spec: dict[str, Any] = {"v": 1, "type": "bar", "data": data, "encodings": encodings}
    if options:
        spec["options"] = options
    return spec


def kpi_tile(
    label: str,
    value: float,
    previous: float | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """A KPI as a current-vs-prior comparison bar.

    With ``previous`` the tile reads as change against the prior period;
    without it, a single bar. (A dedicated numeric-tile mark is a kernel
    v2 candidate; this preset stays within spec v1's chart types.)
    """
    data = (
        [
            {"period": "previous", "value": previous},
            {"period": "current", "value": value},
        ]
        if previous is not None
        else [{"period": label, "value": value}]
    )
    return {
        "v": 1,
        "type": "bar",
        "data": data,
        "encodings": {
            "x": {"field": "period", "type": "nominal"},
            "y": {"field": "value", "type": "quantitative"},
        },
        "options": {"title": title or label},
    }


COMPONENTS: dict[str, Callable[..., dict[str, Any]]] = {
    "time_series": time_series,
    "comparison_bars": comparison_bars,
    "kpi_tile": kpi_tile,
}


def expand_component(name: str, args: dict[str, Any]) -> ChartSpec:
    """Expand a named component into a validated ChartSpec.

    Args:
        name: Component name from :data:`COMPONENTS`.
        args: Keyword arguments for the component builder.

    Returns:
        The validated ChartSpec.

    Raises:
        KeyError: Unknown component — the message lists valid names.
        ChartSpecError: The expansion failed spec validation (a component
            bug or impossible arguments); field-level messages included.

    """
    builder = COMPONENTS.get(name)
    if builder is None:
        raise KeyError(f"Unknown component {name!r}. Available: {', '.join(sorted(COMPONENTS))}")
    return validate_chart_spec(builder(**args))
