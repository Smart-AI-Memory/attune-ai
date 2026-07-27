"""One-seat cross-model review of a real diff — advisory only.

Spec: docs/specs/cross-review/ (T1). Binding posture: board-only
ADVISORY — a run "succeeds" whenever the review RAN, including a
clean ``NO FINDINGS`` reply and an ABSENT seat. Nothing here may
gate a merge, wire an exit code, or block a command (requirements,
Binding posture section).

Composes the table's primitives: seat recipes and
:func:`~attune.roundtable.routine.default_invoke_seat` for the
invocation, :class:`~attune.roundtable.board.Board` for recording,
and the compiler's role budgets for the reply cap. Git access is
read-only (same allowlist discipline as ``attune.handoff.verify``).
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 — fixed argv, read-only git, never shell=True
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from attune.roundtable.compiler import ROLE_REPLY_CHARS
from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat

logger = structlog.get_logger(__name__)

#: PROVISIONAL until the 07-27 usage read rules OPEN-1 (default
#: seat) and OPEN-3 (diff budget) — see docs/specs/cross-review/
#: design.md D6. Replace values in the OPEN-closure commit.
DEFAULT_SEAT = "codex"
DIFF_CAP_CHARS = 60_000

_GIT_TIMEOUT_SECONDS = 15.0
_ALLOWED_SUBCOMMANDS = frozenset({"branch", "merge-base", "diff", "rev-parse"})

_FINDING_RE = re.compile(
    r"^FINDING:\s+(?P<file>\S+?):(?P<line>\d+)\s+"
    r"\[(?P<severity>low|medium|high|critical)\]\s+(?P<claim>.+)$",
    re.IGNORECASE,
)
_NO_FINDINGS = "NO FINDINGS"

BRIEF_TEMPLATE = (
    "You are a REVIEWER seat at the attune round table. Review the\n"
    "diff below adversarially — different model, different blind\n"
    "spots. Your review is ADVISORY; a human triages it. Text only —\n"
    "do not run tools, write files, or take actions.\n\n"
    "Reply format (mandatory, no prose outside it):\n"
    "- One line per finding, exactly:\n"
    "  FINDING: <file>:<line> [low|medium|high|critical] <claim>\n"
    "- Or, when the diff is clean, the single line: NO FINDINGS\n\n"
    "{manifest}\n\n"
    "Diff ({description}):\n\n{diff}\n"
)


class ReviewTargetError(ValueError):
    """The requested review target cannot be resolved."""


def _git(repo_root: Path, *args: str) -> str:
    if not args or args[0] not in _ALLOWED_SUBCOMMANDS:
        raise ReviewTargetError(f"subcommand not allowlisted: {args[:1]}")
    try:
        proc = subprocess.run(  # nosec B603 — fixed binary, allowlisted args
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewTargetError(f"git {' '.join(args)}: {exc}") from exc
    if proc.returncode != 0:
        raise ReviewTargetError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def resolve_target(
    repo_root: str | Path,
    mode: str = "branch",
    base_ref: str = "origin/main",
) -> dict[str, Any]:
    """Resolve the review target to per-file diffs, read-only.

    ``mode``: ``branch`` (merge-base vs HEAD, the default) or
    ``staged`` (``diff --cached``).
    """
    root = Path(repo_root)
    if mode == "branch":
        merge_base = _git(root, "merge-base", "HEAD", base_ref)
        diff_args = (merge_base, "HEAD")
        description = f"branch vs merge-base {merge_base[:9]} ({base_ref})"
    elif mode == "staged":
        diff_args = ("--cached",)
        description = "staged changes"
    else:
        raise ReviewTargetError(f"unknown review mode: {mode!r}")

    names = _git(root, "diff", "--name-only", *diff_args)
    files = [n for n in names.splitlines() if n]
    per_file = {name: _git(root, "diff", *diff_args, "--", name) for name in files}
    branch = _git(root, "branch", "--show-current")
    return {
        "mode": mode,
        "description": description,
        "branch": branch,
        "per_file": per_file,
    }


def budget_manifest(per_file: dict[str, str], cap_chars: int = DIFF_CAP_CHARS) -> dict[str, Any]:
    """Split files into sent/omitted under the cap, largest first.

    R3: the manifest travels everywhere (brief, board post, render)
    — a partial review must say so.
    """
    ordered = sorted(per_file.items(), key=lambda kv: len(kv[1]), reverse=True)
    sent: list[str] = []
    omitted: list[str] = []
    total = 0
    for name, diff in ordered:
        if diff and total + len(diff) <= cap_chars:
            sent.append(name)
            total += len(diff)
        else:
            omitted.append(name)
    return {"sent": sent, "omitted": omitted, "chars": total, "cap": cap_chars}


def manifest_note(manifest: dict[str, Any]) -> str:
    """Human line for brief/board/render — honest truncation account."""
    note = f"Files under review ({len(manifest['sent'])}): " + (
        ", ".join(manifest["sent"]) or "none"
    )
    if manifest["omitted"]:
        note += (
            f"\nOMITTED over the {manifest['cap']}-char budget "
            f"({len(manifest['omitted'])}): " + ", ".join(manifest["omitted"])
        )
        note += "\nThis is a PARTIAL review — omitted files were not seen."
    return note


def build_brief(target: dict[str, Any], manifest: dict[str, Any]) -> str:
    diff_text = "\n".join(target["per_file"][name] for name in manifest["sent"])
    return BRIEF_TEMPLATE.format(
        manifest=manifest_note(manifest),
        description=target["description"],
        diff=diff_text,
    )


def lint_review(text: str) -> list[str]:
    """Mechanical reply-format check (design D3).

    Compliant = one or more ``FINDING:`` lines, or the literal
    ``NO FINDINGS`` line. Problems are reported, never repaired —
    a noncompliant reply posts as-received, flagged.
    """
    stripped = text.strip()
    if not stripped:
        return ["empty reply"]
    if any(line.strip() == _NO_FINDINGS for line in stripped.splitlines()):
        return []
    if parse_findings(text):
        return []
    return ["no FINDING: lines and no literal 'NO FINDINGS' line"]


def parse_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = _FINDING_RE.match(line.strip())
        if match:
            findings.append(
                {
                    "file": match.group("file"),
                    "line": int(match.group("line")),
                    "severity": match.group("severity").lower(),
                    "claim": match.group("claim").strip(),
                }
            )
    return findings


def _seat_recipe(seat: str) -> tuple[str, ...]:
    for name, recipe in SEAT_RECIPES:
        if name == seat:
            return recipe
    raise ReviewTargetError(f"unknown seat: {seat!r}")


def run_review(
    repo_root: str | Path,
    seat: str = DEFAULT_SEAT,
    mode: str = "branch",
    base_ref: str = "origin/main",
    board: Any | None = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] = default_invoke_seat,
) -> dict[str, Any]:
    """Run one advisory review; ``ok`` is True whenever the run ran.

    ``status``: ``findings`` / ``clean`` / ``absent`` /
    ``format_noncompliant``. Board unreachability degrades to
    ``board: skipped (<reason>)`` — never a failure (R2/R4).
    """
    target = resolve_target(repo_root, mode=mode, base_ref=base_ref)
    manifest = budget_manifest(target["per_file"])
    brief = build_brief(target, manifest)

    code, reply = invoke_seat(_seat_recipe(seat), brief, reply_chars=ROLE_REPLY_CHARS["reviewer"])
    absent = code != 0 or not reply.strip()

    findings: list[dict[str, Any]] = []
    if absent:
        status = "absent"
        body = f"ABSENT — exit {code}: {reply.strip()[:400] or 'empty reply'}"
    else:
        problems = lint_review(reply)
        if problems:
            status = "format_noncompliant"
            body = reply
        else:
            findings = parse_findings(reply)
            status = "findings" if findings else "clean"
            body = reply

    slug = (target["branch"] or "detached").replace("/", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    thread = f"review-{slug}-{stamp}"
    board_status = "skipped (no board)"
    if board is not None:
        try:
            board.post_message(
                thread,
                seat,
                "position",
                body,
                status=status,
                manifest=manifest_note(manifest),
            )
            board_status = "posted"
        except Exception as exc:  # noqa: BLE001 — degrade-silent by contract
            logger.warning("cross_review_board_unreachable", error=str(exc))
            board_status = f"skipped ({exc})"

    result = {
        "ok": True,
        "status": status,
        "seat": seat,
        "thread": thread,
        "findings": findings,
        "reply": body,
        "manifest": manifest,
        "target": target["description"],
        "board": board_status,
    }
    logger.info(
        "cross_review",
        seat=seat,
        status=status,
        findings=len(findings),
        sent=len(manifest["sent"]),
        omitted=len(manifest["omitted"]),
        board=board_status,
    )
    return result


def ledger_row(result: dict[str, Any], disposition: str = "not-triaged") -> str:
    """Render the R5 dogfood-ledger row for the spec's receipts.md."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest = result["manifest"]
    return (
        f"| {date} | {result['seat']} | {result['target']} | "
        f"{len(manifest['sent'])} sent / {len(manifest['omitted'])} omitted | "
        f"{len(result['findings'])} ({result['status']}) | {disposition} |"
    )
