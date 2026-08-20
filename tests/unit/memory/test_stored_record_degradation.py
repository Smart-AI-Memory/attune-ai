"""One unreadable stored record must not block every read (I-4).

Library-review I-4: stores parsed and subscripted in different
functions — ``Model.from_dict(json.loads(raw))`` — so a legacy or
hand-edited value raised out of the read that backs promotion, and one
bad key blocked ALL promotions. P15 says the memory layer degrades; it
never blocks.

Every record here is built from the WRITER's own serializer
(``to_dict`` → ``json.dumps``) and then damaged, so the test cannot
drift into asserting a shape the writer never produces — the failure
mode that let class M ("the mock defined the contract") hide I-2.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

import pytest

from attune.memory.types import (
    AccessTier,
    AgentCredentials,
    StagedPattern,
    parse_stored_record,
)


def _written_record() -> str:
    """Exactly what the writer stores — not a hand-written fixture."""
    pattern = StagedPattern(
        pattern_id="p1",
        agent_id="agent-1",
        pattern_type="runbook",
        name="restart the worker",
        description="how to restart",
        confidence=0.9,
        staged_at=datetime(2026, 8, 20, 12, 0, 0),
    )
    return json.dumps(pattern.to_dict())


def test_writer_output_round_trips():
    """The baseline the damaged cases are measured against."""
    parsed = parse_stored_record(StagedPattern, _written_record())

    assert parsed is not None
    assert parsed.pattern_id == "p1"
    assert parsed.pattern_type == "runbook"


@pytest.mark.parametrize(
    ("label", "raw"),
    [
        ("unparseable", "{not json"),
        ("empty", ""),
        ("json list", "[1, 2, 3]"),
        ("json string", '"just a string"'),
        ("json null", "null"),
        ("missing required key", json.dumps({"pattern_id": "p1"})),
        ("unparseable timestamp", json.dumps({**json.loads(_written_record()), "staged_at": "?"})),
        ("out-of-range confidence", json.dumps({**json.loads(_written_record()), "confidence": 9})),
        ("wrong field type", json.dumps({**json.loads(_written_record()), "context": "nope"})),
    ],
)
def test_damaged_records_degrade_to_none(label, raw):
    """Never raises — the caller skips the record and keeps going."""
    assert parse_stored_record(StagedPattern, raw, key=label) is None


# --------------------------------------------------------------------------
# Through the real store, against a real Redis when one is available
# --------------------------------------------------------------------------


#: The suite scrubs REDIS_URL for hermeticity, so the live lane takes
#: its endpoint from here and re-sets it for the store under test.
LIVE_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/0")


@pytest.fixture()
def live_store(monkeypatch):
    """A real RedisShortTermMemory over a real server, own key prefix."""
    redis = pytest.importorskip("redis")
    try:
        redis.Redis.from_url(LIVE_REDIS_URL, socket_connect_timeout=0.5).ping()
    except Exception:  # noqa: BLE001 — any failure means "no server here"
        pytest.skip(f"no reachable Redis at {LIVE_REDIS_URL} for the live read path")

    monkeypatch.setenv("REDIS_URL", LIVE_REDIS_URL)
    from attune.memory.short_term import RedisShortTermMemory

    store = RedisShortTermMemory(use_mock=False)
    if store._client is None:
        pytest.skip("short-term store did not connect")
    written: list[str] = []
    yield store, written
    for key in written:
        store._client.delete(key)


def test_one_poison_key_does_not_block_the_staged_listing(live_store):
    """The promotion-blocking shape, end to end through real Redis."""
    store, written = live_store
    creds = AgentCredentials(agent_id="agent-1", tier=AccessTier.STEWARD)
    marker = uuid.uuid4().hex[:8]

    good = StagedPattern(
        pattern_id=f"good-{marker}",
        agent_id="agent-1",
        pattern_type="runbook",
        name="readable",
        description="d",
    )
    assert store.stage_pattern(good, creds) is True
    written.append(f"{store._patterns.PREFIX_STAGED}{good.pattern_id}")

    # A legacy value written under the same prefix — bytes on the wire,
    # which is how this actually arrives.
    poison_key = f"{store._patterns.PREFIX_STAGED}legacy-{marker}"
    store._client.set(poison_key, json.dumps(["legacy", "list", "shape"]))
    written.append(poison_key)

    listed = store.list_staged_patterns(creds)

    assert good.pattern_id in {p.pattern_id for p in listed}


def test_get_staged_pattern_returns_none_for_an_unreadable_record(live_store):
    """The single-record read degrades rather than raising."""
    store, written = live_store
    creds = AgentCredentials(agent_id="agent-1", tier=AccessTier.STEWARD)
    marker = uuid.uuid4().hex[:8]

    poison_id = f"legacy-{marker}"
    key = f"{store._patterns.PREFIX_STAGED}{poison_id}"
    store._client.set(key, json.dumps(["legacy", "list", "shape"]))
    written.append(key)

    assert store.get_staged_pattern(poison_id, creds) is None
