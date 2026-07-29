"""Fire-rate read for the contract's Principles enforcers (D12).

Answers "are the principles load-bearing or decorative?" from CI
exhaust: for each enforcer cited in the master's Principles section,
count the failed CI runs in a window whose failure logs name it — an
enforcer that fires is a principle demonstrably doing work on the
discipline.

Honest limits, stated in the output:
- Hook-class enforcers (pre-commit / PreToolUse) fire locally and are
  NOT observable in CI history — they are listed, not counted.
- A never-fired enforcer is not proof of uselessness: deterrence and
  irrelevance look identical here. The profile steers attention; it
  does not rule.

Run at release-prep cadence (D12): ``python scripts/principles_fire_rate.py``
(optionally ``--since 2026-07-01`` and ``--limit 200``).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER = REPO_ROOT / "content/collaboration/contract.md"

# Citation shapes — kept in lockstep with the drift guard
# (tests/unit/gates/test_principles_citations.py), which is the
# enforcer that keeps these citations real in the first place.
_PATH_RE = re.compile(r"^[\w./-]+\.(?:py|yml|yaml|md|toml|json|sh|cfg|ini|txt)$")
_DIR_RE = re.compile(r"^[\w.-]+(?:/[\w.-]+)+/?$")

#: Enforcers whose fires happen outside CI (local hooks) — listed, not counted.
_HOOK_CLASS_MARKERS = ("hooks/scripts", "pre-commit")


@dataclass
class Principle:
    """One numbered principle and the enforcer paths it cites."""

    number: int
    title: str
    enforcers: list[str] = field(default_factory=list)


def parse_principles(text: str) -> list[Principle]:
    """Extract numbered principles and their cited enforcer paths."""
    match = re.search(r"^### Principles$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"no '### Principles' heading in {MASTER}")
    nxt = re.search(r"^#{2,3} ", text[match.end() :], re.MULTILINE)
    section = text[match.start() : match.end() + nxt.start() if nxt else len(text)]

    principles: list[Principle] = []
    for item in re.finditer(
        r"^(\d+)\.\s+\*\*(.+?)\*\*(.*?)(?=^\d+\.\s|\Z)", section, re.MULTILINE | re.DOTALL
    ):
        number, title, body = int(item.group(1)), item.group(2), item.group(3)
        enforcers = []
        for span in re.findall(r"`([^`]+)`", body, re.DOTALL):
            collapsed = re.sub(r"\s+", "", span).split("::")[0]
            if _PATH_RE.match(collapsed) or _DIR_RE.match(collapsed):
                enforcers.append(collapsed)
        principles.append(Principle(number, title.rstrip("."), enforcers))
    if not principles:
        raise ValueError("no numbered principles parsed — section format changed?")
    return principles


def _is_hook_class(enforcer: str) -> bool:
    return any(marker in enforcer for marker in _HOOK_CLASS_MARKERS)


def _default_runner(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout


def failed_run_logs(
    since: str, limit: int, runner: Callable[[list[str]], str] = _default_runner
) -> dict[str, str]:
    """Map failed CI run ids in the window to their failure logs."""
    listing = runner(
        [
            "gh",
            "run",
            "list",
            "--status",
            "failure",
            "--created",
            f">{since}",
            "--limit",
            str(limit),
            "--json",
            "databaseId",
        ]
    )
    runs = json.loads(listing or "[]")
    return {
        str(r["databaseId"]): runner(["gh", "run", "view", str(r["databaseId"]), "--log-failed"])
        for r in runs
    }


def fire_counts(principles: list[Principle], logs: dict[str, str]) -> dict[str, list[str]]:
    """Enforcer path -> failed run ids where that enforcer itself FAILED.

    Matches pytest failure lines (``FAILED .../<name>::``), not bare
    mentions — a failed run's log contains every collected test file's
    name, so substring matching inflates every count (caught by the
    first live-fire read).
    """
    counts: dict[str, list[str]] = {}
    for principle in principles:
        for enforcer in principle.enforcers:
            if _is_hook_class(enforcer):
                continue
            fired = re.compile(rf"FAILED\s+\S*{re.escape(Path(enforcer).name)}::")
            counts[enforcer] = [rid for rid, log in logs.items() if fired.search(log)]
    return counts


def format_report(principles: list[Principle], counts: dict[str, list[str]], since: str) -> str:
    """Render the fire-rate profile as markdown."""
    lines = [
        f"# Principles fire-rate read (window: since {since})",
        "",
        "| P# | Principle | Enforcer | Fires | Runs |",
        "|---|---|---|---|---|",
    ]
    never: list[str] = []
    for principle in principles:
        if not principle.enforcers:
            lines.append(f"| {principle.number} | {principle.title} | *(aspirational)* | n/a | — |")
            continue
        for enforcer in principle.enforcers:
            if _is_hook_class(enforcer):
                lines.append(
                    f"| {principle.number} | {principle.title} | `{enforcer}` "
                    f"| not observable (hook-class) | — |"
                )
                continue
            runs = counts.get(enforcer, [])
            if not runs:
                never.append(f"P{principle.number} `{enforcer}`")
            lines.append(
                f"| {principle.number} | {principle.title} | `{enforcer}` "
                f"| {len(runs)} | {', '.join(runs) if runs else '—'} |"
            )
    lines += [
        "",
        "Never fired in window (deterrence and irrelevance look identical "
        "here — steer attention, don't rule): " + (", ".join(never) if never else "none"),
    ]
    return "\n".join(lines)


def main() -> int:
    """CLI entry: read the window, print the profile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default="2026-07-01", help="ISO date lower bound")
    parser.add_argument("--limit", type=int, default=200, help="max failed runs to scan")
    args = parser.parse_args()

    principles = parse_principles(MASTER.read_text(encoding="utf-8"))
    logs = failed_run_logs(args.since, args.limit)
    print(format_report(principles, fire_counts(principles, logs), args.since))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
