"""Tests for ground-truth context budget enforcement."""

from __future__ import annotations

import logging

from attune.authoring.ground_truth.budget import enforce_budget


def test_blocks_under_budget_returned_unchanged() -> None:
    blocks = [("cli_help", "small"), ("public_api", "small")]
    result = enforce_budget(blocks, budget_bytes=10_000)
    assert result == blocks


def test_zero_budget_disables_enforcement() -> None:
    blocks = [("cli_help", "x" * 100_000)]
    result = enforce_budget(blocks, budget_bytes=0)
    assert result == blocks


def test_negative_budget_disables_enforcement() -> None:
    blocks = [("cli_help", "x" * 100_000)]
    result = enforce_budget(blocks, budget_bytes=-1)
    assert result == blocks


def test_drop_order_dataclasses_first() -> None:
    blocks = [
        ("cli_help", "x" * 100),
        ("public_api", "x" * 100),
        ("dataclasses", "x" * 100),
    ]
    # Tight budget — at least one drop required.
    result = enforce_budget(blocks, budget_bytes=250)
    remaining_tags = [tag for tag, _body in result]
    assert "dataclasses" not in remaining_tags


def test_drop_order_public_api_second() -> None:
    blocks = [
        ("cli_help", "x" * 100),
        ("public_api", "x" * 100),
        ("dataclasses", "x" * 100),
    ]
    # Very tight budget — two drops required.
    result = enforce_budget(blocks, budget_bytes=130)
    remaining_tags = [tag for tag, _body in result]
    assert "dataclasses" not in remaining_tags
    assert "public_api" not in remaining_tags
    assert "cli_help" in remaining_tags


def test_drop_continues_to_empty_when_required() -> None:
    blocks = [("cli_help", "x" * 1000)]
    result = enforce_budget(blocks, budget_bytes=10)
    assert result == []


def test_logs_warning_on_drop(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="attune.authoring.ground_truth.budget")
    blocks = [
        ("cli_help", "x" * 100),
        ("public_api", "x" * 100),
        ("dataclasses", "x" * 100),
    ]
    enforce_budget(blocks, budget_bytes=250)
    assert any("dropped dataclasses" in record.getMessage() for record in caplog.records)


def test_drop_fallback_when_unknown_tag() -> None:
    blocks = [("unknown_tag", "x" * 1000)]
    result = enforce_budget(blocks, budget_bytes=10)
    assert result == []
