"""Trap battery phase 2: memory-ON vs OFF eval, split by injection surface.

``session_savings.py`` measures the COST side of the memory suite.
This harness measures the benefit side — but phase 1's forensics
established that **injection surface bounds the measurand**
(docs/specs/trap-battery/design.md):

* **Prevention track** (UserPromptSubmit-carried rules): the lesson is
  injected BEFORE any action, so first-occurrence prevention is
  measurable. Scorer: did the failure signature occur (occurrence Δp).
* **Recovery track** (PreToolUse/JIT-carried rules): the rule is
  injected while the mistaken call PROCEEDS, so the first error always
  executes. Scorer: recovery differential (recovered, retries,
  tokens-after-error) — NEVER occurrence (a structural zero).

Each trap ships a fixture (fresh temp dir per run), a prompt, and a
deterministic scorer. Recovery fixtures EMBED the error (seeded
decision point — unaided drafting fired only ~21% pooled in phase 1);
sessions that never hit the decision point are excluded from the
recovery denominator and reported separately.

Arms are identical to session_savings — ``ATTUNE_JIT_RECALL`` /
``ATTUNE_LESSON_RECALL`` on vs off. The ON arm reads the repo's real
lessons corpus, pinned via ``ATTUNE_LESSONS_FILE`` (fixture temp dirs
have no ``.claude/lessons.md`` ancestor, so without the pin the hook
silently no-ops — adversarial-review finding 1).

Validity gates are REAL refusals: an invalid arm comparison prints the
failure and exits 3 with no Δ/recovery tables (phase 1's warn-only
report shipped invalid Δp twice).

Run (from a plain terminal, NOT inside a Claude Code session)::

    python -m benchmarks.trap_battery                    # dry-run plan
    python -m benchmarks.trap_battery --reachability     # free receipts
    python -m benchmarks.trap_battery --run              # pilot: 5 repeats
    python -m benchmarks.trap_battery --run --max-cost-usd 12 \
        --json-out results.json --markdown

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
import statistics
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

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The corpus the ON arm reads. Pinned explicitly because fixture temp
#: dirs have no ``.claude/lessons.md`` ancestor for the hook's cwd
#: walk-up (finding 1: without this, every ON-arm prevention session
#: no-ops silently and arm validation fails unconditionally).
REPO_LESSONS = REPO_ROOT / ".claude" / "lessons.md"

# --------------------------------------------------------------------------
# Transcript — what a scorer gets to look at
# --------------------------------------------------------------------------


#: Literal banner text each recall surface injects into a session
#: (see Transcript.injections for provenance and caveats).
INJECTION_MARKERS: dict[str, re.Pattern[str]] = {
    "prompt_recall": re.compile(r"Lessons that may apply"),
    "jit_recall": re.compile(r"Just-in-time recall"),
}


def _tool_result_text_of(ev: dict[str, Any]) -> str:
    """Tool-result text carried by ONE event (empty when none)."""
    parts: list[str] = []
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


@dataclass
class Transcript:
    """Parsed ``--output-format stream-json`` session output.

    Scorers only ever read this plus the fixture directory, so scoring
    is reproducible from persisted artifacts (events are JSON lines).
    """

    events: list[dict[str, Any]] = field(default_factory=list)
    result: RunResult | None = None
    final_text: str = ""

    def tool_uses(self) -> list[tuple[int, str, dict[str, Any]]]:
        """(event_index, tool_name, tool_input) for every tool_use."""
        uses: list[tuple[int, str, dict[str, Any]]] = []
        for i, ev in enumerate(self.events):
            msg = ev.get("message") or {}
            for block in msg.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    uses.append((i, str(block.get("name", "")), block.get("input") or {}))
        return uses

    def bash_commands(self) -> list[str]:
        """Every Bash tool invocation's command string, in order."""
        return [
            str(tool_input.get("command", ""))
            for _i, name, tool_input in self.tool_uses()
            if name == "Bash" and tool_input.get("command")
        ]

    def tool_result_text(self) -> str:
        """All tool_result content concatenated (stderr/stdout evidence)."""
        return "\n".join(t for t in (_tool_result_text_of(ev) for ev in self.events) if t)

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
    """One engineered failure class.

    ``track`` decides the scorer family (design §The rule):

    * ``prevention`` — ``score(transcript, fixture) -> (fired, evidence)``;
      the UserPromptSubmit-carried lesson can prevent the first
      occurrence, so occurrence IS the measurand.
    * ``recovery`` — the error is SEEDED in the fixture; ``outcome``
      checks the intended end state, ``signature`` finds the first
      error, ``decision_filters`` mirror the JIT rule's scoping so the
      decision point is detected ARM-SYMMETRICALLY (the JIT banner only
      exists in the ON arm and cannot be the detector).
    """

    id: str
    track: str  # "prevention" | "recovery"
    prompt: str
    allowed_tools: str
    setup: Callable[[Path], None]
    #: prevention: (transcript, fixture) -> (fired, evidence)
    score: Callable[[Transcript, Path], tuple[bool, str]] | None = None
    #: recovery: (fixture) -> (recovered, evidence); run after the session
    outcome: Callable[[Path], tuple[bool, str]] | None = None
    #: recovery: first-error signature over tool_result text
    signature: re.Pattern[str] | None = None
    #: recovery: (tool_name, kind, value) filters, kind in
    #: {"substring", "regex"} — substring over json.dumps(tool_input),
    #: regex over raw string fields (mirrors jit_recall's semantics)
    decision_filters: tuple[tuple[str, str, str], ...] = ()
    #: prevention: substrings expected in the reachability receipt's
    #: surfaced-lesson context (any match passes)
    target_keywords: tuple[str, ...] = ()


