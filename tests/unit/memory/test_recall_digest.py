"""Tests for the recall-digest render (curated-memory R3).

The transform (nodes → report-style progress form → widget HTML) is
pure and tested without Redis. The fetch path is tested against a REAL
Redis with the ``recall_digest`` function loaded when one is reachable
(the R5 non-mocked receipt), and skipped otherwise — no mocks either way.
"""

from __future__ import annotations

import pytest

from attune.elicitation import collect_form_response, form_from_dict, form_to_widget_html
from attune.memory.recall_digest import (
    DETAIL_MAX,
    digest_form_dict,
    fetch_digest_nodes,
    render_digest_html,
)

NODES = [
    {
        "name": "Memory architecture",
        "type": "project_context",
        "description": "git long-term, Redis short-term, widget recall.",
        "updated_at": "2026-07-02T10:05:08",
        "id": "project_context_1",
    },
    {
        "name": "Goal framing",
        "type": "user_context",
        "description": "x " * 200,  # forces truncation
        "updated_at": "2026-07-02T10:05:08",
        "id": "user_context_1",
    },
]


def _real_redis_or_skip():
    """Return a client connected to a Redis carrying recall_digest, or skip."""
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("no reachable Redis on localhost:6379")
    try:
        client.fcall("recall_digest", 0, "1")
    except redis.ResponseError:
        pytest.skip("recall_digest function not loaded (hydration hook has not run)")
    return client


class TestDigestFormDict:
    def test_builds_valid_report_form(self) -> None:
        form = form_from_dict(digest_form_dict(NODES))
        q = form.questions[0]
        assert q.progress_style == "report"
        assert q.required is False
        assert q.options == ["Memory architecture", "Goal framing"]

    def test_node_type_becomes_readable_tag(self) -> None:
        items = digest_form_dict(NODES)["fields"][0]["progress_items"]
        assert items[0]["status"] == "project context"

    def test_detail_truncated(self) -> None:
        items = digest_form_dict(NODES)["fields"][0]["progress_items"]
        assert len(items[1]["detail"]) <= DETAIL_MAX
        assert items[1]["detail"].endswith("…")

    def test_renders_and_round_trips(self) -> None:
        form = form_from_dict(digest_form_dict(NODES))
        html = form_to_widget_html(form)
        assert "Memory digest" in html
        assert "Pick one to go deeper:" in html
        resp = collect_form_response(form, {"memory_digest": "Goal framing"})
        assert resp.responses == {"memory_digest": "Goal framing"}

    def test_unnamed_node_falls_back_to_id(self) -> None:
        form_dict = digest_form_dict([{"id": "n1", "type": "reference", "description": "d"}])
        assert form_dict["fields"][0]["options"] == ["n1"]


class TestFetchAgainstRealRedis:
    """Non-mocked receipt: exercised only where the real function is warm."""

    def test_fetch_returns_nodes(self) -> None:
        client = _real_redis_or_skip()
        nodes = fetch_digest_nodes(count=3, client=client)
        assert nodes, "warm Redis returned an empty digest"
        assert all("name" in n and "type" in n for n in nodes)

    def test_render_digest_html_end_to_end(self) -> None:
        client = _real_redis_or_skip()
        html = render_digest_html(count=3, client=client)
        assert "Pick one to go deeper:" in html
        assert 'data-ftype="progress"' in html
