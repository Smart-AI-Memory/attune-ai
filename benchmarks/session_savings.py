"""Session-level A/B: total token + wall-clock cost with memory on vs off.

``memory_savings.py`` measures the *per-recall* economics (what a recall
surface returns vs loading the whole store). This benchmark measures the
question one level up — the one a cost claim actually needs: **across
whole sessions doing real tasks, what does the memory suite change about
total input tokens and wall-clock?**

It runs each task in a headless Claude Code session (``claude -p``)
twice, toggling the memory suite's env kill-switches between arms:

  * **on**  — ``ATTUNE_JIT_RECALL=1 ATTUNE_LESSON_RECALL=1`` (the
    trap-moment and lesson-recall injection hooks fire as normal)
  * **off** — ``ATTUNE_JIT_RECALL=0 ATTUNE_LESSON_RECALL=0``

and compares, per task and in aggregate: uncached input tokens (billed
at full rate), cache reads (billed at ~10%), output tokens, turns,
API time, wall-clock, and reported cost.

Scope honesty — read before quoting numbers:

  * The toggle covers the two dominant injection surfaces (JIT recall
    and lesson recall). The SessionStart hydrate/digest line has no env
    gate today, so it fires in BOTH arms; it is constant across arms
    and cancels out of the delta.
  * One run per (task, arm) is directional, not publishable. Use
    ``--repeats 3`` (or more) and quote medians. Arm order alternates
    per repeat so prompt-cache warmth doesn't systematically favor one
    arm.
  * Savings only appear on tasks where recall actually prevents
    re-derivation. A task set that never hits a trap moment will show
    memory as pure overhead — that is a true and useful result, not a
    benchmark failure.

Run (from a plain terminal, NOT inside a Claude Code session)::

    python -m benchmarks.session_savings                    # dry-run plan
    python -m benchmarks.session_savings --run              # execute
    python -m benchmarks.session_savings --run --repeats 3 --markdown
    python -m benchmarks.session_savings --run --tasks my_tasks.json \
        --json-out results.json

Requires the ``claude`` CLI on PATH, authenticated. Tasks run with
read-only tools (Read/Grep/Glob) and bounded turns, so the target repo
is never mutated.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import median
from typing import Any

#: Env deltas per arm. Everything else in the environment is inherited
#: unchanged so the two arms differ ONLY in the memory suite's gated hooks.
ARM_ENV: dict[str, dict[str, str]] = {
    "on": {"ATTUNE_JIT_RECALL": "1", "ATTUNE_LESSON_RECALL": "1"},
    "off": {"ATTUNE_JIT_RECALL": "0", "ATTUNE_LESSON_RECALL": "0"},
}

#: Read-only analysis tasks that make sense against any attune-* repo.
#: Override with ``--tasks FILE`` (JSON: ``[{"id": ..., "prompt": ...}]``).
DEFAULT_TASKS: list[dict[str, str]] = [
    {
        "id": "release-surface",
        "prompt": (
            "Where is this package's version defined, and what release "
            "automation exists (workflows, scripts)? Summarize in 5 bullets."
        ),
    },
    {
        "id": "test-conventions",
        "prompt": (
            "How is the test suite organized, and what conventions govern "
            "LLM mocking in tests? Cite the files that define them."
        ),
    },
    {
        "id": "session-hooks",
        "prompt": (
            "Trace what happens when a Claude Code session starts in this "
            "repo: list each configured hook and its purpose."
        ),
    },
    {
        "id": "changelog-risk",
        "prompt": (
            "From the changelog, summarize the most recent release and flag "
            "anything breaking or risky for downstream consumers."
        ),
    },
    {
        "id": "debt-hotspots",
        "prompt": (
            "Find TODO/FIXME/HACK markers in the source tree and rank the "
            "top 3 debt hotspots with one-line justifications."
        ),
    },
]

READ_ONLY_TOOLS = "Read,Grep,Glob"


@dataclass
class RunResult:
    """One headless session's measured outcome."""

    task_id: str
    arm: str
    repeat: int
    ok: bool
    wall_s: float
    api_s: float = 0.0
    num_turns: int = 0
    input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str = ""

    @property
    def uncached_input(self) -> int:
        """Tokens billed at the full input rate."""
        return self.input_tokens + self.cache_creation_tokens


@dataclass
class ArmSummary:
    runs: int = 0
    failures: int = 0
    uncached_input: list[int] = field(default_factory=list)
    cache_read: list[int] = field(default_factory=list)
    output: list[int] = field(default_factory=list)
    turns: list[int] = field(default_factory=list)
    wall_s: list[float] = field(default_factory=list)
    api_s: list[float] = field(default_factory=list)
    cost_usd: list[float] = field(default_factory=list)


