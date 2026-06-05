"""Tests for the curator prompt assembler and output schema (Task 2.1)."""

from __future__ import annotations

from attune.curator.prompt import (
    _MAX_ROWS_PER_SOURCE,
    build_curator_prompt,
)
from attune.curator.result import SourceItem, SourceSummary
from attune.curator.schema import output_schema


def _summary(source_id: str, n: int) -> SourceSummary:
    items = [
        SourceItem(
            item_id=f"{source_id}:{i}",
            title=f"title {i}",
            detail=f"detail {i}",
            link=f"/x/{i}",
            metadata={"bucket": "queue"},
        )
        for i in range(n)
    ]
    return SourceSummary(source_id=source_id, state_hash="h", items=items)


def test_empty_summaries_produce_valid_prompt():
    prompt = build_curator_prompt([], max_items=5)
    assert "(no sources available)" in prompt
    assert "emit_curation" in prompt


def test_block_renders_item_fields():
    prompt = build_curator_prompt([_summary("specs", 1)], max_items=5)
    assert '<source name="specs">' in prompt
    assert "[specs:0] title 0 | /x/0" in prompt
    assert "detail 0" in prompt
    assert "bucket=queue" in prompt


def test_per_source_truncation_marker():
    over = _MAX_ROWS_PER_SOURCE + 5
    prompt = build_curator_prompt([_summary("sweep", over)], max_items=5)
    # Only the first _MAX_ROWS_PER_SOURCE items render; the rest collapse.
    assert f"sweep:{_MAX_ROWS_PER_SOURCE - 1}" in prompt
    assert f"sweep:{_MAX_ROWS_PER_SOURCE}" not in prompt
    assert "...5 more" in prompt


def test_empty_source_block_renders_placeholder():
    prompt = build_curator_prompt([_summary("telemetry", 0)], max_items=5)
    assert '<source name="telemetry">' in prompt
    assert "(no items)" in prompt


def test_max_items_communicated_in_prompt():
    prompt = build_curator_prompt([_summary("specs", 1)], max_items=3)
    assert "at most 3 items" in prompt


def test_output_schema_sets_max_items():
    schema = output_schema(5)
    assert schema["properties"]["items"]["maxItems"] == 5


def test_output_schema_floor_is_one():
    schema = output_schema(0)
    assert schema["properties"]["items"]["maxItems"] == 1


def test_output_schema_returns_copy():
    a = output_schema(2)
    a["properties"]["items"]["maxItems"] = 999
    b = output_schema(4)
    assert b["properties"]["items"]["maxItems"] == 4  # not mutated by a
