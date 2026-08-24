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

#: Chair-ruled values (no longer provisional): OPEN-1 fixed the
#: codex default and OPEN-3 ratified the 60k cap on the T3 dogfood
#: ledger's diff-size evidence — docs/specs/cross-review/
#: decisions.md (2026-07-28 entries) and receipts.md.
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


#: Projector-owned surfaces — reviewable content lives in their masters
#: (content/features/, .claude/skills/, the help sources), so when the
#: brief cap bites these are the right files to drop first.
_PROJECTION_PREFIXES = (
    "plugin/help/generated/",
    "attune-ai-dev/",
    ".help/",
    ".agents/skills/",
)


def _brief_priority(name: str) -> int:
    """Packing rank: masters before projections when the cap bites.

    2026-08-19 retro: a residue-cleanup lane sent 26 files including
    HTML help projections while the 60KB cap pushed out the diff's one
    src enum edit — the omission the scoped follow-up lane existed to
    cover. src and tests are what the seat is there to judge; known
    projections duplicate masters that already rank ahead of them.
    """
    if name.startswith("src/"):
        return 0
    if name.startswith("tests/"):
        return 1
    if name.startswith(_PROJECTION_PREFIXES):
        return 3
    return 2


def budget_manifest(per_file: dict[str, str], cap_chars: int = DIFF_CAP_CHARS) -> dict[str, Any]:
    """Split files into sent/omitted under the cap.

    Packing order: priority class first (src, tests, everything else,
    known projections — see :func:`_brief_priority`), largest diff
    first within a class.

    R3: the manifest travels everywhere (brief, board post, render)
    — a partial review must say so.
    """
    ordered = sorted(per_file.items(), key=lambda kv: (_brief_priority(kv[0]), -len(kv[1])))
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
    prior_rejections: Sequence[str] = (),
) -> dict[str, Any]:
    """Run one advisory review; ``ok`` is True whenever the run ran.

    ``status``: ``findings`` / ``clean`` / ``absent`` /
    ``format_noncompliant``. Board unreachability degrades to
    ``board: skipped (<reason>)`` — never a failure (R2/R4).

    ``prior_rejections``: one-line summaries (claim + refutation) of
    findings already rejected in earlier lanes on this same diff. They
    are appended to the brief so a RE-LANE seat does not spend its
    budget re-reporting a refuted claim (2026-08-24 retro: the same
    false ``cwd=self.repo_path`` finding surfaced in all three #2268
    lanes because each brief was blind to the previous rejections).
    """
    target = resolve_target(repo_root, mode=mode, base_ref=base_ref)
    manifest = budget_manifest(target["per_file"])
    brief = build_brief(target, manifest)
    if prior_rejections:
        lines = "\n".join(f"- {r}" for r in prior_rejections)
        brief += (
            "\n\nPreviously REJECTED findings from earlier lanes on this "
            "same diff, with the refutations. Do NOT re-report these "
            "unless you have NEW evidence that overturns the stated "
            f"refutation:\n{lines}"
        )

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


# The two ledger gates' grammars, mirrored here so a row can be checked
# at AUTHORING time instead of two CI rounds later (2026-08-24 retro:
# PR #2268 went red twice on hand-authored rows — first on the precision
# tally's leading shape, then on the D11a claim/reason format). The
# gates in tests/unit/{gates,scripts}/ stay the independent enforcers;
# drift between this mirror and the gates is caught by the gates
# themselves failing on a row this check passed.
_DISPOSITION_REJECTION = re.compile(r"^(?:dismissed|noise|rejected)\b")
_DISPOSITION_REJECTED_FORMAT = re.compile(
    r"^(?:dismissed|noise|rejected)\b[^\u2014]*\u2014 claim: \".+\" \u2014 reason: .+$"
)
_DISPOSITION_ALL_REAL = re.compile(r"^(?:all |both )?real\b")
_DISPOSITION_N_REAL = re.compile(r"^(\d+|one|two|three|four|five) real\b")
_WORD_COUNTS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def check_disposition(disposition: str, findings: int) -> list[str]:
    """Return the gate problems a ledger disposition would trip, if any.

    Faithful mirror of ``scripts/ledger_precision.py``'s ``classify``
    leading-shape grammar (same regexes, same match order) plus the
    D11a rejection format from
    ``tests/unit/gates/test_ledger_rejection_format.py``. An empty list
    means both gates accept the row. Count contradictions the tally
    would silently mis-tally (e.g. 'both real' with one finding) are
    also flagged \u2014 stricter here than the gates, by design.
    """
    d = disposition.strip()
    problems: list[str] = []
    if d.lower().startswith("clean"):
        if findings != 0:
            problems.append(f"'clean' contradicts a findings count of {findings}")
        return problems
    if _DISPOSITION_REJECTION.match(d):
        if not _DISPOSITION_REJECTED_FORMAT.match(d):
            problems.append(
                "rejection-class rows must carry the verbatim claim and "
                "reason: 'rejected \u2014 claim: \"...\" \u2014 reason: ...' (D11a)"
            )
        return problems
    m = _DISPOSITION_N_REAL.match(d)
    if m:
        token = m.group(1)
        real = _WORD_COUNTS.get(token) or int(token)
        if real > findings:
            problems.append(f"'{real} real' exceeds the findings count of {findings}")
        return problems
    if _DISPOSITION_ALL_REAL.match(d):
        if d.startswith("both ") and findings != 2:
            problems.append(f"'both real' implies exactly 2 findings, count is {findings}")
        elif findings == 0:
            problems.append(
                "'real' contradicts a findings count of 0 \u2014 a "
                "no-findings row leads with 'clean'"
            )
        return problems
    problems.append(
        "disposition must lead with clean / 'N real' / real / "
        "dismissed|noise|rejected \u2014 the precision tally cannot classify "
        f"{d[:40]!r}"
    )
    return problems


def ledger_row(result: dict[str, Any], disposition: str = "not-triaged") -> str:
    """Render the R5 dogfood-ledger row for the spec's receipts.md.

    Any disposition other than the ``not-triaged`` placeholder is
    validated against both ledger gates' grammars at authoring time
    (:func:`check_disposition`); a non-compliant one raises rather than
    shipping a row CI will reject two rounds later.
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest = result["manifest"]
    if disposition != "not-triaged":
        problems = check_disposition(disposition, len(result["findings"]))
        if problems:
            raise ValueError("ledger disposition fails the gates: " + "; ".join(problems))
    return (
        f"| {date} | {result['seat']} | {result['target']} | "
        f"{len(manifest['sent'])} sent / {len(manifest['omitted'])} omitted | "
        f"{len(result['findings'])} ({result['status']}) | {disposition} |"
    )
