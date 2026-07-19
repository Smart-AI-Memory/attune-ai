"""Round-table routines: scheduled/manual headless table runs (P3).

A routine convenes the table on a recurring question — the first is
the weekly **clean-run health check** (chair-ratified 2026-07-18,
replacing the unresolvable "§12 Clean-Run-Check" shorthand): run the
repo's keyless check battery, put the results to the seats, post a
digest thread for the chair.

Gates carried from the interactive loop (R8):

- **R5** — a hard invocation cap; the run halts with a ``halt``
  message when reached, never silently exceeds it.
- **R6** — an unavailable seat is marked absent; the run completes.
- **R8** — the runner NEVER promotes. The digest thread stays on the
  board for the chair; promotion happens interactively
  (``/roundtable promote <thread>``).

Manual-first (chair-ratified): ``python -m attune.roundtable.routine
clean-run``. Arm a schedule only after a proven manual run.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime
import os
import subprocess  # nosec B404 — fixed argv seat recipes, never shell=True
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from attune.roundtable.board import Board

#: Per-check and per-seat wall-clock bounds (seconds).
CHECK_TIMEOUT = 900
SEAT_TIMEOUT = 300

#: Output kept per check/seat before truncation — briefs stay bounded.
TAIL_CHARS = 2000


@dataclass
class RoutineSpec:
    """One routine: its checks, question framing, and caps.

    Args:
        name: Routine name; thread ids are ``routine-<name>-<date>``.
        question: Question template put to the seats; check evidence
            is appended by the runner.
        checks: ``(label, argv)`` commands run keyless for evidence.
        max_invocations: R5 cap on LLM invocations per run (seats +
            synthesis together).
    """

    name: str
    question: str
    checks: Sequence[tuple[str, Sequence[str]]] = ()
    max_invocations: int = 4


#: Routine #1 — the weekly clean-run health check.
CLEAN_RUN = RoutineSpec(
    name="clean-run",
    question=(
        "Weekly clean-run health check. Below are the keyless check "
        "results from the current tree. Deliberate: is the tree "
        "healthy? Name anything that drifted or degraded, rank "
        "anything needing action, and propose AT MOST one lesson "
        "candidate — only if a durable, receipted gotcha surfaced."
    ),
    checks=(
        # sys.executable, not bare "python": the check subprocess must
        # run the interpreter this runner runs under (PATH's python may
        # lack pytest entirely).
        ("collaboration-preflight", (sys.executable, "scripts/collaboration_preflight.py")),
        (
            "keyless-unit-suite",
            (sys.executable, "-m", "pytest", "tests/unit", "-q", "--timeout", "600"),
        ),
    ),
)

ROUTINES: dict[str, RoutineSpec] = {CLEAN_RUN.name: CLEAN_RUN}

#: Seat recipes, verified live 2026-07-18 (requirements: roster
#: invocation recipes). ``{brief}`` marks where the brief goes;
#: ``"-"`` as the sole marker means "brief on stdin".
SEAT_RECIPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("claude", ("claude", "-p", "{brief}")),
    ("antigravity", ("agy", "--add-dir", ".", "-p", "{brief}", "--mode", "plan")),
    ("codex", ("codex", "exec", "--skip-git-repo-check", "-")),
)

BRIEF_PREAMBLE = (
    "You are one seat at a three-model round table (Claude, "
    "Antigravity, Codex), convened by a scheduled routine. Answer "
    "independently. Reply with: (1) your POSITION, concretely; (2) "
    "the main RISK of your own position. Text only — do not run "
    "tools, write files, or take actions.\n\nQuestion:\n\n"
)


def run_command(
    argv: Sequence[str],
    stdin_text: str | None = None,
    timeout: int = SEAT_TIMEOUT,
    provider_clean: bool = False,
) -> tuple[int, str]:
    """Run one fixed-argv command keyless; return (exit code, output tail).

    Two env modes, both deliberate (live-run receipts, 2026-07-18):

    - Checks (default): ``ANTHROPIC_API_KEY`` set to the EMPTY string
      — CI-faithful (unset would let dotenv re-inject a real key
      downstream).
    - Seats (``provider_clean=True``): every ``ANTHROPIC_*`` and
      ``CLAUDE*`` variable REMOVED. When the runner itself executes
      inside a Claude Code session, the child inherits
      ``ANTHROPIC_BASE_URL`` + ``CLAUDE_CODE_*`` and 401s against the
      parent session's proxy; an EMPTY ``ANTHROPIC_API_KEY`` likewise
      401s the ``claude`` CLI instead of letting its own stored auth
      kick in. Scrubbing the whole provider surface fixes both and
      keeps harness identifiers out of member processes (R1 hygiene).
    """
    if provider_clean:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "CLAUDE"))}
    else:
        env = {**os.environ, "ANTHROPIC_API_KEY": ""}
    try:
        proc = subprocess.run(  # nosec B603 — fixed argv, shell=False
            list(argv),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError:
        return 127, f"{argv[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode, out[-TAIL_CHARS:]


def default_invoke_seat(recipe: Sequence[str], brief: str) -> tuple[int, str]:
    """Invoke one seat CLI with the brief substituted per its recipe."""
    if recipe[-1] == "-":
        return run_command(recipe, stdin_text=brief, provider_clean=True)
    argv = [brief if part == "{brief}" else part for part in recipe]
    return run_command(argv, provider_clean=True)


def run_routine(
    spec: RoutineSpec,
    board: Board | None = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] = default_invoke_seat,
    run_check: Callable[..., tuple[int, str]] = run_command,
    dry_run: bool = False,
) -> str:
    """Run one routine end-to-end; return the board thread id.

    Sequence: checks → question posted → seats (R5-capped, R6
    absent-tolerant) → one synthesis invocation → digest printed.
    The thread is left UNPROMOTED for the chair (R8).

    Args:
        spec: The routine to run.
        board: Board client; a default one when None.
        invoke_seat: Seat invoker (injectable for tests).
        run_check: Check runner (injectable for tests).
        dry_run: Run checks and print the brief; skip the board and
            every LLM invocation.
    """
    # Minute-resolution stamp: same-day reruns (fix-and-rerun is the
    # normal proving loop) must not append into one shared thread.
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    thread = f"routine-{spec.name}-{stamp}"

    # Progress goes to stdout as it happens: a routine's first check
    # can run for minutes, and silence reads as a hang (live-run
    # receipt, 2026-07-18 — the chair ran it twice).
    print(f"routine {spec.name!r}: thread {thread!r}", flush=True)
    evidence: list[str] = []
    for label, argv in spec.checks:
        print(f"  check {label} ... running (up to {CHECK_TIMEOUT}s)", flush=True)
        code, tail = run_check(argv, timeout=CHECK_TIMEOUT)
        status = "PASS" if code == 0 else f"FAIL (exit {code})"
        print(f"  check {label}: {status}", flush=True)
        evidence.append(f"### {label}: {status}\n{tail}")
    question = spec.question + "\n\n" + "\n\n".join(evidence)
    brief = BRIEF_PREAMBLE + question

    if dry_run:
        print(f"[dry-run] thread would be {thread!r}; brief follows:\n\n{brief}")
        return thread

    board = board or Board()
    board.ensure_functions()
    board.post_message(thread, "moderator", "question", question, routine=spec.name)

    invocations = 0
    halted = False
    positions: list[tuple[str, str]] = []
    for seat, recipe in SEAT_RECIPES:
        if invocations >= spec.max_invocations:
            halted = True
            board.post_message(
                thread,
                "moderator",
                "halt",
                f"invocation cap ({spec.max_invocations}) reached before seat {seat!r}",
            )
            break
        invocations += 1
        print(f"  seat {seat} ... briefing", flush=True)
        started = datetime.datetime.now()
        code, reply = invoke_seat(recipe, brief)
        duration = f"{(datetime.datetime.now() - started).total_seconds():.0f}s"
        if code != 0 or not reply.strip():
            print(f"  seat {seat}: ABSENT (exit {code}, {duration})", flush=True)
            board.post_message(
                thread,
                seat,
                "position",
                f"ABSENT — exit {code}: {reply[:200]}",
                absent=True,
                duration=duration,
            )
            continue
        print(f"  seat {seat}: position posted ({duration})", flush=True)
        board.post_message(thread, seat, "position", reply, round=1, duration=duration)
        positions.append((seat, reply))

    if positions and invocations < spec.max_invocations:
        invocations += 1
        synthesis_brief = (
            "You are the moderator of a round-table routine. Synthesize "
            "the seat positions below into a digest: agreements, splits, "
            "ranked actions, and any lesson candidate proposed. Be "
            "compact. Text only.\n\n"
            + "\n\n".join(f"## {seat}\n{reply}" for seat, reply in positions)
        )
        print("  synthesis ... running", flush=True)
        code, digest = invoke_seat(("claude", "-p", "{brief}"), synthesis_brief)
        if code == 0 and digest.strip():
            print("  synthesis: posted", flush=True)
            board.post_message(thread, "moderator", "synthesis", digest, round=1)
        else:
            print(f"  synthesis: FAILED (exit {code})", flush=True)
            # Silence here would read as success — name the failure on
            # the thread so the chair sees a digest-less run for what
            # it is.
            board.post_message(
                thread,
                "moderator",
                "halt",
                f"synthesis invocation failed (exit {code}): {digest[:200]}",
            )
    elif positions and not halted:
        board.post_message(
            thread,
            "moderator",
            "halt",
            f"invocation cap ({spec.max_invocations}) reached before synthesis",
        )

    print(
        f"routine {spec.name!r} complete: thread {thread!r} ({invocations} invocations). Review with /roundtable read {thread}; the thread is NOT promoted (R8)."
    )
    return thread


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry: ``python -m attune.roundtable.routine <name> [--dry-run]``."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a round-table routine (manual-first; R8: never self-promotes)."
    )
    parser.add_argument("name", choices=sorted(ROUTINES))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run checks and print the brief; no board writes, no LLM invocations",
    )
    args = parser.parse_args(argv)
    run_routine(ROUTINES[args.name], dry_run=args.dry_run)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
