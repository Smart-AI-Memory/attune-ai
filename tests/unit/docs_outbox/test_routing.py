# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Mechanical routing table (R2) — no per-case judgment."""

from __future__ import annotations

import pytest

from attune.docs_outbox.routing import MERGE_NOW_KINDS, OUTBOX_TARGETS, route


@pytest.mark.parametrize("kind", sorted(OUTBOX_TARGETS))
def test_small_docs_route_to_outbox(kind):
    assert route(kind) == "outbox"


@pytest.mark.parametrize("kind", sorted(MERGE_NOW_KINDS))
def test_rulings_route_merge_now(kind):
    assert route(kind) == "merge-now"


def test_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown artifact kind"):
        route("mystery")


def test_lesson_default_target_is_canonical_corpus():
    assert OUTBOX_TARGETS["lesson"] == ".claude/lessons.md"
