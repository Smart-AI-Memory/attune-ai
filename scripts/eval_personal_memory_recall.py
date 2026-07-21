"""Recall-accuracy benchmark for PersonalMemory (memory-recall-eval spec).

Captures a hand-authored corpus into an ISOLATED tmp root, runs
ground-truthed natural-language queries, and prints a paste-ready
markdown report with hit@1 / hit@3 / negative-query false-positive
rate (design D1-D4, docs/specs/memory-recall-eval/design.md).

Run keyless so ``capture()``'s polish step stays on the deterministic
skeleton path and the run spends nothing:

    ANTHROPIC_API_KEY="" .venv/bin/python scripts/eval_personal_memory_recall.py

The script never touches ``~/.attune`` or the repo's ``.attune/``
(R1): both memory roots are created under a ``tempfile.mkdtemp()``
that is removed on exit.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

# (topic, kind, content) — realistic entries, 1-2 clearly-stated facts
# each (R2). Kinds cover all four VALID_KINDS.
CORPUS: list[tuple[str, str, str]] = [
    (
        "api-timeout-policy",
        "decision",
        "We set the outbound HTTP timeout for all provider API calls to "
        "30 seconds, with a single retry after a 2-second backoff. Longer "
        "timeouts made workflow hangs indistinguishable from slow model "
        "responses; shorter ones false-failed large-context requests.",
    ),
    (
        "redis-over-postgres",
        "decision",
        "We chose Redis over Postgres for the session memory index because "
        "the access pattern is key-lookup plus full-text search over small "
        "documents, and RediSearch gives us both without an ORM layer. "
        "Postgres stays the answer for relational billing data.",
    ),
    (
        "python-floor-version",
        "decision",
        "The package supports Python 3.10 as the floor version. 3.9 was "
        "dropped because structural pattern matching and modern union "
        "syntax appear throughout the codebase.",
    ),
    (
        "release-tag-from-merge-sha",
        "decision",
        "Releases are tagged from the squash-merge SHA on main, never from "
        "the branch tip, because the branch tip can differ from what "
        "actually landed after rebases.",
    ),
    (
        "budget-cap-defaults",
        "decision",
        "Workflow budget caps default to 2 dollars at quick depth, 10 at "
        "standard, and 25 at deep. Setting ATTUNE_MAX_BUDGET_USD to zero "
        "disables the cap entirely.",
    ),
    (
        "retry-with-jitter",
        "pattern",
        "For any polling loop against an external API, add full jitter to "
        "the retry delay: sleep a random amount between zero and the "
        "backoff ceiling instead of a fixed interval. Fixed intervals "
        "synchronized our CI pollers and tripped rate limits.",
    ),
    (
        "early-return-guards",
        "pattern",
        "Flatten nested conditionals with early-return guard clauses: "
        "validate inputs at the top of the function and return or raise "
        "immediately. Three levels of nesting is the refactor trigger.",
    ),
    (
        "atomic-file-writes",
        "pattern",
        "Write files atomically: write to a tempfile in the destination "
        "directory, then os.replace onto the target. Pin newline handling "
        "explicitly so Windows text mode cannot rewrite line endings.",
    ),
    (
        "keyless-test-runs",
        "pattern",
        "To reproduce keyless CI locally, set ANTHROPIC_API_KEY to the "
        "EMPTY STRING rather than unsetting it. An unset variable lets "
        "dotenv re-inject the real key from the env file and the run "
        "silently spends money.",
    ),
    (
        "single-source-projection",
        "pattern",
        "Generated docs and mirrors are never edited directly: edit the "
        "master source, re-run the projector script, and commit both "
        "sides together. A drift-guard test fails CI when the projection "
        "is stale.",
    ),
    (
        "windows-crlf-test-failures",
        "troubleshooting",
        "If a byte-identity or round-trip test fails only on Windows CI "
        "lanes with CRLF versus LF differences, the writer opened a file "
        "in text mode without pinning newline. Fix the writer to pass "
        "newline='\\n'; do not loosen the test.",
    ),
    (
        "stash-pop-silent-skip",
        "troubleshooting",
        "When git stash pop appears to succeed but your stashed versions "
        "of files are missing, the destination branch tracks files the "
        "stash held as untracked — git silently keeps the branch copies. "
        "Recover with git checkout stash@{0} -- <files>.",
    ),
    (
        "editable-install-wrong-code",
        "troubleshooting",
        "If code changes in a worktree seem to have no effect, the "
        "editable install maps the package to the main checkout's src "
        "directory. Run with PYTHONPATH set to the worktree's absolute "
        "src path to execute the worktree's code.",
    ),
    (
        "port-8765-collision",
        "troubleshooting",
        "When the ops dashboard fails to start because port 8765 is held "
        "by another session, enable autoPort so the preview manager "
        "assigns a free port via the PORT environment variable, and "
        "remove any hardcoded --port flag from the launch command.",
    ),
    (
        "gpg-signing-config",
        "reference",
        "Commits are GPG-signed via commit.gpgsign true. A rebase replays "
        "commits; verify signatures afterwards with git log --format "
        "'%G?' and re-sign if any show N.",
    ),
    (
        "status-vocabulary",
        "reference",
        "Spec status lines must lead with a controlled-vocabulary token: "
        "complete, completed, done, shipped, superseded, approved, "
        "active, living, draft, parked, or paused. The token parked "
        "additionally requires a Resume-Trigger clause.",
    ),
    (
        "coverage-bars",
        "reference",
        "Test coverage policy: 80 percent is the enforced floor via "
        "codecov project and patch gates; 85 percent is the local "
        "fail_under target bar.",
    ),
    (
        "secret-storage-location",
        "reference",
        "API keys live in ~/.attune/anthropic.env with 0600 permissions, "
        "sourced from the shell profile with a set -a guard. Never store "
        "credentials in editor settings.json files: settings sync uploads "
        "them to the cloud.",
    ),
]

# Hand-authored ground truth (R3): (query, {acceptable expected topics}).
# Written as a person would ask, not as paraphrases of entry text.
POSITIVE_QUERIES: list[tuple[str, set[str]]] = [
    ("what timeout did we pick for provider API calls?", {"api-timeout-policy"}),
    ("how many retries do outbound HTTP requests get?", {"api-timeout-policy"}),
    ("why did we go with Redis instead of Postgres?", {"redis-over-postgres"}),
    ("where does relational billing data belong?", {"redis-over-postgres"}),
    ("what's the minimum Python version we support?", {"python-floor-version"}),
    ("why was Python 3.9 dropped?", {"python-floor-version"}),
    ("which commit should a release tag point at?", {"release-tag-from-merge-sha"}),
    ("what's the default budget cap at standard depth?", {"budget-cap-defaults"}),
    ("how do I disable the workflow budget cap?", {"budget-cap-defaults"}),
    ("how should retry delays be spaced when polling an API?", {"retry-with-jitter"}),
    ("what made our CI pollers hit rate limits?", {"retry-with-jitter"}),
    ("when should deeply nested if statements be refactored?", {"early-return-guards"}),
    (
        "what's the safe way to write a file so readers never see a partial write?",
        {"atomic-file-writes"},
    ),
    ("how do I simulate CI's keyless environment locally?", {"keyless-test-runs"}),
    ("why does unsetting the API key still spend money in tests?", {"keyless-test-runs"}),
    ("can I edit generated documentation files directly?", {"single-source-projection"}),
    (
        "tests pass everywhere except Windows with line ending differences — what's wrong?",
        {"windows-crlf-test-failures"},
    ),
    (
        "git stash pop lost my changes without any conflict — what happened?",
        {"stash-pop-silent-skip"},
    ),
    (
        "my code edits in the worktree don't change the program's behavior — why?",
        {"editable-install-wrong-code"},
    ),
    (
        "the dashboard won't start because its port is taken — what's the fix?",
        {"port-8765-collision"},
    ),
    ("how do I check commit signatures after a rebase?", {"gpg-signing-config"}),
    ("which tokens are allowed at the start of a spec status line?", {"status-vocabulary"}),
    ("what extra clause does a parked spec need?", {"status-vocabulary"}),
    ("what's our enforced test coverage floor?", {"coverage-bars"}),
    ("where should API keys be stored on this machine?", {"secret-storage-location"}),
    ("why shouldn't credentials go in editor settings files?", {"secret-storage-location"}),
]

# Negative queries (R4): plausible asks with NO good match in the corpus.
NEGATIVE_QUERIES: list[str] = [
    "what's our Kubernetes ingress configuration?",
    "which GraphQL schema versioning scheme do we use?",
    "what did we decide about the mobile app's push notification provider?",
    "how is the Terraform state bucket locked?",
    "what's the on-call rotation schedule?",
    "which CSS framework does the marketing site use?",
]


def _topic_of(path_str: str) -> str:
    """Recover the topic slug from a result path (.../<topic>/<kind>.md)."""
    return Path(path_str).parent.name


def _cross_check() -> list[str]:
    """Validate corpus/ground-truth tables before producing any number."""
    problems: list[str] = []
    topics = {t for t, _, _ in CORPUS}
    if len(topics) != len(CORPUS):
        problems.append("duplicate topic slugs in CORPUS")
    covered: set[str] = set()
    for query, expected in POSITIVE_QUERIES:
        missing = expected - topics
        if missing:
            problems.append(f"query {query!r} expects unknown topics {missing}")
        covered |= expected
    uncovered = topics - covered
    if uncovered:
        problems.append(f"corpus entries with no positive query: {sorted(uncovered)}")
    if len(NEGATIVE_QUERIES) < 5:
        problems.append("need >=5 negative queries (R4)")
    return problems


def main() -> int:
    problems = _cross_check()
    if problems:
        for p in problems:
            print(f"CROSS-CHECK FAIL: {p}", file=sys.stderr)
        return 1

    from attune.memory.personal import PersonalMemory

    tmp = Path(tempfile.mkdtemp(prefix="recall-eval-"))
    try:
        mem = PersonalMemory(
            global_root=tmp / "global",
            project_root=tmp / "project",  # nonexistent → never scanned
        )
        for topic, kind, content in CORPUS:
            mem.capture(topic, kind=kind, content=content)

        hit1 = hit3 = 0
        failures: list[tuple[str, set[str], list[str]]] = []
        correct_top1_scores: list[float] = []
        for query, expected in POSITIVE_QUERIES:
            hits = mem.query(query, k=3)
            got = [_topic_of(h["path"]) for h in hits]
            if got and got[0] in expected:
                hit1 += 1
                correct_top1_scores.append(float(hits[0].get("score") or 0.0))
            if any(t in expected for t in got):
                hit3 += 1
            else:
                failures.append((query, expected, got))

        # D3: FP = negative top-1 score >= min correct-positive top-1 score.
        neg_rows: list[tuple[str, str, float, bool]] = []
        threshold = min(correct_top1_scores) if correct_top1_scores else None
        for query in NEGATIVE_QUERIES:
            hits = mem.query(query, k=3)
            top_topic = _topic_of(hits[0]["path"]) if hits else "(none)"
            top_score = float(hits[0].get("score") or 0.0) if hits else 0.0
            is_fp = threshold is not None and top_score >= threshold
            neg_rows.append((query, top_topic, top_score, is_fp))

        n_pos, n_neg = len(POSITIVE_QUERIES), len(NEGATIVE_QUERIES)
        fp_count = sum(1 for *_, fp in neg_rows if fp)
        print("## Recall-accuracy benchmark — paste-ready report\n")
        print(
            f"- Corpus: {len(CORPUS)} entries (4 kinds) · "
            f"{n_pos} positive / {n_neg} negative queries"
        )
        print(f"- **hit@1: {hit1}/{n_pos} ({hit1 / n_pos:.0%})**")
        print(f"- **hit@3: {hit3}/{n_pos} ({hit3 / n_pos:.0%})**")
        if threshold is None:
            print(
                "- **FP rate: criterion inapplicable** "
                "(zero correct positives to calibrate against)"
            )
        else:
            print(
                f"- **FP rate: {fp_count}/{n_neg} ({fp_count / n_neg:.0%})** "
                f"(threshold = min correct-positive top-1 score "
                f"{threshold:.4f})"
            )
        if failures:
            print("\n### hit@3 misses (query · expected · got)\n")
            for query, expected, got in failures:
                print(f"- {query!r} · expected {sorted(expected)} · got {got}")
        print("\n### Negative queries (query · top-1 topic · score · FP?)\n")
        for query, topic, score, fp in neg_rows:
            print(f"- {query!r} · {topic} · {score:.4f} · {'FP' if fp else 'ok'}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
