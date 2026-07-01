#!/usr/bin/env python3
"""Recall-accuracy benchmark for attune.memory.PersonalMemory.

Writes a small, realistic corpus into an isolated temp directory via
PersonalMemory.capture(), then runs hand-authored ground-truth queries
against PersonalMemory.query() and reports hit@1 / hit@3 / false-positive
rate. See docs/specs/memory-recall-eval/requirements.md for the design.

Modes (--phase):
  all          capture + evaluate in one process (default; Runs 1-2)
  persistence  capture and evaluate in two SEPARATE OS processes against
               the same global root, so the query side starts from a
               brand-new PersonalMemory instance with nothing in memory
               - proves recall survives process death (Run 3)
  capture      write the corpus into --root (used by persistence mode)
  evaluate     query against an already-captured --root (used by
               persistence mode; --json-out FILE for machine-readable
               output)

Never touches real memory (~/.attune/personal_memory or a project's
.attune/memory/) - the orchestrating modes use isolated temp
directories; capture/evaluate take an explicit --root.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attune.memory.personal import PersonalMemory  # noqa: E402

# ---------------------------------------------------------------------------
# Corpus: realistic captured-memory entries with one clear fact each.
# ---------------------------------------------------------------------------


@dataclass
class CorpusEntry:
    topic: str
    kind: str
    content: str


CORPUS: list[CorpusEntry] = [
    CorpusEntry(
        "redis-timeout-config",
        "decision",
        "We set the Redis connection timeout to 30 seconds after seeing "
        "intermittent 5-second-timeout failures under load in staging. "
        "A shorter timeout was too aggressive for cross-region latency.",
    ),
    CorpusEntry(
        "db-choice-rationale",
        "decision",
        "We chose Redis over Postgres for the session cache because reads "
        "need sub-millisecond latency and the data is fully ephemeral - "
        "durability guarantees Postgres offers weren't worth the latency cost.",
    ),
    CorpusEntry(
        "retry-backoff-pattern",
        "pattern",
        "Standard retry pattern for flaky network calls: exponential backoff "
        "starting at 200ms, capped at 5 seconds, max 4 attempts, jitter of "
        "up to 50ms added to avoid thundering-herd retries.",
    ),
    CorpusEntry(
        "feature-flag-rollout-pattern",
        "pattern",
        "Feature flags are rolled out in three stages: internal team only, "
        "10% of users for 48 hours, then 100%. Each stage requires error-rate "
        "monitoring to stay flat before advancing.",
    ),
    CorpusEntry(
        "flaky-auth-test",
        "troubleshooting",
        "The auth integration test flaked intermittently because it raced "
        "against token refresh - the token was sometimes still mid-rotation "
        "when the test asserted on it. Fixed by waiting for the rotation-complete "
        "event instead of a fixed sleep.",
    ),
    CorpusEntry(
        "memory-leak-worker-pool",
        "troubleshooting",
        "A memory leak in the worker pool was caused by completed task futures "
        "never being removed from a tracking dict. Fixed by popping the future "
        "from the dict in its done-callback.",
    ),
    CorpusEntry(
        "api-rate-limit-headers",
        "reference",
        "The upstream payments API returns rate-limit info in the "
        "X-RateLimit-Remaining and X-RateLimit-Reset headers; Reset is a Unix "
        "timestamp, not a delta in seconds.",
    ),
    CorpusEntry(
        "deploy-window-policy",
        "reference",
        "Deploys are only allowed Tuesday-Thursday, 10am-3pm Eastern, to ensure "
        "on-call engineers are at their desks if something breaks.",
    ),
    CorpusEntry(
        "cache-invalidation-strategy",
        "decision",
        "Cache invalidation uses a write-through strategy with a 60-second TTL "
        "as a backstop, rather than pure TTL-only, because stale reads after a "
        "write were causing visible UI inconsistency.",
    ),
    CorpusEntry(
        "logging-pii-redaction-pattern",
        "pattern",
        "All log statements pass through a redaction filter that masks email "
        "addresses and phone numbers before the line is written, using a regex "
        "pass applied at the logging handler level, not at each call site.",
    ),
    CorpusEntry(
        "slow-query-n-plus-one",
        "troubleshooting",
        "The dashboard load was slow because of an N+1 query - each row fetched "
        "its own related-object query in a loop. Fixed with a single joined "
        "query using select_related, cutting load time from 4s to 200ms.",
    ),
    CorpusEntry(
        "webhook-signature-verification",
        "reference",
        "Incoming webhooks are verified using an HMAC-SHA256 signature over the "
        "raw request body, compared with constant-time comparison to avoid "
        "timing attacks; the shared secret rotates monthly.",
    ),
    CorpusEntry(
        "queue-consumer-idempotency",
        "pattern",
        "Queue consumers are idempotent by keying processed-message state on the "
        "message's unique ID in a dedup table with a 24-hour TTL, so redelivery "
        "after a crash doesn't double-process.",
    ),
    CorpusEntry(
        "onboarding-doc-location",
        "reference",
        "New-engineer onboarding docs live in docs/onboarding/, not the wiki - "
        "the wiki was deprecated after it drifted out of sync with the repo.",
    ),
    CorpusEntry(
        "circuit-breaker-threshold",
        "decision",
        "The circuit breaker trips after 5 consecutive failures within a "
        "10-second window and stays open for 30 seconds before a half-open "
        "retry, tuned down from an initial 20-failure threshold that was too "
        "slow to react during a real outage.",
    ),
    CorpusEntry(
        "test-flake-quarantine-policy",
        "reference",
        "Flaky tests get quarantined (marked xfail with a tracking issue link) "
        "after failing 3 times in a week, rather than being deleted outright.",
    ),
    CorpusEntry(
        "graphql-pagination-pattern",
        "pattern",
        "GraphQL list fields use cursor-based pagination with an opaque "
        "base64-encoded cursor, not offset-based, so results stay stable when "
        "items are inserted or deleted mid-pagination.",
    ),
    CorpusEntry(
        "incident-postmortem-timing",
        "reference",
        "Postmortems for Sev1 incidents are due within 5 business days of "
        "resolution; Sev2 within 10 business days. Blameless format is required.",
    ),
]


@dataclass
class Query:
    text: str
    expected_topic: str | None  # None = negative query, no good match expected


QUERIES: list[Query] = [
    Query("Why did we set the Redis timeout to 30 seconds?", "redis-timeout-config"),
    Query("Why Redis instead of Postgres for the session cache?", "db-choice-rationale"),
    Query("What's our standard retry/backoff pattern for network calls?", "retry-backoff-pattern"),
    Query("How do we roll out feature flags safely?", "feature-flag-rollout-pattern"),
    Query("Why was the auth test flaky?", "flaky-auth-test"),
    Query("What caused the memory leak in the worker pool?", "memory-leak-worker-pool"),
    Query("What headers does the payments API use for rate limiting?", "api-rate-limit-headers"),
    Query("When are we allowed to deploy?", "deploy-window-policy"),
    Query("How does cache invalidation work?", "cache-invalidation-strategy"),
    Query("How do we redact PII from logs?", "logging-pii-redaction-pattern"),
    Query("Why was the dashboard slow to load?", "slow-query-n-plus-one"),
    Query("How do we verify incoming webhook signatures?", "webhook-signature-verification"),
    Query("How do queue consumers avoid double-processing messages?", "queue-consumer-idempotency"),
    Query("Where do the onboarding docs live?", "onboarding-doc-location"),
    Query("What's the circuit breaker failure threshold?", "circuit-breaker-threshold"),
    Query("When do we quarantine a flaky test?", "test-flake-quarantine-policy"),
    Query("What pagination style do we use for GraphQL lists?", "graphql-pagination-pattern"),
    Query("How long do we have to write a postmortem?", "incident-postmortem-timing"),
    # Negative queries: no good match should exist in the corpus.
    Query("What's our company's parental leave policy?", None),
    Query("Which JavaScript framework do we use for the frontend?", None),
    Query("What's the office WiFi password?", None),
    Query("How do we handle currency conversion for international pricing?", None),
    Query("What's our policy on remote work days per week?", None),
]


def capture_corpus(global_root: Path) -> None:
    """Write the benchmark corpus into ``global_root`` via PersonalMemory."""
    unused_project_root = global_root.parent / "no_project_dir"  # never created
    pm = PersonalMemory(global_root=global_root, project_root=unused_project_root)
    for entry in CORPUS:
        pm.capture(entry.topic, entry.content, kind=entry.kind)


def evaluate(global_root: Path) -> dict:
    """Run the ground-truth queries against an already-captured root."""
    unused_project_root = global_root.parent / "no_project_dir"  # never created
    pm = PersonalMemory(global_root=global_root, project_root=unused_project_root)

    hit_at_1 = 0
    hit_at_3 = 0
    positive_queries = [q for q in QUERIES if q.expected_topic is not None]
    negative_queries = [q for q in QUERIES if q.expected_topic is None]
    failures: list[dict] = []

    positive_top_scores: list[float] = []
    for q in positive_queries:
        results = pm.query(q.text, k=3)
        topics_returned = [Path(r["path"]).parent.name for r in results]
        if results:
            positive_top_scores.append(results[0]["score"])
        if topics_returned[:1] == [q.expected_topic]:
            hit_at_1 += 1
        if q.expected_topic in topics_returned:
            hit_at_3 += 1
        else:
            failures.append(
                {
                    "query": q.text,
                    "expected": q.expected_topic,
                    "got": topics_returned,
                }
            )

    # NOTE: `score` is an unbounded raw keyword-overlap count (not a
    # normalized [0,1] confidence), so there is no universal absolute
    # threshold for "confident false positive." We report the actual
    # top-1 score distributions for positive vs. negative queries and
    # let the reader judge separation, rather than picking an arbitrary
    # cutoff that could over- or under-state precision.
    negative_top_scores: list[float] = []
    negative_hits: list[dict] = []
    for q in negative_queries:
        results = pm.query(q.text, k=3)
        top_score = results[0]["score"] if results else 0.0
        negative_top_scores.append(top_score)
        negative_hits.append(
            {
                "query": q.text,
                "top_result": results[0]["path"] if results else None,
                "score": top_score,
            }
        )

    return {
        "corpus_size": len(CORPUS),
        "positive_queries": len(positive_queries),
        "negative_queries": len(negative_queries),
        "hit_at_1": hit_at_1,
        "hit_at_1_rate": hit_at_1 / len(positive_queries),
        "hit_at_3": hit_at_3,
        "hit_at_3_rate": hit_at_3 / len(positive_queries),
        "positive_top_scores": positive_top_scores,
        "negative_top_scores": negative_top_scores,
        "failures": failures,
        "negative_hits": negative_hits,
    }


def run_benchmark() -> dict:
    """Capture + evaluate within a single process (Runs 1-2 methodology)."""
    tmp_root = Path(tempfile.mkdtemp(prefix="attune_memory_recall_eval_"))
    global_root = tmp_root / "global"
    global_root.mkdir(parents=True, exist_ok=True)
    try:
        capture_corpus(global_root)
        return evaluate(global_root)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def run_persistence_benchmark() -> dict:
    """Capture and evaluate in two SEPARATE OS processes (Run 3 methodology).

    The capture subprocess exits (taking its PersonalMemory instance and
    any process state with it) before the evaluate subprocess starts from
    a brand-new instance pointed at the same on-disk global root. Identical
    numbers to run_benchmark() prove recall is fully file-backed and
    survives process death.
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="attune_memory_recall_eval_persist_"))
    global_root = tmp_root / "global"
    global_root.mkdir(parents=True, exist_ok=True)
    script = str(Path(__file__).resolve())
    try:
        subprocess.run(
            [sys.executable, script, "--phase", "capture", "--root", str(global_root)],
            check=True,
        )
        # Results go through a file, not stdout - attune_rag's structlog
        # lines print to stdout and would corrupt inline JSON.
        json_out = tmp_root / "results.json"
        subprocess.run(
            [
                sys.executable,
                script,
                "--phase",
                "evaluate",
                "--root",
                str(global_root),
                "--json-out",
                str(json_out),
            ],
            check=True,
        )
        return json.loads(json_out.read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def print_report(results: dict) -> None:
    print(f"Corpus size:        {results['corpus_size']}")
    print(f"Positive queries:   {results['positive_queries']}")
    print(f"Negative queries:   {results['negative_queries']}")
    print(
        f"hit@1:              {results['hit_at_1']}/{results['positive_queries']} "
        f"({results['hit_at_1_rate']:.1%})"
    )
    print(
        f"hit@3:              {results['hit_at_3']}/{results['positive_queries']} "
        f"({results['hit_at_3_rate']:.1%})"
    )
    pos_scores = sorted(results["positive_top_scores"])
    neg_scores = sorted(results["negative_top_scores"])
    print(f"Positive top-1 scores (sorted): {pos_scores}")
    print(f"Negative top-1 scores (sorted): {neg_scores}")
    print(
        "(score is an unbounded raw keyword-overlap count, not a [0,1] "
        "confidence - see decisions.md for how to read this)"
    )
    if results["failures"]:
        print("\nRecall failures (expected topic not in top-3):")
        for f in results["failures"]:
            print(f"  Q: {f['query']!r}")
            print(f"     expected={f['expected']!r} got={f['got']!r}")
    print("\nNegative-query top results (for manual precision inspection):")
    for f in results["negative_hits"]:
        print(f"  Q: {f['query']!r}")
        print(f"     top_result={f['top_result']!r} score={f['score']:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("all", "persistence", "capture", "evaluate"),
        default="all",
        help="all = single-process benchmark (default); persistence = "
        "capture and evaluate in separate subprocesses; capture/evaluate "
        "= one half, against an explicit --root",
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="global-root directory (required for capture/evaluate phases)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="write raw JSON results to this file instead of printing the "
        "human report (evaluate phase)",
    )
    args = parser.parse_args()

    if args.phase in ("capture", "evaluate") and args.root is None:
        parser.error(f"--phase {args.phase} requires --root")

    if args.phase == "capture":
        capture_corpus(args.root)
        return
    if args.phase == "evaluate":
        results = evaluate(args.root)
        if args.json_out:
            args.json_out.write_text(json.dumps(results), encoding="utf-8")
        else:
            print_report(results)
        return

    if args.phase == "persistence":
        results = run_persistence_benchmark()
        print("Mode: PERSISTENCE - capture and query ran in separate OS processes;")
        print("the query side used a brand-new PersonalMemory instance.\n")
    else:
        results = run_benchmark()
    print_report(results)


if __name__ == "__main__":
    main()
