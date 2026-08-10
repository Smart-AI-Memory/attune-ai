"""Tests for the recall-digest render (curated-memory R3).

The transform (nodes → report-style progress form → widget HTML) is
pure and tested without Redis. The fetch path is tested two ways: the
parse/render logic against a fake client injected at the network
boundary (runs everywhere, incl. keyless CI), and end-to-end against a
REAL Redis with the ``recall_digest`` function loaded when one is
reachable (the R5 non-mocked receipt), skipped otherwise.
"""

from __future__ import annotations

import json

import pytest

from attune.elicitation import collect_form_response, form_from_dict, form_to_widget_html
from attune.memory import recall_digest as recall_digest_mod
from attune.memory.recall_digest import (
    DETAIL_MAX,
    digest_form_dict,
    fetch_digest_nodes,
    main,
    render_digest_html,
)


class FakeRedisClient:
    """Client double at the network boundary — fcall returns canned entries."""

    def __init__(self, entries: list) -> None:
        self.entries = entries
        self.calls: list[tuple] = []

    def fcall(self, name, numkeys, count):
        self.calls.append((name, numkeys, count))
        return self.entries


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
        description_part = items[1]["detail"].split("  ⟨")[0]
        assert len(description_part) <= DETAIL_MAX
        assert description_part.endswith("…")

    def test_age_label_appended_from_updated_at(self) -> None:
        """R2 (memory-status-integrity): the digest is a recall surface and
        must carry the epistemic STATUS label (P2 task 8: a calibrated tier,
        not a bare day-count). Label only — order untouched."""
        items = digest_form_dict(NODES)["fields"][0]["progress_items"]
        assert all("unverified⟩" in item["detail"] for item in items)
        assert all(
            any(tier in item["detail"] for tier in ("settled", "check-before-acting", "suspect"))
            for item in items
        )
        # D1: labelling must not reorder — fixture order preserved.
        assert [item["label"] for item in items] == ["Memory architecture", "Goal framing"]

    def test_missing_updated_at_yields_no_label_and_no_crash(self) -> None:
        form_dict = digest_form_dict([{"id": "n1", "type": "reference", "description": "d"}])
        detail = form_dict["fields"][0]["progress_items"][0]["detail"]
        assert "unverified" not in detail

    def test_malformed_updated_at_yields_no_label(self) -> None:
        form_dict = digest_form_dict(
            [{"id": "n1", "type": "reference", "description": "d", "updated_at": "not-a-date"}]
        )
        assert "unverified" not in form_dict["fields"][0]["progress_items"][0]["detail"]

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


class TestFetchWithFakeClient:
    """Parse/render logic against a boundary double — runs in keyless CI."""

    def test_parses_str_and_bytes_entries(self) -> None:
        entries = [json.dumps(NODES[0]), json.dumps(NODES[1]).encode("utf-8")]
        client = FakeRedisClient(entries)
        nodes = fetch_digest_nodes(count=2, client=client)
        assert [n["name"] for n in nodes] == ["Memory architecture", "Goal framing"]
        assert client.calls == [("recall_digest", 0, "2")]

    def test_malformed_entry_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="malformed JSON"):
            fetch_digest_nodes(client=FakeRedisClient(["{not json"]))

    def test_empty_reply_yields_no_nodes(self) -> None:
        assert fetch_digest_nodes(client=FakeRedisClient([])) == []

    def test_default_client_built_from_redis_url(self, monkeypatch) -> None:
        redis = pytest.importorskip("redis")
        captured = {}

        def fake_from_url(url, **kwargs):
            captured["url"] = url
            return FakeRedisClient([json.dumps(NODES[0])])

        monkeypatch.setenv("REDIS_URL", "redis://example.invalid:6390/2")
        # Hermetic against ambient dotenv REDIS_PASSWORD — the resolver
        # (rct-4) would merge it into the URL.
        for var in ("REDIS_PRIVATE_URL", "REDIS_PUBLIC_URL", "REDIS_PASSWORD", "REDIS_USER"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(redis.Redis, "from_url", fake_from_url)
        nodes = fetch_digest_nodes(count=1)
        assert captured["url"] == "redis://example.invalid:6390/2"
        assert nodes[0]["name"] == "Memory architecture"

    def test_render_digest_html_via_fake_client(self) -> None:
        html = render_digest_html(count=2, client=FakeRedisClient([json.dumps(NODES[0])]))
        assert "Pick one to go deeper:" in html
        assert "Memory architecture" in html

    def test_render_empty_digest_raises(self) -> None:
        with pytest.raises(ValueError, match="returned no nodes"):
            render_digest_html(client=FakeRedisClient([]))


class TestMain:
    def test_main_prints_widget_html(self, monkeypatch, capsys) -> None:
        monkeypatch.setattr(
            recall_digest_mod, "render_digest_html", lambda count: f"<form>{count}</form>"
        )
        assert main(["--count", "4"]) == 0
        assert capsys.readouterr().out.strip() == "<form>4</form>"