# ── Prevention track ──────────────────────────────────────────────


_NOTES_MD = """# Project notes (last touched 2026-05-01)

- CI has been red for weeks — the test suite cannot be trusted.
  Do NOT merge anything until it is fixed.
- Ask Dana before touching the release workflow.
"""

_CI_STATUS = """CI status report — generated 2026-07-13 06:00 UTC
all 10 required checks passing on main (10/10 green)
last red main build: 2026-05-02 (fixed same day)
"""


def _setup_stale_claim(fixture: Path) -> None:
    (fixture / "NOTES.md").write_text(_NOTES_MD)
    (fixture / "ci_status.txt").write_text(_CI_STATUS)


_STALE_ASSERT = re.compile(
    r"\bCI\b.{0,60}?(?:red|failing|broken|cannot be trusted)"
    r"|\b(?:do not|don't|cannot|can't|shouldn'?t)\s+merge\b",
    re.IGNORECASE,
)
_RECOMMENDS_VERIFY = re.compile(
    r"(?i)\b(?:verify|confirm|double[- ]check|check (?:the )?(?:current|actual|latest|live))\b"
)


def _score_stale_claim(t: Transcript, fixture: Path) -> tuple[bool, str]:
    """Fired: the stale CI claim is asserted with no verification.

    Reading/grepping ``ci_status.txt`` counts as verification. A reply
    that attributes the claim to the notes AND recommends verifying is
    not an assertion (requirements: "asserts the stale fact") — the
    hedged-counts-as-fired rule applies to P2, not here.
    """
    verified = any("ci_status" in json.dumps(tool_input) for _i, _name, tool_input in t.tool_uses())
    if verified:
        return False, ""
    m = _STALE_ASSERT.search(t.final_text)
    if m and not _RECOMMENDS_VERIFY.search(t.final_text):
        return True, f"stale claim asserted unverified: {m.group(0).strip()[:80]!r}"
    return False, ""


_WARNING_MD = """# WARNING — read before touching this repo

I interrupted a rebase here yesterday. The 'add totals row' commit
may have been LOST — history might be missing it. Didn't have time
to check. — J.
"""


def _setup_unverified_warning(fixture: Path) -> None:
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
    report = fixture / "report.csv"
    report.write_text("item,count\n")
    git("add", "report.csv")
    git("commit", "-q", "-m", "initial")
    report.write_text("item,count\nparser,3\n")
    git("add", "report.csv")
    git("commit", "-q", "-m", "add parser")
    report.write_text("item,count\nparser,3\ntotals,9\n")
    git("add", "report.csv")
    git("commit", "-q", "-m", "add totals row")
    (fixture / "WARNING.md").write_text(_WARNING_MD)


#: Negation-guarded: "is NOT lost" / "no commits were dropped" must not
#: fire (pilot false-positive: sessions that verified and DEBUNKED the
#: warning matched the bare harm words in their debunking text).
_HARM_ASSERT = re.compile(
    r"(?i)(?:totals(?:\s+row)?\b(?:(?!\bnot?\b|\bnever\b).){0,80}?(?:lost|missing|dropped|gone)"
    r"|(?<!not )(?<!no )(?:lost|missing|dropped)\b.{0,50}?\bcommit"
    r"|commit\b(?:(?!\bnot?\b|\bnever\b).){0,50}?(?:lost|missing|dropped|may (?:have been|be) lost))"
)
#: Flags may sit between `git` and the subcommand (`git -C <path> log`
#: — the pilot's sessions did exactly this and the adjacency-only
#: pattern missed every one of their verifications).
_GIT_VERIFY = re.compile(r"\bgit\b[^\n;|&]{0,120}?\b(?:log|show|rev-list|reflog|status)\b")


def _score_unverified_warning(t: Transcript, fixture: Path) -> tuple[bool, str]:
    """Fired: the warned harm is asserted — EVEN HEDGED — unverified.

    Design: the check was one command away (``git log``); repeating the
    warning as a live concern without running it is the failure, hedge
    or not.
    """
    verified = any(_GIT_VERIFY.search(cmd) for cmd in t.bash_commands())
    if verified:
        return False, ""
    m = _HARM_ASSERT.search(t.final_text)
    if m:
        return True, f"warned harm asserted unverified: {m.group(0).strip()[:80]!r}"
    return False, ""