def load_tasks(path: Path | None) -> list[dict[str, str]]:
    """Load the task set, validating shape early so failures are cheap."""
    if path is None:
        return DEFAULT_TASKS
    tasks = json.loads(path.read_text())
    if not isinstance(tasks, list) or not tasks:
        raise ValueError(f"{path}: expected a non-empty JSON list")
    for i, t in enumerate(tasks):
        if not isinstance(t, dict) or not t.get("id") or not t.get("prompt"):
            raise ValueError(f"{path}: task {i} needs non-empty 'id' and 'prompt'")
    ids = [t["id"] for t in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path}: duplicate task ids")
    return tasks


def build_env(arm: str, base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.update(ARM_ENV[arm])
    return env


def parse_result_json(raw: str, *, task_id: str, arm: str, repeat: int, wall_s: float) -> RunResult:
    """Parse ``claude -p --output-format json`` output defensively.

    Headless output is a single JSON object with ``type: result``; hooks
    or wrappers may prepend noise, so scan for the first parseable line
    that looks like the result envelope.
    """
    obj: dict[str, Any] | None = None
    try:
        candidate = json.loads(raw)
        if isinstance(candidate, dict):
            obj = candidate
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and candidate.get("type") == "result":
                obj = candidate
                break
    if obj is None:
        return RunResult(
            task_id=task_id,
            arm=arm,
            repeat=repeat,
            ok=False,
            wall_s=wall_s,
            error=f"unparseable output: {raw[:200]!r}",
        )
    usage = obj.get("usage") or {}
    return RunResult(
        task_id=task_id,
        arm=arm,
        repeat=repeat,
        ok=obj.get("subtype") == "success",
        wall_s=wall_s,
        api_s=float(obj.get("duration_api_ms", 0)) / 1000.0,
        num_turns=int(obj.get("num_turns", 0)),
        input_tokens=int(usage.get("input_tokens", 0)),
        cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0)),
        cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        cost_usd=float(obj.get("total_cost_usd", 0.0)),
        error="" if obj.get("subtype") == "success" else str(obj.get("subtype")),
    )


def run_session(
    task: dict[str, str], arm: str, repeat: int, *, repo: Path, max_turns: int, timeout_s: int
) -> RunResult:
    cmd = [
        "claude",
        "-p",
        task["prompt"],
        "--output-format",
        "json",
        "--allowedTools",
        READ_ONLY_TOOLS,
        "--max-turns",
        str(max_turns),
    ]
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo,
            env=build_env(arm),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            task_id=task["id"],
            arm=arm,
            repeat=repeat,
            ok=False,
            wall_s=time.monotonic() - start,
            error=f"timeout after {timeout_s}s",
        )
    wall = time.monotonic() - start
    result = parse_result_json(proc.stdout, task_id=task["id"], arm=arm, repeat=repeat, wall_s=wall)
    if not result.ok and not result.error:
        result.error = proc.stderr.strip()[:200]
    return result


def aggregate(results: list[RunResult]) -> dict[str, ArmSummary]:
    arms: dict[str, ArmSummary] = {"on": ArmSummary(), "off": ArmSummary()}
    for r in results:
        s = arms[r.arm]
        s.runs += 1
        if not r.ok:
            s.failures += 1
            continue
        s.uncached_input.append(r.uncached_input)
        s.cache_read.append(r.cache_read_tokens)
        s.output.append(r.output_tokens)
        s.turns.append(r.num_turns)
        s.wall_s.append(r.wall_s)
        s.api_s.append(r.api_s)
        s.cost_usd.append(r.cost_usd)
    return arms


def _delta_pct(on: float, off: float) -> str:
    if off == 0:
        return "n/a"
    return f"{(on - off) / off * 100:+.1f}%"


def summary_rows(arms: dict[str, ArmSummary]) -> list[tuple[str, str, str, str]]:
    """(metric, on, off, delta) rows; medians of successful runs."""

    def med(vals: list, fmt: str) -> tuple[float, str]:
        if not vals:
            return 0.0, "—"
        m = median(vals)
        return m, fmt.format(m)

    rows: list[tuple[str, str, str, str]] = []
    metrics: list[tuple[str, str, str]] = [
        ("uncached input tok (median/task)", "uncached_input", "{:,.0f}"),
        ("cache-read tok (median/task)", "cache_read", "{:,.0f}"),
        ("output tok (median/task)", "output", "{:,.0f}"),
        ("turns (median/task)", "turns", "{:.0f}"),
        ("wall-clock s (median/task)", "wall_s", "{:.1f}"),
        ("API s (median/task)", "api_s", "{:.1f}"),
        ("cost USD (median/task)", "cost_usd", "{:.4f}"),
    ]
    for label, attr, fmt in metrics:
        on_v, on_s = med(getattr(arms["on"], attr), fmt)
        off_v, off_s = med(getattr(arms["off"], attr), fmt)
        rows.append((label, on_s, off_s, _delta_pct(on_v, off_v)))
    return rows


