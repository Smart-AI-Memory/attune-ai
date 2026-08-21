"""One badly-typed field must not cost the whole file (class G2).

These readers skip malformed JSON per record. That is a promise: a bad
line is skipped, the rest survive. Well-formed JSON carrying a
badly-typed field used to break the promise — the guard catches
``JSONDecodeError`` while ``int("abc")`` raises ``ValueError``, which
sails past it and out of the function, taking every good record with it.

Real files on disk, real reads — no patched parsers. The defect is about
what a coercion does to a value that actually came off disk, so a mocked
loader could not see it (class-M ruling).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.ops.data import _as_float, _as_int, read_memory_summary


def _write(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(r) + "\n" for r in records),
        encoding="utf-8",
    )
    return path


def test_bad_token_field_does_not_lose_the_good_records(tmp_path: Path) -> None:
    """The middle record is poison; the outer two must still be counted."""
    path = _write(
        tmp_path / "memory_events.jsonl",
        [
            {"event": "recall", "est_tokens": 10, "ts": "2026-08-21T00:00:00Z"},
            {"event": "recall", "est_tokens": "abc", "ts": "2026-08-21T00:00:00Z"},
            {"event": "recall", "est_tokens": 20, "ts": "2026-08-21T00:00:00Z"},
        ],
    )

    summary = read_memory_summary(path)

    assert summary["total_events"] == 3, "a badly-typed field dropped whole records"
    assert summary["total_est_tokens"] == 30, (
        "the poison record must contribute 0, not corrupt the sum "
        f"(got {summary['total_est_tokens']})"
    )


def test_malformed_json_line_is_still_skipped(tmp_path: Path) -> None:
    """The original per-record promise still holds."""
    path = tmp_path / "memory_events.jsonl"
    path.write_text(
        json.dumps({"event": "recall", "est_tokens": 5, "ts": "2026-08-21T00:00:00Z"})
        + "\n{ this is not json\n"
        + json.dumps({"event": "recall", "est_tokens": 7, "ts": "2026-08-21T00:00:00Z"})
        + "\n",
        encoding="utf-8",
    )

    summary = read_memory_summary(path)
    assert summary["total_events"] == 2
    assert summary["total_est_tokens"] == 12


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("abc", 0),
        (None, 0),
        ("", 0),
        ([], 0),
        ({}, 0),
        ("12", 12),
        (12, 12),
        (12.9, 12),
        (True, 1),
    ],
)
def test_as_int_is_total(value: object, expected: int) -> None:
    """_as_int must return for every input, never raise."""
    assert _as_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("abc", 0.0), (None, 0.0), ("", 0.0), ([], 0.0), ("1.5", 1.5), (2, 2.0)],
)
def test_as_float_is_total(value: object, expected: float) -> None:
    assert _as_float(value) == pytest.approx(expected)


def test_total_coercions_honour_an_explicit_default() -> None:
    assert _as_int("abc", default=-1) == -1
    assert _as_float("abc", default=-1.0) == pytest.approx(-1.0)
