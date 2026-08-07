"""Recall-digest render — memory's "here is what I carry" surface.

Pulls the curated-memory digest from Redis (``FCALL recall_digest``, the
data the SessionStart hydration hook keeps warm) and renders it as a
report-style ``progress`` form (communication grammar): each node is a
tagged, pickable card; the answer is one node to pull more on.

This module is Redis's first real consumer in the curated-memory loop
(curated-memory-productionization R3): the render reads the Redis
function's output, never the curated JSON file. The transform is split
from the fetch so it stays testable without a Redis server.

Usage from a session::

    python -m attune.memory.recall_digest --count 9

prints widget HTML ready to pass to ``show_widget``; the submitted
answer round-trips through :func:`attune.elicitation.collect_form_response`.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

#: Redis Function the SessionStart hydration hook loads (memory repo's
#: ``functions.lua``). Returns one JSON document per curated node.
DIGEST_FUNCTION = "recall_digest"

#: Max characters of a node description carried into the card note.
DETAIL_MAX = 160


def fetch_digest_nodes(count: int = 9, client: Any = None) -> list[dict[str, Any]]:
    """Fetch curated nodes from the ``recall_digest`` Redis Function.

    Args:
        count: How many nodes to request (most-recent first).
        client: An optional connected ``redis.Redis`` client. When None,
            one is created from ``REDIS_URL`` (default
            ``redis://127.0.0.1:6379/0``).

    Returns:
        A list of node dicts (``name``, ``type``, ``description``,
        ``updated_at``, ``id``, ``edges``), most-recent first.

    Raises:
        ImportError: If the ``redis`` package is not installed.
        ValueError: If the function returns malformed JSON.
        redis.RedisError: If Redis is unreachable or the function is
            not loaded.
    """
    if client is None:
        import redis  # noqa: PLC0415 — optional dependency, import at use

        url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        client = redis.Redis.from_url(url, decode_responses=True)

    raw = client.fcall(DIGEST_FUNCTION, 0, str(count))
    nodes: list[dict[str, Any]] = []
    for entry in raw or []:
        if isinstance(entry, bytes):
            entry = entry.decode("utf-8")
        try:
            nodes.append(json.loads(entry))
        except (TypeError, json.JSONDecodeError) as e:
            logger.exception("recall_digest returned a malformed entry")
            raise ValueError(f"recall_digest returned malformed JSON: {e}") from e
    return nodes


def _detail(description: str) -> str:
    """Trim a node description to a one-line card note."""
    text = " ".join(description.split())
    if len(text) <= DETAIL_MAX:
        return text
    return text[: DETAIL_MAX - 1].rstrip() + "…"


def _age_suffix(updated_at: Any) -> str:
    """Staleness label for a digest card, from the node's ``updated_at``.

    Redis digest nodes carry no file path, so the age basis is the graph's
    ``updated_at`` — the same last-EDIT stopgap the file sweep uses until
    ``verified:`` ships (memory-status-integrity P2). Label only, never used
    to reorder or drop a node (decision D1), and a missing or malformed
    timestamp yields no label rather than costing the caller the digest.

    Args:
        updated_at: ISO-8601 date or datetime string from the node dict.

    Returns:
        ``"  ⟨N days unverified⟩"`` or ``""`` when the timestamp is unusable.
    """
    from datetime import date

    from attune.memory.curated_audit import format_age_annotation

    try:
        basis = date.fromisoformat(str(updated_at)[:10])
    except (TypeError, ValueError):
        return ""
    days = max(0, (date.today() - basis).days)
    return f"  {format_age_annotation(days)}"


def digest_form_dict(
    nodes: list[dict[str, Any]], question_id: str = "memory_digest"
) -> dict[str, Any]:
    """Build the report-style ``progress`` form dict for a digest.

    Every node becomes a pickable card tagged with its node type; the
    (optional) answer is the node name to pull more on. Feed the result
    to :func:`attune.elicitation.form_from_dict`.

    Args:
        nodes: Node dicts as returned by :func:`fetch_digest_nodes`.
        question_id: The form field id the answer posts back under.

    Returns:
        A form dict ``{title, description, fields: [...]}``.
    """
    items = []
    for node in nodes:
        name = str(node.get("name", "")) or str(node.get("id", "unnamed"))
        items.append(
            {
                "label": name,
                "status": str(node.get("type", "node")).replace("_", " "),
                "detail": _detail(str(node.get("description", "")))
                + _age_suffix(node.get("updated_at")),
            }
        )
    labels = [it["label"] for it in items]
    return {
        "title": "Memory digest",
        "description": "What curated memory carries right now, most recent first.",
        "fields": [
            {
                "id": question_id,
                "text": "Pull more on a topic?",
                "type": "progress",
                "progress_style": "report",
                "required": False,
                "options": labels,
                "progress_items": items,
                "rationale": (f"{len(items)} curated node(s), live from FCALL {DIGEST_FUNCTION}."),
            }
        ],
    }


def render_digest_html(count: int = 9, client: Any = None) -> str:
    """Fetch the digest from Redis and render it as widget HTML.

    Args:
        count: How many nodes to request.
        client: Optional connected ``redis.Redis`` client (see
            :func:`fetch_digest_nodes`).

    Returns:
        Self-contained HTML for ``show_widget``.

    Raises:
        ValueError: If Redis returns no nodes (an empty digest usually
            means the hydration hook has not run).
    """
    from attune.elicitation import form_from_dict, form_to_widget_html

    nodes = fetch_digest_nodes(count=count, client=client)
    if not nodes:
        raise ValueError(
            "recall_digest returned no nodes — has the SessionStart hydration hook run?"
        )
    form = form_from_dict(digest_form_dict(nodes))
    return form_to_widget_html(form)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: print the digest widget HTML to stdout."""
    import argparse

    parser = argparse.ArgumentParser(description="Render the curated-memory recall digest")
    parser.add_argument("--count", type=int, default=9, help="nodes to request (default 9)")
    args = parser.parse_args(argv)
    print(render_digest_html(count=args.count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
