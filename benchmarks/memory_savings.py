"""Measure the memory suite's recall economics against the live store.

The cross-session memory loop (README §5) keeps its durable corpus in
files, serves it from Redis, and *recalls* a bounded, relevant slice on
demand instead of loading the whole store into the model's context. This
benchmark quantifies that trade for the corpus currently hydrated in
Redis (the same ``attune:memory:*`` docs the SessionStart hook warms):

  * **Token footprint** — how many tokens it costs to load the whole
    store into context, vs. what a recall surface actually returns.
  * **Latency** — how long a recall call takes vs. reading + concatenating
    the backing corpus files from disk.

Two recall surfaces are measured:

  1. **SessionStart digest** — ``FCALL recall_digest`` renders the curated
     nodes as a bounded card list (real call, real render).
  2. **Trap-moment lessons** — the ``UserPromptSubmit`` reminder injects a
     relevance-ranked lessons slice capped at
     ``lessons.DEFAULT_MAX_TOKENS`` tokens, no matter how large the lessons
     corpus grows.

Run::

    python -m benchmarks.memory_savings              # human table
    python -m benchmarks.memory_savings --markdown   # README-ready table
    python -m benchmarks.memory_savings --json-out results.json

Requires a reachable Redis with the curated corpus hydrated (the
SessionStart hook, or ``attune memory hydrate``) and ``tiktoken``.
Token counts use ``cl100k_base`` — an approximation of Claude's
tokenizer, stable and reproducible for relative comparison.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from statistics import median
from typing import Any

# ``attune.memory.lessons`` owns the trap-moment injection budget; read it
# rather than hard-coding so the benchmark tracks the real cap.
from attune.memory.lessons import DEFAULT_MAX_TOKENS as LESSONS_BUDGET_TOKENS
from attune.memory.recall_digest import DIGEST_FUNCTION, digest_form_dict, fetch_digest_nodes

#: The curated-memory repo the store is hydrated from — its ``*.md`` files
#: are the "whole files into context" baseline for the digest latency.
CURATED_CORPUS_DIR = Path.home() / ".attune" / "memory"

#: How many curated nodes the SessionStart digest requests.
DIGEST_COUNT = 9

#: Latency sample size (median reported; warm cache).
LATENCY_ITERS = 50


def _encoder() -> Any:
    import tiktoken  # noqa: PLC0415 — optional dependency, import at use

    return tiktoken.get_encoding("cl100k_base")


def _client() -> Any:
    import redis  # noqa: PLC0415 — optional dependency, import at use

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)


def _corpus_tokens_by_layer(client: Any, enc: Any) -> dict[str, dict[str, int]]:
    """Sum the ``text`` tokens of every hydrated doc, grouped by class.

    Returns ``{class: {"docs": n, "tokens": t}}`` for lesson / file /
    rule / node keys — the full store as it would land in context.
    """
    classes = {
        "lessons": "attune:memory:lesson:*",
        "files": "attune:memory:file:*",
        "rules": "attune:memory:rule:*",
        "nodes": "attune:memory:node:*",
    }
    out: dict[str, dict[str, int]] = {}
    for label, pattern in classes.items():
        docs = 0
        tokens = 0
        for key in client.scan_iter(match=pattern, count=500):
            text = client.hget(key, "text") or client.hget(key, "description") or ""
            if text:
                docs += 1
                tokens += len(enc.encode(text))
        out[label] = {"docs": docs, "tokens": tokens}
    return out


def _digest_recall_tokens(client: Any, enc: Any) -> int:
    """Tokens the SessionStart digest actually returns (real FCALL)."""
    nodes = fetch_digest_nodes(count=DIGEST_COUNT, client=client)
    rendered = json.dumps(digest_form_dict(nodes))
    return len(enc.encode(rendered))


def _time_median(fn: Any, iters: int = LATENCY_ITERS) -> float:
    """Median wall-clock (ms) of ``fn`` over ``iters`` warm calls."""
    fn()  # warm
    samples = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return median(samples)


def _read_all_corpus() -> str:
    """Baseline: read + concatenate every curated corpus file from disk."""
    parts = []
    for md in sorted(CURATED_CORPUS_DIR.rglob("*.md")):
        parts.append(md.read_text(encoding="utf-8"))
    return "\n".join(parts)


def measure() -> dict[str, Any]:
    """Run every measurement and return a structured result."""
    enc = _encoder()
    client = _client()

    by_layer = _corpus_tokens_by_layer(client, enc)
    lessons_tokens = by_layer["lessons"]["tokens"]
    nodes_tokens = by_layer["nodes"]["tokens"]
    store_tokens = sum(v["tokens"] for v in by_layer.values())
    store_docs = sum(v["docs"] for v in by_layer.values())

    digest_recall = _digest_recall_tokens(client, enc)

    # Trap-moment lessons: the injection is capped at the budget regardless
    # of corpus size, so the recall figure is min(budget, corpus).
    lessons_recall = min(LESSONS_BUDGET_TOKENS, lessons_tokens)

    digest_latency = _time_median(lambda: fetch_digest_nodes(count=DIGEST_COUNT, client=client))
    disk_latency = _time_median(_read_all_corpus)

    def ratio(full: int, recall: int) -> float:
        return round(full / recall, 1) if recall else 0.0

    return {
        "tokenizer": "cl100k_base",
        "store": {"docs": store_docs, "tokens": store_tokens, "by_layer": by_layer},
        "surfaces": {
            "sessionstart_digest": {
                "full_tokens": nodes_tokens,
                "recall_tokens": digest_recall,
                "reduction_x": ratio(nodes_tokens, digest_recall),
                "recall_latency_ms": round(digest_latency, 2),
                "baseline_latency_ms": round(disk_latency, 2),
                "note": f"FCALL {DIGEST_FUNCTION} over {by_layer['nodes']['docs']} curated nodes",
            },
            "trapmoment_lessons": {
                "full_tokens": lessons_tokens,
                "recall_tokens": lessons_recall,
                "reduction_x": ratio(lessons_tokens, lessons_recall),
                "note": (
                    f"budget-capped at DEFAULT_MAX_TOKENS={LESSONS_BUDGET_TOKENS}; "
                    f"{by_layer['lessons']['docs']} lessons in corpus"
                ),
            },
        },
    }


def _markdown(r: dict[str, Any]) -> str:
    d = r["surfaces"]["sessionstart_digest"]
    lz = r["surfaces"]["trapmoment_lessons"]
    lines = [
        "| Recall surface | Load whole corpus | Recall on demand | Token reduction |",
        "|---|--:|--:|--:|",
        f"| SessionStart digest ({r['store']['by_layer']['nodes']['docs']} curated nodes) "
        f"| {d['full_tokens']:,} tok | {d['recall_tokens']:,} tok | **{d['reduction_x']}×** |",
        f"| Trap-moment lessons ({r['store']['by_layer']['lessons']['docs']} lessons) "
        f"| {lz['full_tokens']:,} tok | ≤{lz['recall_tokens']:,} tok | **{lz['reduction_x']}×** |",
    ]
    lat = (
        f"\nDigest recall latency: **{d['recall_latency_ms']} ms** "
        f"(vs {d['baseline_latency_ms']} ms to read the corpus files from disk), "
        f"median of {LATENCY_ITERS} calls."
    )
    return "\n".join(lines) + "\n" + lat


def _human(r: dict[str, Any]) -> str:
    s = r["store"]
    out = [
        f"Store: {s['docs']} docs, {s['tokens']:,} tokens "
        f"({r['tokenizer']}) — the whole-memory-into-context cost.",
        "  by layer: "
        + ", ".join(f"{k}={v['docs']}/{v['tokens']:,}tok" for k, v in s["by_layer"].items()),
        "",
    ]
    for name, d in r["surfaces"].items():
        out.append(
            f"{name}: full={d['full_tokens']:,} recall={d['recall_tokens']:,} "
            f"→ {d['reduction_x']}× smaller  [{d['note']}]"
        )
        if "recall_latency_ms" in d:
            out.append(
                f"    latency: recall={d['recall_latency_ms']}ms  "
                f"disk-read-all={d['baseline_latency_ms']}ms"
            )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--markdown", action="store_true", help="emit the README table")
    parser.add_argument("--json-out", type=Path, help="write full results JSON here")
    args = parser.parse_args(argv)

    try:
        result = measure()
    except Exception as e:  # noqa: BLE001 — surface any setup gap plainly
        print(
            f"benchmark could not run: {e}\n"
            "Needs a reachable Redis with the curated corpus hydrated "
            "(run the SessionStart hook or `attune memory hydrate`) and tiktoken.",
            file=sys.stderr,
        )
        return 1

    if args.json_out:
        args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(_markdown(result) if args.markdown else _human(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