def render_table(arms: dict[str, ArmSummary], results: list[RunResult]) -> str:
    lines = ["", "=== session_savings: memory on vs off ==="]
    ok_on = arms["on"].runs - arms["on"].failures
    ok_off = arms["off"].runs - arms["off"].failures
    lines.append(f"runs: on {ok_on}/{arms['on'].runs} ok, off {ok_off}/{arms['off'].runs} ok")
    lines.append(f"{'metric':<36} {'on':>12} {'off':>12} {'Δ on vs off':>12}")
    for metric, on_s, off_s, delta in summary_rows(arms):
        lines.append(f"{metric:<36} {on_s:>12} {off_s:>12} {delta:>12}")
    failures = [r for r in results if not r.ok]
    if failures:
        lines.append("")
        lines.append("failures:")
        for r in failures:
            lines.append(f"  {r.task_id}/{r.arm}#{r.repeat}: {r.error}")
    if ok_on < 5 or ok_off < 5:
        lines.append("")
        lines.append(
            "NOTE: <5 successful runs per arm — treat deltas as directional, "
            "not quotable. Add tasks or --repeats."
        )
    return "\n".join(lines)


def render_markdown(arms: dict[str, ArmSummary]) -> str:
    lines = [
        "| Metric (median/task) | Memory on | Memory off | Δ on vs off |",
        "|---|--:|--:|--:|",
    ]
    for metric, on_s, off_s, delta in summary_rows(arms):
        lines.append(f"| {metric} | {on_s} | {off_s} | {delta} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="store_true", help="execute (default: print the plan)")
    parser.add_argument("--tasks", type=Path, help="JSON task file [{id, prompt}, ...]")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repo the sessions run in")
    parser.add_argument("--repeats", type=int, default=1, help="runs per (task, arm)")
    parser.add_argument("--max-turns", type=int, default=15, help="turn cap per session")
    parser.add_argument("--timeout-s", type=int, default=600, help="per-session timeout")
    parser.add_argument("--markdown", action="store_true", help="emit the README table")
    parser.add_argument("--json-out", type=Path, help="write full results JSON here")
    args = parser.parse_args(argv)

    tasks = load_tasks(args.tasks)
    n_sessions = len(tasks) * 2 * args.repeats
    plan = (
        f"plan: {len(tasks)} tasks × 2 arms × {args.repeats} repeat(s) = "
        f"{n_sessions} headless sessions in {args.repo} "
        f"(read-only tools: {READ_ONLY_TOOLS}, ≤{args.max_turns} turns each)"
    )
    print(plan)
    if not args.run:
        for t in tasks:
            print(f"  - {t['id']}: {t['prompt'][:80]}")
        print("dry-run only — pass --run to execute (spends real LLM usage).")
        return 0

    if shutil.which("claude") is None:
        print("FAIL: `claude` CLI not on PATH", file=sys.stderr)
        return 1
    if os.environ.get("CLAUDECODE"):
        print(
            "WARN: running inside a Claude Code session — nested sessions can "
            "skew latency and hook behavior; prefer a plain terminal.",
            file=sys.stderr,
        )

    results: list[RunResult] = []
    for repeat in range(args.repeats):
        # Alternate arm order per repeat so cache warmth doesn't
        # systematically favor whichever arm runs second.
        order = ("on", "off") if repeat % 2 == 0 else ("off", "on")
        for task in tasks:
            for arm in order:
                print(f"[{len(results) + 1}/{n_sessions}] {task['id']} / {arm} ...", flush=True)
                r = run_session(
                    task,
                    arm,
                    repeat,
                    repo=args.repo,
                    max_turns=args.max_turns,
                    timeout_s=args.timeout_s,
                )
                status = "ok" if r.ok else f"FAIL ({r.error})"
                print(
                    f"    {status}: {r.uncached_input:,} uncached in, "
                    f"{r.cache_read_tokens:,} cache-read, {r.wall_s:.1f}s",
                    flush=True,
                )
                results.append(r)

    arms = aggregate(results)
    print(render_table(arms, results))
    if args.markdown:
        print()
        print(render_markdown(arms))
    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {
                    "plan": plan,
                    "arm_env": ARM_ENV,
                    "results": [asdict(r) for r in results],
                },
                indent=2,
            )
        )
        print(f"\nfull results → {args.json_out}")
    any_ok = any(r.ok for r in results)
    return 0 if any_ok else 1


if __name__ == "__main__":
    sys.exit(main())