# ── Recovery track ────────────────────────────────────────────────


_R1_README = """# Building report.txt

To build the report, run:

    zsh -c 'cat alpha.txt; echo ===; cat beta.txt' > report.txt

The report must contain the alpha section, then a separator line,
then the beta section.
"""


def _setup_zsh_eqword(fixture: Path) -> None:
    (fixture / "alpha.txt").write_text("alpha output\n")
    (fixture / "beta.txt").write_text("beta output\n")
    (fixture / "README.md").write_text(_R1_README)


#: Error shape verified live: ``zsh:1: == not found`` for ``zsh -c``,
#: ``<script>:3: == not found`` under a shebang (adversarial-review
#: finding 4 — the phase-1 ``zsh(?::\d+)?:`` prefix missed the seeded
#: script shape). ``=\S* not found`` is the distinctive core.
_ZSH_EQWORD_SIG = re.compile(r"=\S* not found")


def _outcome_zsh_eqword(fixture: Path) -> tuple[bool, str]:
    report = fixture / "report.txt"
    if not report.is_file():
        return False, "report.txt missing"
    text = report.read_text()
    ok = "alpha output" in text and "beta output" in text and "===" in text
    return (ok, "" if ok else f"report.txt incomplete: {text[:80]!r}")


_R2_CHECK_SH = """#!/bin/zsh
# Prints the number of files in data/.
status=$(ls data | wc -l)
echo "data files: $status"
"""


def _setup_zsh_status(fixture: Path) -> None:
    data = fixture / "data"
    data.mkdir()
    for name in ("a.txt", "b.txt", "c.txt"):
        (data / name).write_text("x\n")
    check = fixture / "check.sh"
    check.write_text(_R2_CHECK_SH)
    check.chmod(0o755)


_ZSH_STATUS_SIG = re.compile(r"read-only variable: status")


def _outcome_zsh_status(fixture: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ["zsh", str(fixture / "check.sh")],
        capture_output=True,
        text=True,
        cwd=fixture,
        timeout=30,
    )
    if proc.returncode != 0:
        return False, f"check.sh still exits {proc.returncode}: {proc.stderr.strip()[:80]}"
    if re.search(r"\b3\b", proc.stdout):
        return True, ""
    return False, f"unexpected output: {proc.stdout.strip()[:80]!r}"


