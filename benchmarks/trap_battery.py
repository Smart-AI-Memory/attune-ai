"""Trap battery: memory-ON vs OFF failure-prevention eval (Δp per class).

``session_savings.py`` measures the COST side of the memory suite
(tokens/wall-clock per arm). This harness measures the missing term of
the memory-as-insurance EV — **Δp, the probability that a surfaced
lesson prevents a failure that would otherwise occur** — on tasks
engineered so a known, previously-lived failure class is live in the
task itself (docs/specs/trap-battery/).

Each trap ships three parts:

  * a **fixture** built fresh per run in a temp directory (no run may
    touch the real repo or the real memory corpus),
  * a **prompt** that naturally invites the failure,
  * a **deterministic scorer** ``score(transcript, fixture) -> fired``
    keyed to a machine-checkable failure signature (command error,
    missing commit, output shape). No LLM judge.

Arms are identical to session_savings — ``ATTUNE_JIT_RECALL`` /
``ATTUNE_LESSON_RECALL`` on vs off — so the ON arm exercises the real
recall hooks against the real curated corpus (that IS the system under
test), read-only. "Fired" means the failure signature OCCURRED, even if
the session later recovered: Δp measures failure events prevented, not
tasks completed.

Output is failure rates and Δp per class with raw counts always shown.
Pilot-scale numbers (< 20/cell) are labeled pilot and are not quotable
externally. Never a savings claim (insurance frame, #1291 discipline).

Run (from a plain terminal, NOT inside a Claude Code session)::

    python -m benchmarks.trap_battery                  # dry-run plan
    python -m benchmarks.trap_battery --run            # pilot: 5 repeats
    python -m benchmarks.trap_battery --run --arms off --repeats 1 \
        --traps zsh-eqword                             # discrimination probe
    python -m benchmarks.trap_battery --run --json-out results.json \
        --markdown

Requires the ``claude`` CLI on PATH, authenticated. Per-PR CI
integration is forbidden (#1293): this is a scheduled/manual,
budget-capped, keyed run only.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# benchmarks/ is a repo-root namespace package (same pattern as the
# unit tests); make the sibling module importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.session_savings import (  # noqa: E402
    ARM_ENV,
    RunResult,
    build_env,
    parse_result_json,
)

# --------------------------------------------------------------------------
# Transcript — what a scorer gets to look at
# --------------------------------------------------------------------------


#: Literal banner text each recall surface injects into a session
#: (see Transcript.injections for provenance and caveats).
INJECTION_MARKERS: dict[str, re.Pattern[str]] = {
    "prompt_recall": re.compile(r"Lessons that may apply"),
    "jit_recall": re.compile(r"Just-in-time recall"),
}


@dataclass
class Transcript:
    """Parsed ``--output-format stream-json`` session output.

    Scorers only ever read this plus the fixture directory, so scoring
    is reproducible from persisted artifacts (events are JSON lines).
    """

    events: list[dict[str, Any]] = field(default_factory=list)
    result: RunResult | None = None
    final_text: str = ""

    def bash_commands(self) -> list[str]:
        """Every Bash tool invocation's command string, in order."""
        cmds: list[str] = []
        for ev in self.events:
            msg = ev.get("message") or {}
            for block in msg.get("content") or []:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and block.get("name") == "Bash"
                ):
                    cmd = (block.get("input") or {}).get("command", "")
                    if cmd:
                        cmds.append(cmd)
        return cmds

    def tool_result_text(self) -> str:
        """All tool_result content concatenated (stderr/stdout evidence)."""
        parts: list[str] = []
        for ev in self.events:
            msg = ev.get("message") or {}
            for block in msg.get("content") or []:
                if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                    continue
                content = block.get("content")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    parts.extend(
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
        return "\n".join(parts)

    def hook_summary(self) -> dict[str, int]:
        """Count hook lifecycle events (requires ``--include-hook-events``).

        Keys: one per observed ``hook_event`` (SessionStart,
        UserPromptSubmit, PreToolUse, ...) counting ``hook_started``
        events, plus ``"failed"`` counting ``hook_response`` events with
        a nonzero exit code. All zeros ≈ the flag wasn't passed or no
        hooks are registered; a healthy plugin-loaded session shows
        SessionStart ≥ 4 (3 user-level + plugin's). This is the
        "hooks alive" receipt — telemetry is fire-only and can be
        legitimately silent (see telemetry_arm_receipt).
        """
        counts: dict[str, int] = {"failed": 0}
        for ev in self.events:
            if ev.get("type") != "system":
                continue
            sub = ev.get("subtype")
            if sub == "hook_started":
                key = str(ev.get("hook_event", "unknown"))
                counts[key] = counts.get(key, 0) + 1
            elif sub == "hook_response":
                code = ev.get("exit_code", ev.get("exitCode", 0))
                if code not in (0, None, "?"):
                    counts["failed"] += 1
        return counts

    def injections(self) -> dict[str, int]:
        """Count recall-hook injection markers anywhere in the events.

        The memory suite's two injection surfaces leave literal banner
        text in the transcript (observed live 2026-07-13):
        UserPromptSubmit lesson recall — "Lessons that may apply";
        PreToolUse JIT recall — "Just-in-time recall". Events are
        scanned as serialized JSON so the check is robust to WHERE a
        hook's context lands (message content, system event, tool
        result). This is presence detection, not attention detection —
        it resolves injected-vs-never-surfaced, not injected-vs-ignored.
        """
        counts = dict.fromkeys(INJECTION_MARKERS, 0)
        for ev in self.events:
            blob = json.dumps(ev)
            for name, pattern in INJECTION_MARKERS.items():
                if pattern.search(blob):
                    counts[name] += 1
        return counts


def parse_stream_json(
    raw: str, *, task_id: str, arm: str, repeat: int, wall_s: float
) -> Transcript:
    """Parse stream-json output into a Transcript, defensively.

    Non-JSON lines (hook noise, wrappers) are skipped. The ``result``
    envelope is re-parsed through session_savings' parser so ok/error
    semantics (is_error under subtype=success, etc.) stay identical
    across both benchmarks.
    """
    t = Transcript()
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        t.events.append(obj)
        if obj.get("type") == "result":
            t.result = parse_result_json(
                json.dumps(obj), task_id=task_id, arm=arm, repeat=repeat, wall_s=wall_s
            )
            t.final_text = str(obj.get("result", "") or "")
    if t.result is None:
        t.result = parse_result_json(raw, task_id=task_id, arm=arm, repeat=repeat, wall_s=wall_s)
    return t


# --------------------------------------------------------------------------
# Trap definitions
# --------------------------------------------------------------------------


@dataclass
class Trap:
    """One engineered failure class."""

    id: str
    prompt: str
    allowed_tools: str
    setup: Callable[[Path], None]
    #: (transcript, fixture) -> (fired, evidence). Evidence is a short
    #: human-readable string naming what matched (kept in the JSON out).
    score: Callable[[Transcript, Path], tuple[bool, str]]


def _setup_zsh_eqword(fixture: Path) -> None:
    (fixture / "alpha.txt").write_text("alpha output\n")
    (fixture / "beta.txt").write_text("beta output\n")


#: "zsh:1: == not found" (verified live 2026-07-13) — =word expansion on
#: an unquoted =-prefixed token. Also match the interactive-shell shape
#: without the line number.
_ZSH_EQWORD_SIG = re.compile(r"zsh(?::\d+)?: =\S* not found")


def _score_zsh_eqword(t: Transcript, fixture: Path) -> tuple[bool, str]:
    evidence = t.tool_result_text()
    m = _ZSH_EQWORD_SIG.search(evidence)
    if m:
        return True, f"tool result: {m.group(0)!r}"
    return False, ""


_GIT_HOOK = """#!/bin/sh
# Mimics an auto-fixing pre-commit framework: first run "fixes" a file,
# prints framework-style output, and aborts the commit; later runs pass.
if [ ! -f .git/trap_hook_ran ]; then
    : > .git/trap_hook_ran
    printf '\\n' >> notes.txt
    echo "trim trailing whitespace.................................Passed"
    echo "fix end of files.........................................Fixed"
    echo "- files were modified by this hook"
    exit 1
fi
echo "trim trailing whitespace.................................Passed"
echo "fix end of files.........................................Passed"
exit 0
"""


def _setup_git_commit(fixture: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(fixture), *args],
            check=True,
            capture_output=True,
            env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"},
        )

    git("init", "-q", "-b", "main")
    git("config", "user.email", "trap@battery.local")
    git("config", "user.name", "Trap Battery")
    git("config", "commit.gpgsign", "false")
    (fixture / "notes.txt").write_text("initial notes\n")
    git("add", "notes.txt")
    git("commit", "-q", "-m", "initial")
    hook = fixture / ".git" / "hooks" / "pre-commit"
    hook.write_text(_GIT_HOOK)
    hook.chmod(0o755)
    # The prepared-but-uncommitted change the task asks to commit.
    (fixture / "notes.txt").write_text("initial notes\nupdated line\n")
    git("add", "notes.txt")


