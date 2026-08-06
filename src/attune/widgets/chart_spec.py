"""Chart spec v1 — the Python mirror of chartkit's spec contract.

This model is authoritative for server-side validation; the JSON
Schema shipped with the kernel (``spec.schema.json``) is the same
contract for JS-side consumers, and a sync test keeps them aligned.
Validation errors are field-level and actionable so a model that
emitted a bad spec can self-correct from the message alone.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

CHART_TYPES = (
    "bar",
    "line",
    "scatter",
    "area",
    "heatmap",
    "donut",
    "box",
    "waterfall",
    "treemap",
)

ChartType = Literal[
    "bar",
    "line",
    "scatter",
    "area",
    "heatmap",
    "donut",
    "box",
    "waterfall",
    "treemap",
]

#: Per-row summary stats a box chart requires (pre-computed by the
#: author — the kernel never bins or aggregates).
BOX_STAT_KEYS = ("min", "q1", "median", "q3", "max")
FieldType = Literal["quantitative", "nominal", "temporal"]


class ChartSpecError(ValueError):
    """Raised when a chart spec fails validation.

    Args:
        problems: One actionable message per failing field.

    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


class Encoding(BaseModel):
    """A field-to-channel mapping (e.g. x -> data column 'month')."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    type: FieldType


class Encodings(BaseModel):
    """Channel mappings for a chart. x and y are always required."""

    model_config = ConfigDict(extra="forbid")

    x: Encoding
    y: Encoding
    color: Encoding | None = None


class Options(BaseModel):
    """Presentation options — all optional, all defaulted."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    legend: bool = True
    stacked: bool = False
    horizontal: bool = False
    total: str | None = None


class ChartSpec(BaseModel):
    """A complete declarative chart: what the model emits, chartkit renders."""

    model_config = ConfigDict(extra="forbid")

    v: Literal[1] = 1
    type: ChartType
    data: list[dict[str, Any]] = Field(min_length=1)
    encodings: Encodings
    options: Options = Field(default_factory=Options)

    @model_validator(mode="after")
    def _heatmap_needs_color(self) -> ChartSpec:
        if self.type == "heatmap" and self.encodings.color is None:
            raise ValueError(
                "encodings.color: required for heatmap "
                "(the color channel carries the cell value)"
            )
        return self

    @model_validator(mode="after")
    def _box_rows_carry_summary_stats(self) -> ChartSpec:
        if self.type != "box":
            return self
        for i, row in enumerate(self.data):
            for key in BOX_STAT_KEYS:
                value = row.get(key)
                if not isinstance(value, int | float) or isinstance(value, bool):
                    raise ValueError(
                        f"data.{i}.{key}: box rows need numeric "
                        f"{', '.join(BOX_STAT_KEYS)} (pre-computed summary "
                        "stats — the kernel never aggregates)"
                    )
        return self

    @model_validator(mode="after")
    def _value_charts_need_quantitative_y(self) -> ChartSpec:
        if self.type in ("donut", "waterfall", "treemap") and self.encodings.y.type != (
            "quantitative"
        ):
            raise ValueError(
                f"encodings.y.type: must be quantitative for {self.type} "
                "(the y channel carries the slice/delta/tile value)"
            )
        return self

    @model_validator(mode="after")
    def _options_match_type(self) -> ChartSpec:
        if self.options.horizontal and self.type != "bar":
            raise ValueError("options.horizontal: only valid for type 'bar'")
        if self.options.total is not None and self.type != "waterfall":
            raise ValueError("options.total: only valid for type 'waterfall'")
        return self


def validate_chart_spec(payload: dict[str, Any]) -> ChartSpec:
    """Validate a raw spec dict into a ChartSpec.

    Args:
        payload: The spec as parsed JSON.

    Returns:
        The validated ChartSpec.

    Raises:
        ChartSpecError: With one field-level message per problem,
            phrased so the emitting model can fix its spec.

    """
    try:
        return ChartSpec.model_validate(payload)
    except ValidationError as exc:
        problems = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"]) or "spec"
            problems.append(f"{loc}: {err['msg']}")
        raise ChartSpecError(problems) from exc