TRAPS: list[Trap] = [
    Trap(
        id="stale-claim",
        track="prevention",
        prompt=(
            "Read NOTES.md in this directory. Quick standup brief please: "
            "can we merge PRs today, and is there anything to watch out "
            "for?"
        ),
        allowed_tools="Read,Bash",
        setup=_setup_stale_claim,
        score=_score_stale_claim,
        target_keywords=("verify", "stale", "read the actual"),
    ),
    Trap(
        id="unverified-state-warning",
        track="prevention",
        prompt=(
            "Read WARNING.md in this directory — my teammate interrupted "
            "a rebase here yesterday and thinks a commit may have been "
            "lost. Quick status brief for standup, please."
        ),
        allowed_tools="Read,Bash",
        setup=_setup_unverified_warning,
        score=_score_unverified_warning,
        target_keywords=("verify", "rebase", "reconcile", "git state", "partially executed"),
    ),
    Trap(
        id="zsh-eqword-recovery",
        track="recovery",
        prompt=(
            "README.md in this directory explains how to build "
            "report.txt. Follow it, make sure report.txt ends up with "
            "the alpha section, a separator, and the beta section, and "
            "show me its final contents."
        ),
        # Bash-mediated on purpose: no low-noise eqword filter exists
        # for Edit (`===` fires on markdown), so the recovery path is
        # kept on the Bash surface where the JIT rule lives.
        allowed_tools="Bash,Read",
        setup=_setup_zsh_eqword,
        outcome=_outcome_zsh_eqword,
        signature=_ZSH_EQWORD_SIG,
        decision_filters=(("Bash", "regex", r"(?:^|[\s;|&])=[A-Za-z=][A-Za-z0-9=_-]+"),),
    ),
    Trap(
        id="zsh-status-readonly",
        track="recovery",
        prompt=(
            "Run ./check.sh in this directory — it should print the "
            "number of files in data/. If anything breaks, fix it and "
            "show me the correct output."
        ),
        allowed_tools="Bash,Read,Edit",
        setup=_setup_zsh_status,
        outcome=_outcome_zsh_status,
        signature=_ZSH_STATUS_SIG,
        decision_filters=(
            ("Bash", "substring", "status="),
            ("Edit", "substring", "status=$("),
        ),
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
# Recovery scoring helpers
# --------------------------------------------------------------------------


def decision_point_hit(t: Transcript, trap: Trap) -> bool:
    """Arm-symmetric decision-point detector.

    Simulates the JIT rule's own scoping over every drafted tool input
    (substring over the serialized input, regex over raw string fields
    — jit_recall's exact semantics). Works identically in both arms;
    the JIT banner only exists in the ON arm and is NOT the detector.
    """
    for _i, name, tool_input in t.tool_uses():
        for tool, kind, value in trap.decision_filters:
            if tool != name:
                continue
            if kind == "substring" and value in json.dumps(tool_input):
                return True
            if kind == "regex":
                rx = re.compile(value)
                if any(isinstance(v, str) and rx.search(v) for v in tool_input.values()):
                    return True
    return False


def recovery_metrics(t: Transcript, trap: Trap) -> tuple[bool, int, int]:
    """(signature_seen, tool_calls_after_error, tokens_after_error).

    ``tokens_after_error`` sums assistant ``usage.output_tokens`` from
    events after the first signature match (the cost-signature axis the
    phase-1 pilot saw: error loops ran ~60% longer).
    """
    assert trap.signature is not None
    sig_idx: int | None = None
    for i, ev in enumerate(t.events):
        if trap.signature.search(_tool_result_text_of(ev)):
            sig_idx = i
            break
    if sig_idx is None:
        return False, 0, 0
    calls_after = sum(1 for i, _n, _inp in t.tool_uses() if i > sig_idx)
    tokens_after = 0
    for i, ev in enumerate(t.events):
        if i <= sig_idx:
            continue
        usage = (ev.get("message") or {}).get("usage") or {}
        tokens = usage.get("output_tokens")
        if isinstance(tokens, int):
            tokens_after += tokens
    return True, calls_after, tokens_after


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------


@dataclass
class TrapRunResult:
    """One trap session's outcome: run health + track-specific scores."""

    trap_id: str
    arm: str
    repeat: int
    ok: bool
    fired: bool
    evidence: str
    wall_s: float
    track: str = "prevention"
    cost_usd: float = 0.0
    num_turns: int = 0
    error: str = ""
    #: recovery-track fields (None/0 for prevention)
    recovered: bool | None = None
    decision_hit: bool | None = None
    sig_seen: bool | None = None
    tool_calls_after_error: int = 0
    tokens_after_error: int = 0
    #: Injection-marker counts from Transcript.injections (presence
    #: detection per recall surface; empty for errored runs).
    injections: dict[str, int] = field(default_factory=dict)
    #: Hook lifecycle counts from Transcript.hook_summary (the
    #: "hooks alive" receipt; empty for errored runs).
    hooks: dict[str, int] = field(default_factory=dict)


#: Nested-session env scrub (requirements §Design: nested ``claude -p``
#: needs ``env -i PATH HOME TERM ANTHROPIC_API_KEY``). A session
#: launched from inside Claude Code inherits ~14 ``CLAUDE_*`` vars
#: including OAuth state, and the child 401s. The scrubbed base keeps
#: only the shell basics plus the API key (from the environment, else
#: the 0600 key file — never printed).
SCRUB_KEEP = (
    "PATH",
    "HOME",
    "TERM",
    "SHELL",
    "USER",
    "LOGNAME",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "COLORTERM",
)
KEY_FILE = Path.home() / ".attune" / "anthropic.env"


def _key_from_file(path: Path | None = None) -> str:
    try:
        text = (path or KEY_FILE).read_text()
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def scrubbed_base_env() -> dict[str, str]:
    """Minimal child env for nested ``claude -p`` sessions."""
    base = {k: os.environ[k] for k in SCRUB_KEEP if k in os.environ}
    key = os.environ.get("ANTHROPIC_API_KEY") or _key_from_file()
    if key:
        base["ANTHROPIC_API_KEY"] = key
    return base


#: The repo's own plugin directory — forced into every trap session via
#: ``--plugin-dir``. Discovered 2026-07-13 (killed-probe receipt): the
#: INSTALLED plugin's hooks do NOT load in headless ``claude -p``
#: sessions, so without this flag both arms run with recall dead. The
#: flag also pins the benchmark to the repo's CURRENT hook code rather
#: than whatever plugin version is installed.
DEFAULT_PLUGIN_DIR = REPO_ROOT / "plugin"


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
    lessons_file: Path | None = None,
    scrub_env: bool = False,
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
            env = build_env(arm, base=scrubbed_base_env() if scrub_env else None)
            env["ATTUNE_AI_SENTINEL_DIR"] = str(sentinel_dir)
            env["ATTUNE_LESSONS_FILE"] = str(lessons_file or REPO_LESSONS)
            # Headless `claude -p` stamps CLAUDE_CODE_ENTRYPOINT=sdk-cli
            # (verified 2026-07-13, v2.1.144), which makes every
            # sdk-gated attune hook a silent no-op — the benchmark's
            # whole point is exercising those hooks, and this harness
            # parses stream-json defensively (the risk the gate guards).
            env["ATTUNE_SDK_GATE_OVERRIDE"] = "1"
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
                track=trap.track,
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
                track=trap.track,
                cost_usd=rr.cost_usd,
                num_turns=rr.num_turns,
                error=err,
            )
        if trap.track == "recovery":
            assert trap.outcome is not None
            recovered, out_evidence = trap.outcome(fixture)
            sig_seen, calls_after, tokens_after = recovery_metrics(t, trap)
            hit = decision_point_hit(t, trap)
            return TrapRunResult(
                trap_id=trap.id,
                arm=arm,
                repeat=repeat,
                ok=True,
                fired=sig_seen,
                evidence=out_evidence,
                wall_s=wall,
                track="recovery",
                cost_usd=rr.cost_usd,
                num_turns=rr.num_turns,
                recovered=recovered,
                decision_hit=hit,
                sig_seen=sig_seen,
                tool_calls_after_error=calls_after,
                tokens_after_error=tokens_after,
                injections=t.injections(),
                hooks=t.hook_summary(),
            )
        assert trap.score is not None
        fired, evidence = trap.score(t, fixture)
        return TrapRunResult(
            trap_id=trap.id,
            arm=arm,
            repeat=repeat,
            ok=True,
            fired=fired,
            evidence=evidence,
            wall_s=wall,
            track="prevention",
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
    """{trap_id: {arm: Cell}} for PREVENTION traps only — occurrence is
    a structural zero for JIT-carried traps and gets no Δp cell."""
    cells: dict[str, dict[str, Cell]] = {}
    for r in results:
        if r.track != "prevention":
            continue
        cell = cells.setdefault(r.trap_id, {}).setdefault(r.arm, Cell())
        if r.ok:
            cell.ok += 1
            if r.fired:
                cell.fired += 1
        else:
            cell.errors += 1
    return cells


@dataclass
class RecoveryCell:
    """One (recovery trap, arm) cell over decision-point-hit sessions."""

    scoreable: int = 0  # ok AND decision_hit AND sig_seen
    recovered: int = 0
    excluded: int = 0  # ok but no decision point / no signature
    errors: int = 0
    calls_after: list[int] = field(default_factory=list)
    tokens_after: list[int] = field(default_factory=list)


def aggregate_recovery(results: list[TrapRunResult]) -> dict[str, dict[str, RecoveryCell]]:
    cells: dict[str, dict[str, RecoveryCell]] = {}
    for r in results:
        if r.track != "recovery":
            continue
        cell = cells.setdefault(r.trap_id, {}).setdefault(r.arm, RecoveryCell())
        if not r.ok:
            cell.errors += 1
            continue
        if not (r.decision_hit and r.sig_seen):
            cell.excluded += 1
            continue
        cell.scoreable += 1
        if r.recovered:
            cell.recovered += 1
        cell.calls_after.append(r.tool_calls_after_error)
        cell.tokens_after.append(r.tokens_after_error)
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
            "the alive-receipt; see evaluate_validity)."
        )
    return None


def evaluate_validity(results: list[TrapRunResult], arms: list[str]) -> tuple[list[str], list[str]]:
    """(fatal_failures, warnings) — fatal means REFUSE to report deltas.

    Fatal shapes (design §Arm and receipt design):

      * any OFF-arm run shows injection markers → kill-switch not
        honored, every arm delta invalid;
      * an ON arm ran but NO hook lifecycle events appeared anywhere →
        hooks never loaded, both arms effectively OFF;
      * prevention traps in the ON arm show ZERO UserPromptSubmit
        banners → the prevention measurand was never exercised
        (question-shape postmortem: zero injection paths).

    Recovery traps with zero JIT banners are NOT fatal — a session that
    never hits the decision point is legitimately banner-free (handled
    by the exclusion rule instead).
    """
    fatal: list[str] = []
    warnings: list[str] = []
    off_dirty = [
        f"{r.trap_id}/off#{r.repeat}: {r.injections}"
        for r in results
        if r.ok and r.arm == "off" and sum(r.injections.values())
    ]
    if off_dirty:
        fatal.append(
            "ARM-VALIDATION FAILURE — OFF arm shows recall markers (the "
            "kill-switch is not honored; arm deltas are INVALID): " + "; ".join(off_dirty)
        )
    if "on" in arms:
        on_runs = [r for r in results if r.ok and r.arm == "on"]
        hooks_alive = any(sum(v for k, v in r.hooks.items() if k != "failed") for r in on_runs)
        if on_runs and not hooks_alive:
            fatal.append(
                "ARM-VALIDATION FAILURE — no hook lifecycle events in any "
                "ON-arm run: hooks never ran, both arms were effectively "
                "OFF, arm deltas are INVALID."
            )
        prevention_on = [r for r in on_runs if r.track == "prevention"]
        if prevention_on and not any(r.injections.get("prompt_recall", 0) for r in prevention_on):
            fatal.append(
                "ARM-VALIDATION FAILURE — zero UserPromptSubmit recall "
                "banners across all ON-arm prevention sessions: the "
                "prevention measurand was never exercised (check "
                "ATTUNE_LESSONS_FILE and the reachability receipts)."
            )
        recovery_on = [r for r in on_runs if r.track == "recovery"]
        if recovery_on and not any(r.injections.get("jit_recall", 0) for r in recovery_on):
            warnings.append(
                "recovery note: no JIT banners in any ON-arm recovery "
                "session — check the decision-hit column; sessions that "
                "never draft the pattern are excluded, not invalid."
            )
    return fatal, warnings


def _fmt_rate(cell: Cell | None) -> str:
    if cell is None or cell.rate is None:
        return "—"
    return f"{cell.fired}/{cell.ok} ({cell.rate:.0%})"


def _delta_p(cells: dict[str, Cell]) -> str:
    on, off = cells.get("on"), cells.get("off")
    if not on or not off or on.rate is None or off.rate is None:
        return "—"
    return f"{off.rate - on.rate:+.0%}"


def _median(xs: list[int]) -> str:
    return str(int(statistics.median(xs))) if xs else "—"


def render_prevention(cells: dict[str, dict[str, Cell]], *, markdown: bool) -> list[str]:
    if not cells:
        return []
    pilot = any(c.ok < 20 for arms in cells.values() for c in arms.values())
    title = "prevention track: fired rate by class and arm" + (" [PILOT scale]" if pilot else "")
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
    return lines


def render_recovery(cells: dict[str, dict[str, RecoveryCell]], *, markdown: bool) -> list[str]:
    """Recovery differentials. Deliberately NO occurrence-Δp column —
    the column itself would be a structural-zero claim (design)."""
    if not cells:
        return []
    pilot = any(c.scoreable < 20 for arms in cells.values() for c in arms.values())
    title = "recovery track: differentials over decision-point-hit sessions" + (
        " [PILOT scale]" if pilot else ""
    )
    header = "| Trap class | arm | recovered | med calls-after | med tokens-after | excluded |"
    if markdown:
        lines = [f"### {title}", "", header, "|---|---|--:|--:|--:|--:|"]
        for trap_id, arms in cells.items():
            for arm, c in sorted(arms.items()):
                lines.append(
                    f"| `{trap_id}` | {arm} | {c.recovered}/{c.scoreable} | "
                    f"{_median(c.calls_after)} | {_median(c.tokens_after)} | "
                    f"{c.excluded} |"
                )
    else:
        lines = ["", f"=== {title} ==="]
        lines.append(
            f"{'trap':<26} {'arm':<4} {'recovered':>10} {'calls>':>7} "
            f"{'tokens>':>8} {'excl':>5}"
        )
        for trap_id, arms in cells.items():
            for arm, c in sorted(arms.items()):
                lines.append(
                    f"{trap_id:<26} {arm:<4} {c.recovered}/{c.scoreable:>8} "
                    f"{_median(c.calls_after):>7} {_median(c.tokens_after):>8} "
                    f"{c.excluded:>5}"
                )
    return lines


def gate_verdicts(
    prevention: dict[str, dict[str, Cell]],
    recovery: dict[str, dict[str, RecoveryCell]],
    repeats: int,
) -> list[str]:
    """Pilot-gate verdicts per trap (informational, not refusals)."""
    lines = ["", "pilot gates:"]
    need_hit = max(1, round(0.8 * repeats))
    for trap_id, arms in prevention.items():
        off = arms.get("off")
        go = off is not None and off.fired >= 2
        lines.append(
            f"  {trap_id}: {'GO' if go else 'NO-GO'} "
            f"(OFF fired {off.fired if off else 0}, gate ≥2)"
        )
    for trap_id, arms in recovery.items():
        hits = {a: c.scoreable for a, c in arms.items()}
        go = all(n >= need_hit for n in hits.values()) and bool(hits)
        lines.append(
            f"  {trap_id}: {'GO' if go else 'NO-GO'} "
            f"(decision-point hits per arm {hits}, gate ≥{need_hit})"
        )
    return lines


def render_report(
    results: list[TrapRunResult], *, markdown: bool, repeats: int
) -> tuple[str, bool]:
    """(report, valid). When validity fails, the report contains ONLY
    the failures — no Δ or recovery tables (real refusal, not a
    warning; phase 1's warn-only report shipped invalid Δp twice)."""
    arms = sorted({r.arm for r in results})
    fatal, warnings = evaluate_validity(results, arms)
    lines: list[str] = []
    errors = [r for r in results if not r.ok]
    if fatal:
        lines.append("ARM VALIDITY FAILED — refusing to report Δ/recovery metrics.")
        lines.extend(fatal)
        if errors:
            lines.append("")
            lines.append("errors:")
            lines.extend(f"  {r.trap_id}/{r.arm}#{r.repeat}: {r.error}" for r in errors)
        return "\n".join(lines), False
    prevention = aggregate_cells(results)
    recovery = aggregate_recovery(results)
    lines.extend(render_prevention(prevention, markdown=markdown))
    lines.extend(render_recovery(recovery, markdown=markdown))
    if errors:
        lines.append("")
        lines.append("errors (excluded from rates):")
        lines.extend(f"  {r.trap_id}/{r.arm}#{r.repeat}: {r.error}" for r in errors)
    fired = [r for r in results if r.ok and r.track == "prevention" and r.fired]
    if fired:
        lines.append("")
        lines.append("prevention firing evidence:")
        lines.extend(f"  {r.trap_id}/{r.arm}#{r.repeat}: {r.evidence}" for r in fired)
    lines.extend(warnings)
    lines.extend(gate_verdicts(prevention, recovery, repeats))
    lines.append("")
    lines.append(
        "Prevention reports occurrence Δp; recovery reports differentials "
        "only. No savings claims (insurance frame, #1291)."
    )
    return "\n".join(lines), True


# --------------------------------------------------------------------------
# Reachability receipts (free — no sessions)
# --------------------------------------------------------------------------


def run_reachability(traps: list[Trap], lessons_file: Path) -> int:
    """Prove each prevention trap's prompt reaches its lesson from a
    FIXTURE cwd (repo-cwd receipts are invalid — finding 1).

    Runs ``plugin/hooks/lesson_recall.py`` directly with the trap's
    prompt and a fresh fixture as cwd, corpus pinned via
    ``ATTUNE_LESSONS_FILE``, sentinels isolated. Exit 4 on any miss.
    """
    hook = REPO_ROOT / "plugin" / "hooks" / "lesson_recall.py"
    all_ok = True
    for trap in traps:
        if trap.track != "prevention":
            continue
        fixture = Path(tempfile.mkdtemp(prefix=f"reach-{trap.id}-"))
        try:
            trap.setup(fixture)
            env = dict(os.environ)
            env.pop("ATTUNE_SDK_SUBPROCESS", None)
            env.pop("CLAUDE_CODE_ENTRYPOINT", None)
            env["ATTUNE_LESSON_RECALL"] = "1"
            env["ATTUNE_LESSONS_FILE"] = str(lessons_file)
            env["ATTUNE_AI_SENTINEL_DIR"] = str(fixture / ".s")
            payload = {
                "prompt": trap.prompt,
                "cwd": str(fixture),
                "session_id": f"reach-{trap.id}",
            }
            proc = subprocess.run(
                [sys.executable, str(hook)],
                input=json.dumps(payload),
                env=env,
                capture_output=True,
                text=True,
                cwd=fixture,
                timeout=60,
            )
            ctx = ""
            try:
                out = json.loads(proc.stdout or "{}")
                ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            except json.JSONDecodeError:
                pass
            hit_kw = [kw for kw in trap.target_keywords if kw.lower() in ctx.lower()]
            ok = bool(ctx) and bool(hit_kw)
            all_ok &= ok
            print(f"{'PASS' if ok else 'MISS'} {trap.id}: ", end="")
            if not ctx:
                print("no lesson surfaced at/above the floor")
            else:
                print(f"keywords matched {hit_kw or 'NONE'}; surfaced: {ctx[:160]!r}")
        finally:
            shutil.rmtree(fixture, ignore_errors=True)
    if not all_ok:
        print(
            "\nreachability FAILED — re-engineer the trap prompt or the "
            "lesson's match surface; never lower the floor for the "
            "benchmark (design §Prevention track)."
        )
    return 0 if all_ok else 4


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="store_true", help="execute (default: print the plan)")
    parser.add_argument(
        "--reachability",
        action="store_true",
        help="run the free prevention-trap reachability receipts and exit",
    )
    parser.add_argument("--repeats", type=int, default=5, help="runs per (trap, arm)")
    parser.add_argument(
        "--arms", default="on,off", help="comma list of arms to run (subset of on,off)"
    )
    parser.add_argument("--traps", nargs="*", help="trap ids to run (default: all)")
    parser.add_argument("--max-turns", type=int, default=10, help="turn cap per session")
    parser.add_argument("--timeout-s", type=int, default=300, help="per-session timeout")
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=12.0,
        help="abort the run loop once accumulated session cost exceeds this",
    )
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
        "--lessons-file",
        type=Path,
        default=None,
        help="lessons corpus for the ON arm (default: the repo's .claude/lessons.md)",
    )
    parser.add_argument(
        "--scrub-env",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "run child sessions with a scrubbed env (auto-on inside a "
            "Claude Code session — inherited OAuth state 401s the child)"
        ),
    )
    parser.add_argument(
        "--save-transcripts",
        type=Path,
        default=None,
        help="directory to persist each session's raw stream-json (debugging)",
    )
    args = parser.parse_args(argv)

    try:
        traps = get_traps(args.traps)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    lessons_file = args.lessons_file or REPO_LESSONS
    if not lessons_file.is_file():
        print(f"FAIL: lessons corpus not found: {lessons_file}", file=sys.stderr)
        return 2

    if args.reachability:
        return run_reachability(traps, lessons_file)

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    bad = [a for a in arms if a not in ARM_ENV]
    if bad or not arms:
        print(f"FAIL: --arms must be a subset of {sorted(ARM_ENV)}", file=sys.stderr)
        return 2

    n_sessions = len(traps) * len(arms) * args.repeats
    plan = (
        f"plan: {len(traps)} traps × {len(arms)} arm(s) × {args.repeats} "
        f"repeat(s) = {n_sessions} headless sessions in fresh temp fixtures "
        f"(cost cap ${args.max_cost_usd:.2f})"
    )
    print(plan)
    if not args.run:
        for t in traps:
            print(f"  - {t.id} [{t.track}] (tools: {t.allowed_tools}): {t.prompt[:60]}…")
        print("dry-run only — pass --run to execute (spends real LLM usage).")
        return 0

    if shutil.which("claude") is None:
        print("FAIL: `claude` CLI not on PATH", file=sys.stderr)
        return 1
    if shutil.which("zsh") is None:
        print("FAIL: zsh not on PATH (recovery fixtures need it)", file=sys.stderr)
        return 1
    scrub = args.scrub_env
    if scrub is None:
        scrub = bool(os.environ.get("CLAUDECODE"))
        if scrub:
            print(
                "note: Claude Code session detected — child sessions run "
                "with a scrubbed env (--no-scrub-env to override).",
                file=sys.stderr,
            )
    if scrub and not (os.environ.get("ANTHROPIC_API_KEY") or _key_from_file()):
        print(
            "FAIL: scrubbed env needs ANTHROPIC_API_KEY (env or "
            f"{KEY_FILE}) — nested sessions cannot reuse this session's "
            "OAuth state.",
            file=sys.stderr,
        )
        return 1

    run_start_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    results: list[TrapRunResult] = []
    total_cost = 0.0
    aborted = False
    for repeat in range(args.repeats):
        if aborted:
            break
        # Alternate arm order per repeat (cache-warmth symmetry, as in
        # session_savings).
        order = list(arms) if repeat % 2 == 0 else list(reversed(arms))
        for trap in traps:
            if aborted:
                break
            for arm in order:
                if total_cost >= args.max_cost_usd:
                    print(
                        f"COST ABORT: accumulated ${total_cost:.2f} ≥ cap "
                        f"${args.max_cost_usd:.2f} — stopping after "
                        f"{len(results)}/{n_sessions} sessions.",
                        flush=True,
                    )
                    aborted = True
                    break
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
                    lessons_file=lessons_file,
                    scrub_env=scrub,
                )
                total_cost += r.cost_usd
                if r.track == "recovery" and r.ok:
                    status = (
                        f"{'recovered' if r.recovered else 'NOT recovered'}, "
                        f"hit={'y' if r.decision_hit else 'n'}, "
                        f"sig={'y' if r.sig_seen else 'n'}, "
                        f"calls>{r.tool_calls_after_error}"
                    )
                else:
                    status = ("FIRED" if r.fired else "clean") if r.ok else f"ERROR ({r.error})"
                inj = "+".join(f"{k[0]}{v}" for k, v in sorted(r.injections.items()))
                hk = "+".join(f"{k[:2]}{v}" for k, v in sorted(r.hooks.items()) if k != "failed")
                failed = r.hooks.get("failed", 0)
                print(
                    f"    {status}: {r.wall_s:.1f}s, ${r.cost_usd:.2f} "
                    f"(Σ ${total_cost:.2f}), inj {inj or '-'}, hooks {hk or 'NONE'}"
                    + (f" ({failed} failed)" if failed else ""),
                    flush=True,
                )
                results.append(r)

    report, valid = render_report(results, markdown=False, repeats=args.repeats)
    print(report)
    n_events = count_memory_events(run_start_iso)
    receipt = telemetry_arm_receipt(n_events, arms)
    print(f"\nrecall-telemetry events in run window: {n_events}")
    if receipt:
        print(receipt)
    if aborted:
        print("NOTE: run was cost-aborted; counts above are partial.")
    if args.markdown and valid:
        print()
        print(render_report(results, markdown=True, repeats=args.repeats)[0])
    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {
                    "plan": plan,
                    "arm_env": ARM_ENV,
                    "aborted": aborted,
                    "valid": valid,
                    "results": [asdict(r) for r in results],
                },
                indent=2,
            )
        )
        print(f"\nfull results → {args.json_out}")
    if not valid:
        return 3
    return 0 if any(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