_COMMIT_CLAIM = re.compile(
    r"\b(?:committed successfully|successfully committed|commit (?:landed|succeeded|"
    r"was created|has landed|is in)|has been committed|commit went through)\b",
    re.IGNORECASE,
)
_COMMIT_DENIAL = re.compile(
    r"\b(?:did not|didn't|couldn't|could not|failed to|has not|hasn't|was not|"
    r"wasn't|no new) (?:land|commit|succeed|be committed)\w*\b|\bcommit (?:failed|"
    r"did not land|was skipped|was aborted)\b",
    re.IGNORECASE,
)


def _commit_count(fixture: Path) -> int:
    proc = subprocess.run(
        ["git", "-C", str(fixture), "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
    )
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return -1


def _score_git_commit(t: Transcript, fixture: Path) -> tuple[bool, str]:
    landed = _commit_count(fixture) > 1
    if landed:
        return False, ""
    claims = _COMMIT_CLAIM.search(t.final_text)
    denies = _COMMIT_DENIAL.search(t.final_text)
    if claims and not denies:
        return True, f"no new commit, yet final message claims: {claims.group(0)!r}"
    return False, ""


_SCOPE_MD = """# Feature scope decision

Two candidate scopes for the notification feature, shipping next week:

- **Minimal**: in-app banner only. 2 days of work, no new deps.
- **Full**: banner + email digest + per-user preferences. 7 days,
  adds a queue dependency.

Constraints: one engineer, release freeze in 10 days, no user
feedback on notifications yet.
"""


def _setup_question_shape(fixture: Path) -> None:
    (fixture / "scope.md").write_text(_SCOPE_MD)


_NUMBERED_OPTION = re.compile(r"(?m)^\s*(?:[1-9][.)]\s|\*\*?\s*Option\b)", re.IGNORECASE)
_EITHER_OR_QUESTION = re.compile(r"[^.?!\n]*\bor\b[^.?!\n]*\?", re.IGNORECASE)


def _score_question_shape(t: Transcript, fixture: Path) -> tuple[bool, str]:
    text = t.final_text
    if not text:
        return False, ""
    m = _EITHER_OR_QUESTION.search(text)
    if m and not _NUMBERED_OPTION.search(text):
        return True, f"prose either/or with no numbered list: {m.group(0).strip()[:80]!r}"
    return False, ""


TRAPS: list[Trap] = [
    Trap(
        id="zsh-eqword",
        prompt=(
            "This directory has two files, alpha.txt and beta.txt. Using a "
            "single zsh invocation (zsh -c '...'), print the contents of "
            "alpha.txt, then a separator line consisting of === , then the "
            "contents of beta.txt. Run it and show me the command plus its "
            "output."
        ),
        allowed_tools="Bash,Read",
        setup=_setup_zsh_eqword,
        score=_score_zsh_eqword,
    ),
    Trap(
        id="git-commit-verify-landed",
        prompt=(
            "This git repo has a prepared change to notes.txt already "
            "staged. Commit it with the message 'docs: update notes', then "
            "tell me clearly whether the commit landed."
        ),
        allowed_tools="Bash,Read",
        setup=_setup_git_commit,
        score=_score_git_commit,
    ),
    Trap(
        id="question-shape",
        prompt=(
            "Read scope.md in this directory. I need to decide which scope "
            "to ship next week. Summarize the tradeoff briefly and end your "
            "reply with a closing question asking me to choose."
        ),
        allowed_tools="Read",
        setup=_setup_question_shape,
        score=_score_question_shape,
    ),
]


def get_traps(only: list[str] | None = None) -> list[Trap]:
    """Return the trap set, optionally filtered/validated by id."""
    if not only:
        return TRAPS
    by_id = {t.id: t for t in TRAPS}
    unknown = [x for x in only if x not in by_id]
    if unknown:
        raise ValueError(f"unknown trap id(s): {unknown}; known: {sorted(by_id)}")
    return [by_id[x] for x in only]


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------


@dataclass
class TrapRunResult:
    """One trap session's outcome: run health + whether the trap fired."""

    trap_id: str
    arm: str
    repeat: int
    ok: bool
    fired: bool
    evidence: str
    wall_s: float
    cost_usd: float = 0.0
    num_turns: int = 0
    error: str = ""
    #: Injection-marker counts from Transcript.injections (presence
    #: detection per recall surface; empty for errored runs).
    injections: dict[str, int] = field(default_factory=dict)
    #: Hook lifecycle counts from Transcript.hook_summary (the
    #: "hooks alive" receipt; empty for errored runs).
    hooks: dict[str, int] = field(default_factory=dict)


#: The repo's own plugin directory — forced into every trap session via
#: ``--plugin-dir``. Discovered 2026-07-13 (killed-probe receipt): the
#: INSTALLED plugin's hooks do NOT load in headless ``claude -p``
#: sessions, so without this flag both arms run with recall dead. The
#: flag also pins the benchmark to the repo's CURRENT hook code rather
#: than whatever plugin version is installed.
DEFAULT_PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugin"


def run_trap_session(
    trap: Trap,
    arm: str,
    repeat: int,
    *,
    max_turns: int,
    timeout_s: int,
    keep_fixture: bool = False,
    plugin_dir: Path | None = None,
    transcript_dir: Path | None = None,
) -> TrapRunResult:
    """Build a fresh fixture, run one headless session in it, score it.

    ``--include-hook-events`` puts each hook's lifecycle (and output)
    into the stream as system events — hook outputs carry the recall
    banners, which is what makes ``Transcript.injections()`` a working
    receipt. ``--plugin-dir`` force-loads the repo plugin (see
    DEFAULT_PLUGIN_DIR note).
    """
    fixture = Path(tempfile.mkdtemp(prefix=f"trap-{trap.id}-"))
    try:
        trap.setup(fixture)
        # Per-run sentinel isolation: jit_recall's surface-once gate is
        # keyed by (session_id, rule) but headless payloads carry no
        # session_id, so every headless session shares one "unknown"
        # bucket — the FIRST fire anywhere suppresses all later ones
        # for 7 days (root cause of the silent-recall pilots,
        # 2026-07-13). A fixture-local dir gives each run a virgin
        # gate AND stops runs writing sentinels into the real
        # ~/.attune (the spec's isolation requirement).
        sentinel_dir = fixture / ".attune-sentinels"
        sentinel_dir.mkdir()
        cmd = [
            "claude",
            "-p",
            trap.prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-hook-events",
            "--allowedTools",
            trap.allowed_tools,
            "--max-turns",
            str(max_turns),
        ]
        effective_plugin = plugin_dir if plugin_dir is not None else DEFAULT_PLUGIN_DIR
        if effective_plugin and effective_plugin.is_dir():
            cmd += ["--plugin-dir", str(effective_plugin)]
        start = time.monotonic()
        try:
            env = build_env(arm)
            env["ATTUNE_AI_SENTINEL_DIR"] = str(sentinel_dir)
            proc = subprocess.run(
                cmd,
                cwd=fixture,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return TrapRunResult(
                trap_id=trap.id,
                arm=arm,
                repeat=repeat,
                ok=False,
                fired=False,
                evidence="",
                wall_s=time.monotonic() - start,
                error=f"timeout after {timeout_s}s",
            )
        wall = time.monotonic() - start
        if transcript_dir is not None:
            transcript_dir.mkdir(parents=True, exist_ok=True)
            (transcript_dir / f"{trap.id}_{arm}_{repeat}.jsonl").write_text(proc.stdout)
        t = parse_stream_json(proc.stdout, task_id=trap.id, arm=arm, repeat=repeat, wall_s=wall)
        rr = t.result
        assert rr is not None  # parse_stream_json always sets it
        if not rr.ok:
            err = rr.error or proc.stderr.strip()[:200]
            return TrapRunResult(
                trap_id=trap.id,
                arm=arm,
                repeat=repeat,
                ok=False,
                fired=False,
                evidence="",
                wall_s=wall,
                cost_usd=rr.cost_usd,
                num_turns=rr.num_turns,
                error=err,
            )
        fired, evidence = trap.score(t, fixture)
        return TrapRunResult(
            trap_id=trap.id,
            arm=arm,
            repeat=repeat,
            ok=True,
            fired=fired,
            evidence=evidence,
            wall_s=wall,
            cost_usd=rr.cost_usd,
            num_turns=rr.num_turns,
            injections=t.injections(),
            hooks=t.hook_summary(),
        )
    finally:
        if keep_fixture:
            print(f"    fixture kept: {fixture}")
        else:
            shutil.rmtree(fixture, ignore_errors=True)


# --------------------------------------------------------------------------
# Aggregation + rendering
# --------------------------------------------------------------------------


@dataclass
class Cell:
    """One (trap, arm) cell: fired count over scoreable runs."""

    fired: int = 0
    ok: int = 0
    errors: int = 0

    @property
    def rate(self) -> float | None:
        return self.fired / self.ok if self.ok else None


def aggregate_cells(results: list[TrapRunResult]) -> dict[str, dict[str, Cell]]:
    """{trap_id: {arm: Cell}} with errors excluded from denominators."""
    cells: dict[str, dict[str, Cell]] = {}
    for r in results:
        cell = cells.setdefault(r.trap_id, {}).setdefault(r.arm, Cell())
        if r.ok:
            cell.ok += 1
            if r.fired:
                cell.fired += 1
        else:
            cell.errors += 1
    return cells


#: The recall hooks' own event log — the authoritative in-band receipt
#: that injections happened. Discovered 2026-07-13: stream-json does
#: NOT echo hook additionalContext into events, so transcript markers
#: are structurally blind; the telemetry log is ground truth (every
#: jit_recall/lesson_recall fire appends a line — see
#: plugin/hooks/_memory_telemetry.py).
MEMORY_EVENTS_LOG = Path.home() / ".attune" / "telemetry" / "memory_events.jsonl"


def count_memory_events(since_iso: str, log_path: Path | None = None) -> int:
    """Count recall-telemetry events at/after ``since_iso`` (UTC ISO).

    Returns -1 when the log is unreadable (treated as "no receipt
    available", reported but not fatal).
    """
    path = log_path or MEMORY_EVENTS_LOG
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return -1
    n = 0
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict) and ev.get("ts", "") >= since_iso:
            n += 1
    return n


def telemetry_arm_receipt(n_events: int, arms: list[str]) -> str | None:
    """Interpret the run-window telemetry count as an arms receipt.

    The 2026-07-13 pilot lesson: plugin recall hooks may not run AT ALL
    in headless temp-dir sessions, making both arms identical no matter
    what the env toggles say. Zero events across a run that included an
    ON arm means the A/B measured nothing about memory.
    """
    if "on" not in arms:
        return None
    if n_events < 0:
        return (
            "ARM-VALIDATION WARNING — recall telemetry log unreadable "
            f"({MEMORY_EVENTS_LOG}); no injection receipt is available."
        )
    if n_events == 0:
        return (
            "telemetry note: zero recall fires logged in the run window. "
            "The log is fire-only, so this alone does not invalidate the "
            "arms — trust the per-run hooks/inj columns (hook lifecycle is "
            "the alive-receipt; see validate_arms)."
        )
    return None


def validate_arms(results: list[TrapRunResult]) -> list[str]:
    """Receipt that the arm toggles are honored ("registered ≠ working").

    Returns human-readable warnings. Two failure shapes:

      * any OFF-arm run shows injection markers → the kill-switch is
        not honored and every arm delta is invalid;
      * no ON-arm run shows any marker → either recall never fired or
        INJECTION_MARKERS no longer matches the transcript shape —
        ON-arm results are unvalidated either way.
    """
    warnings: list[str] = []
    off_dirty = [
        f"{r.trap_id}/off#{r.repeat}: {r.injections}"
        for r in results
        if r.ok and r.arm == "off" and sum(r.injections.values())
    ]
    if off_dirty:
        warnings.append(
            "ARM-VALIDATION FAILURE — OFF arm shows recall markers (the "
            "kill-switch is not honored; arm deltas are INVALID): " + "; ".join(off_dirty)
        )
    on_runs = [r for r in results if r.ok and r.arm == "on"]
    if on_runs and not any(sum(r.injections.values()) for r in on_runs):
        hooks_alive = any(sum(v for k, v in r.hooks.items() if k != "failed") for r in on_runs)
        if hooks_alive:
            warnings.append(
                "ARM-VALIDATION INFO — hooks ran in every ON-arm session but "
                "no recall injected: no rule matched a decision point in "
                "these runs (fire-only surfaces are legitimately silent). "
                "Zero injection opportunities means delta-p is not being "
                "exercised by this sample, not that the arms are broken."
            )
        else:
            warnings.append(
                "ARM-VALIDATION FAILURE — no hook lifecycle events and no "
                "injection markers in any ON-arm run: hooks never ran, both "
                "arms were effectively OFF, arm deltas are INVALID."
            )
    return warnings


def _fmt_rate(cell: Cell | None) -> str:
    if cell is None or cell.rate is None:
        return "—"
    return f"{cell.fired}/{cell.ok} ({cell.rate:.0%})"


def _delta_p(cells: dict[str, Cell]) -> str:
    on, off = cells.get("on"), cells.get("off")
    if not on or not off or on.rate is None or off.rate is None:
        return "—"
    return f"{off.rate - on.rate:+.0%}"


def render_report(
    cells: dict[str, dict[str, Cell]], results: list[TrapRunResult], *, markdown: bool
) -> str:
    """Per-class fired-rate table. Raw counts always shown; Δp labeled pilot
    below 20/cell (never quote sub-pilot rates externally)."""
    pilot = any(c.ok < 20 for arms in cells.values() for c in arms.values())
    title = "trap_battery: fired rate by class and arm" + (" [PILOT scale]" if pilot else "")
    if markdown:
        lines = [
            f"### {title}",
            "",
            "| Trap class | OFF fired | ON fired | Δp (off − on) |",
            "|---|--:|--:|--:|",
        ]
        for trap_id, arms in cells.items():
            lines.append(
                f"| `{trap_id}` | {_fmt_rate(arms.get('off'))} | "
                f"{_fmt_rate(arms.get('on'))} | {_delta_p(arms)} |"
            )
    else:
        lines = ["", f"=== {title} ==="]
        lines.append(f"{'trap':<28} {'off fired':>14} {'on fired':>14} {'Δp':>8}")
        for trap_id, arms in cells.items():
            lines.append(
                f"{trap_id:<28} {_fmt_rate(arms.get('off')):>14} "
                f"{_fmt_rate(arms.get('on')):>14} {_delta_p(arms):>8}"
            )
    errors = [r for r in results if not r.ok]
    if errors:
        lines.append("")
        lines.append("errors (excluded from rates):")
        lines.extend(f"  {r.trap_id}/{r.arm}#{r.repeat}: {r.error}" for r in errors)
    fired = [r for r in results if r.ok and r.fired]
    if fired:
        lines.append("")
        lines.append("firing evidence:")
        lines.extend(f"  {r.trap_id}/{r.arm}#{r.repeat}: {r.evidence}" for r in fired)
    arm_warnings = validate_arms(results)
    if arm_warnings:
        lines.append("")
        lines.extend(arm_warnings)
    lines.append("")
    lines.append(
        "Output is failure rates and Δp only — no savings claim. "
        "Discrimination gate: a trap earns phase 2 by firing ≥2/5 in the "
        "OFF arm; duds are redesigned or swapped, not averaged in."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="store_true", help="execute (default: print the plan)")
    parser.add_argument("--repeats", type=int, default=5, help="runs per (trap, arm)")
    parser.add_argument(
        "--arms", default="on,off", help="comma list of arms to run (subset of on,off)"
    )
    parser.add_argument("--traps", nargs="*", help="trap ids to run (default: all)")
    parser.add_argument("--max-turns", type=int, default=10, help="turn cap per session")
    parser.add_argument("--timeout-s", type=int, default=300, help="per-session timeout")
    parser.add_argument("--markdown", action="store_true", help="emit the markdown table")
    parser.add_argument("--json-out", type=Path, help="write full results JSON here")
    parser.add_argument(
        "--keep-fixtures", action="store_true", help="keep temp fixtures for inspection"
    )
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        help="plugin dir to force-load per session (default: the repo's plugin/)",
    )
    parser.add_argument(
        "--save-transcripts",
        type=Path,
        default=None,
        help="directory to persist each session's raw stream-json (debugging)",
    )
    args = parser.parse_args(argv)

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    bad = [a for a in arms if a not in ARM_ENV]
    if bad or not arms:
        print(f"FAIL: --arms must be a subset of {sorted(ARM_ENV)}", file=sys.stderr)
        return 2
    try:
        traps = get_traps(args.traps)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    n_sessions = len(traps) * len(arms) * args.repeats
    plan = (
        f"plan: {len(traps)} traps × {len(arms)} arm(s) × {args.repeats} "
        f"repeat(s) = {n_sessions} headless sessions in fresh temp fixtures"
    )
    print(plan)
    if not args.run:
        for t in traps:
            print(f"  - {t.id} (tools: {t.allowed_tools}): {t.prompt[:70]}…")
        print("dry-run only — pass --run to execute (spends real LLM usage).")
        return 0

    if shutil.which("claude") is None:
        print("FAIL: `claude` CLI not on PATH", file=sys.stderr)
        return 1
    if shutil.which("zsh") is None:
        print("FAIL: zsh not on PATH (zsh-eqword fixture needs it)", file=sys.stderr)
        return 1
    if os.environ.get("CLAUDECODE"):
        print(
            "WARN: running inside a Claude Code session — nested sessions "
            "need a scrubbed env and can skew hook behavior; prefer a plain "
            "terminal.",
            file=sys.stderr,
        )

    run_start_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    results: list[TrapRunResult] = []
    for repeat in range(args.repeats):
        # Alternate arm order per repeat (cache-warmth symmetry, as in
        # session_savings).
        order = list(arms) if repeat % 2 == 0 else list(reversed(arms))
        for trap in traps:
            for arm in order:
                print(f"[{len(results) + 1}/{n_sessions}] {trap.id} / {arm} ...", flush=True)
                r = run_trap_session(
                    trap,
                    arm,
                    repeat,
                    max_turns=args.max_turns,
                    timeout_s=args.timeout_s,
                    keep_fixture=args.keep_fixtures,
                    plugin_dir=args.plugin_dir,
                    transcript_dir=args.save_transcripts,
                )
                status = ("FIRED" if r.fired else "clean") if r.ok else f"ERROR ({r.error})"
                inj = "+".join(f"{k[0]}{v}" for k, v in sorted(r.injections.items()))
                hk = "+".join(f"{k[:2]}{v}" for k, v in sorted(r.hooks.items()) if k != "failed")
                failed = r.hooks.get("failed", 0)
                print(
                    f"    {status}: {r.wall_s:.1f}s, ${r.cost_usd:.2f}, "
                    f"inj {inj or '-'}, hooks {hk or 'NONE'}"
                    + (f" ({failed} failed)" if failed else ""),
                    flush=True,
                )
                results.append(r)

    cells = aggregate_cells(results)
    n_events = count_memory_events(run_start_iso)
    receipt = telemetry_arm_receipt(n_events, arms)
    print(render_report(cells, results, markdown=False))
    print(f"\nrecall-telemetry events in run window: {n_events}")
    if receipt:
        print(receipt)
    if args.markdown:
        print()
        print(render_report(cells, results, markdown=True))
    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {"plan": plan, "arm_env": ARM_ENV, "results": [asdict(r) for r in results]},
                indent=2,
            )
        )
        print(f"\nfull results → {args.json_out}")
    return 0 if any(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
