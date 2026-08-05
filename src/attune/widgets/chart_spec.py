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

CHART_TYPES = ("bar", "line", "scatter", "area", "heatmap")

ChartType = Literal["bar", "line", "scatter", "area", "heatmap"]
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
