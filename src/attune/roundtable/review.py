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

import json
import os
import re
import subprocess  # nosec B404 — fixed argv, read-only git, never shell=True
import sys
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePath
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

#: Environment markers identifying the MODERATING host — the session
#: resolving the diff and briefing a seat. OPEN-1 (2026-07-28) fixed
#: the default at ``codex`` when Claude was the only host, so "the
#: ruled default" and "a non-authoring seat" were the same value.
#: A Codex-hosted ``/cross-review`` breaks that identity: the ruled
#: default would brief the AUTHORING seat on its own diff, and a
#: self-review reads exactly like a clean one.
#:
#: The Codex names are VERIFIED, not inferred — read out of a live
#: Codex tool-call shell on 2026-09-10. An earlier draft keyed on
#: ``CODEX_SHELL``/``CODEX_APP_TOOLS_PIPE_PATH``/``CODEX_MCP_NODE_PATH``/
#: ``CODEX_INTERNAL_ORIGINATOR_OVERRIDE``, harvested from
#: ``~/.codex/shell_snapshots/``; a live probe exported NONE of them, so
#: detection would have returned None inside the very host it was written
#: for. Prefix-matching is used rather than a fixed list precisely because
#: that list proved wrong once: the marker set differs between an
#: interactive session and ``codex exec``, and a new release may rename
#: any single variable.
HOST_ENV_PREFIXES: tuple[tuple[str, str], ...] = (
    ("claude", "CLAUDECODE"),
    ("codex", "CODEX_"),
)

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


#: Governance/enforcement surfaces — small, load-bearing, and exactly
#: what a D11 lane exists to read. Without their own class they sort
#: into "everything else" AND lose the largest-first tiebreak (a
#: 31-line allowlist shrink ranks behind every doc), which is how the
#: #2259 lane omitted pyproject.toml and the gate allowlist while
#: reporting clean (2026-08-24 retro O2).
_GOVERNANCE_PREFIXES = (
    ".claude/gates/",
    ".github/",
)

#: Exact-name governance files — matched whole, so `pyproject.toml.bak`
#: does not outrank real docs (codex D11 finding, 2026-08-24).
_GOVERNANCE_FILES = frozenset({"pyproject.toml", "codecov.yml"})


def _brief_priority(name: str) -> int:
    """Packing rank: masters before projections when the cap bites.

    2026-08-19 retro: a residue-cleanup lane sent 26 files including
    HTML help projections while the 60KB cap pushed out the diff's one
    src enum edit — the omission the scoped follow-up lane existed to
    cover. src and tests are what the seat is there to judge; known
    projections duplicate masters that already rank ahead of them.
    Governance surfaces rank right behind tests (see
    ``_GOVERNANCE_PREFIXES``).
    """
    if name.startswith("src/"):
        return 0
    if name.startswith("tests/"):
        return 1
    if name in _GOVERNANCE_FILES or name.startswith(_GOVERNANCE_PREFIXES):
        return 2
    if name.startswith(_PROJECTION_PREFIXES):
        return 4
    return 3


def budget_manifest(
    per_file: dict[str, str], cap_chars: int = DIFF_CAP_CHARS, require_complete: bool = False
) -> dict[str, Any]:
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
    if require_complete and omitted:
        raise ReviewTargetError("incomplete review: " + ", ".join(omitted))
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


def detect_moderator_host(environ: dict[str, str] | None = None) -> str | None:
    """Name the host running this moderator, or ``None`` when unsure.

    ``None`` covers both "no marker" (a plain shell, CI, a test) and
    "markers for two hosts" — a nested launch, where the innermost host
    cannot be told from the outer one by environment alone. Guessing
    between them is what would reintroduce a silent self-review, so the
    ambiguous case is reported as unknown and handled by the caller.
    """
    env = os.environ if environ is None else environ
    found = [
        seat
        for seat, prefix in HOST_ENV_PREFIXES
        if any(key.startswith(prefix) and value for key, value in env.items())
    ]
    return found[0] if len(found) == 1 else None


def resolve_default_seat(host: str | None) -> str:
    """Pick the reviewer seat for a caller that named none.

    Returns OPEN-1's ruled ``codex`` in every case OPEN-1 contemplated —
    a Claude-hosted or host-less run — and diverges only when ``codex``
    IS the moderator, which is the one case the ruling predates.
    """
    if host != DEFAULT_SEAT:
        return DEFAULT_SEAT
    return "claude"


def _resolve_seat(seat: str | None) -> tuple[str, str | None]:
    """Return the seat to brief and the host that asked for it."""
    host = detect_moderator_host()
    resolved = resolve_default_seat(host) if seat is None else seat
    if resolved == host:
        # Reachable only when a caller NAMES the moderating seat. Allowed
        # — explicit is explicit — but it is not a cross-review, so it is
        # stamped rather than passed off as one.
        logger.warning("cross_review_self_review", seat=resolved, host=host)
    return resolved, host


def _seat_recipe(seat: str) -> tuple[str, ...]:
    for name, recipe in SEAT_RECIPES:
        if name == seat:
            return recipe
    raise ReviewTargetError(f"unknown seat: {seat!r}")


def _independence(seat: str, host: str | None) -> bool | None:
    """Is the reviewer independent of the author? ``None`` = unverified.

    Not ``False`` for an undetected host: that would assert independence
    the run has not evidenced, and the ambiguous nested-launch case
    resolves to ``codex`` — which may BE the moderator (codex D11 lane,
    2026-09-09). Consumers treat ``None`` as "do not trust a clean
    result on independence grounds".
    """
    if host is None:
        return None
    return seat == host


def _resolve_claude_auth(
    seat: str, host: str | None, claude_auth: str, invoke_seat: Callable[..., Any]
) -> str:
    """Resolve ``auto`` narrowly: only a KNOWN non-Claude host gets it.

    The cross-host case is the one where ``api`` cannot succeed anyway —
    a Codex moderator asking for the Claude seat at a zero cap gets a
    refusal instead of a review, and no single invocation can carry the
    right route for both hosts (passing ``subscription`` from a Claude
    host raises, because the seat there resolves to ``codex``).

    An UNKNOWN host resolves to ``api`` deliberately, on two grounds:
    it preserves the zero-cap refusal pinned by
    ``test_default_claude_still_refuses_zero_api_budget``, and it keeps
    the route from depending on whether a marker happened to be set —
    a CI run must not take a different route than the same call on a
    laptop.

    Known footgun, accepted by the chair 2026-09-09: if the API cap is
    ever raised deliberately, a cross-host run still prefers the
    subscription. Override with an explicit ``claude_auth="api"``.
    """
    if claude_auth != "auto":
        return claude_auth
    cross_host = host is not None and host != "claude"
    if seat == "claude" and cross_host and invoke_seat is default_invoke_seat:
        return "subscription"
    return "api"


def _validate_review_options(
    seat: str, invoke_seat: Callable[..., Any], claude_auth: str, diff_cap_chars: int
) -> None:
    """Reject invalid launch configuration before resolving or sending a diff."""
    if claude_auth not in ("api", "subscription"):
        raise ReviewTargetError("claude_auth must be api or subscription")
    if claude_auth == "subscription" and (
        seat != "claude" or invoke_seat is not default_invoke_seat
    ):
        raise ReviewTargetError("subscription review requires the real Claude seat")
    if type(diff_cap_chars) is not int or not 1 <= diff_cap_chars <= 250_000:
        raise ReviewTargetError("diff_cap_chars must be an integer from 1 to 250000")


def _invoke_review(
    seat: str, claude_auth: str, invoke_seat: Callable[..., Any], brief: str
) -> tuple[int, str]:
    """Dispatch only the explicitly selected authentication route."""
    if claude_auth == "subscription":
        from attune.roundtable.subscription_review import invoke_subscription_review

        return invoke_subscription_review(brief, reply_chars=ROLE_REPLY_CHARS["reviewer"])
    return invoke_seat(_seat_recipe(seat), brief, reply_chars=ROLE_REPLY_CHARS["reviewer"])


def run_review(
    repo_root: str | Path,
    seat: str | None = None,
    mode: str = "branch",
    base_ref: str = "origin/main",
    board: Any | None = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] = default_invoke_seat,
    prior_rejections: Sequence[str] = (),
    paths: Sequence[str] | None = None,
    claude_auth: str = "auto",
    diff_cap_chars: int = DIFF_CAP_CHARS,
    require_complete: bool = False,
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
    A ``claude``-seat review at the session spend cap raises
    :class:`~attune.gates.session_ledger.SessionSpendCapError` from
    the default invoker BEFORE any subprocess spawns
    (docs/specs/session-spend-ledger/). That refusal stops a NEW
    billable launch; it does not touch the binding posture above —
    nothing here gates a merge or scores a finding.
    ``claude_auth`` defaults to ``"auto"``, which selects ``"subscription"``
    ONLY for a real ``claude`` seat briefed from a KNOWN non-Claude host —
    the cross-host case, where ``api`` is refused at a zero cap and no one
    invocation could carry the right route for both hosts. Every other
    combination, an unknown host included, resolves to ``api``. The
    subscription route uses a verified Pro/Max login in a scrubbed,
    tool-free CLI process; neither route changes the API cap. The RESOLVED
    route is what validation checks and what the result reports, so a
    ledger row never names a route the run did not take.
    ``diff_cap_chars`` permits a deliberate bounded larger brief (up to
    250,000 characters). ``require_complete`` refuses omissions before
    invoking any seat; the default 60,000-character manifest is unchanged.
    ``paths`` scopes the review to those repo-relative files (posix
    separators) — the scoped re-lane for a PARTIAL manifest's omitted
    substantive files (2026-08-24 retro O2: the #2259 lane could not
    be re-run on the two files it omitted). Every requested path must
    be in the diff or the run raises ``ReviewTargetError`` (fail
    closed — codex D11, both rounds); the result carries
    ``scoped_to`` so the ledger row states the scope honestly.
    An omitted ``seat`` resolves against the moderating host so the run
    cannot brief the authoring seat on its own diff (OPEN-1 refined
    2026-09-09): Claude-hosted and host-less runs keep OPEN-1's ruled
    ``codex``, a Codex-hosted run gets ``claude``. Naming a seat always
    wins, including the moderator's own; the result then reports
    ``self_review: True`` rather than passing it off as a cross-review.
    ``host`` and ``self_review`` are stamped on every result so a missed
    host marker is visible in the ledger row.
    """
    seat, host = _resolve_seat(seat)
    claude_auth = _resolve_claude_auth(seat, host, claude_auth, invoke_seat)
    _validate_review_options(seat, invoke_seat, claude_auth, diff_cap_chars)
    context = {
        "host": host,
        "self_review": _independence(seat, host),
        "claude_auth": claude_auth if seat == "claude" else None,
    }
    target = resolve_target(repo_root, mode=mode, base_ref=base_ref)
    per_file = target["per_file"]
    scoped_to: list[str] | None = None
    if paths is not None:
        wanted = {PurePath(p).as_posix() for p in paths}
        misses = sorted(wanted - set(per_file))
        if misses:
            # Codex D11 findings (2026-08-24, both re-lane rounds): a
            # scope the diff cannot fully satisfy must fail LOUD. An
            # all-miss scope would brief the seat on an empty diff and
            # come back "clean" having reviewed nothing; a partial miss
            # would claim coverage of a request it silently shrank.
            # Callers re-issue with only in-diff paths.
            raise ReviewTargetError(
                "scoped review: requested path(s) not in the diff: " + ", ".join(misses)
            )
        per_file = {name: diff for name, diff in per_file.items() if name in wanted}
        scoped_to = sorted(per_file)
        # The seat must know it is reading a deliberate slice, not the
        # whole diff — scoping travels in the brief, not just the result.
        target["description"] += f" — SCOPED to {len(scoped_to)} path(s): " + ", ".join(scoped_to)
    manifest = budget_manifest(
        per_file, cap_chars=diff_cap_chars, require_complete=require_complete
    )
    brief = build_brief(target, manifest)
    if prior_rejections:
        # Bounded so a long rejection history cannot crowd out the diff
        # the seat is there to assess (re-lane finding, 2026-08-24).
        capped = [r[:300] for r in list(prior_rejections)[:12]]
        lines = "\n".join(f"- {r}" for r in capped)
        if len(prior_rejections) > 12:
            lines += f"\n- (+{len(prior_rejections) - 12} more rejections truncated)"
        brief += (
            "\n\nPreviously REJECTED findings from earlier lanes on this "
            "same diff, with the refutations. Do NOT re-report these "
            "unless you have NEW evidence that overturns the stated "
            f"refutation:\n{lines}"
        )

    code, reply = _invoke_review(seat, claude_auth, invoke_seat, brief)
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
                **context,
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
        **context,
    }
    if scoped_to is not None:
        result["scoped_to"] = scoped_to
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


def clean_disposition(manifest: dict[str, Any]) -> str:
    """Render the disposition for a lane that reviewed and found nothing.

    A clean lane over a PARTIAL manifest is the case the spec warns
    about ("never describe a partial or absent review as complete"), so
    the omission is stated in the row itself rather than left to the
    reader to notice two columns to the left.
    """
    omitted = len(manifest["omitted"])
    sent = len(manifest["sent"])
    if omitted:
        return (
            f"clean \u2014 no findings, but the manifest OMITTED {omitted} "
            "file(s): clean-on-partial, re-lane scoped to them before relying on it"
        )
    return f"clean \u2014 no findings; complete manifest ({sent} files sent)"


def ledger_row(result: dict[str, Any], disposition: str = "not-triaged") -> str:
    """Render the R5 dogfood-ledger row for the spec's receipts.md.

    Any disposition other than the ``not-triaged`` placeholder is
    validated against both ledger gates' grammars at authoring time
    (:func:`check_disposition`); a non-compliant one raises rather than
    shipping a row CI will reject two rounds later.

    A lane whose status is ``clean`` gets its disposition filled in
    automatically (:func:`clean_disposition`). The placeholder is not a
    legal disposition -- ``ledger_precision``'s tally rejects any row it
    cannot classify -- so emitting it for the COMMON case of a
    no-findings lane made the module's own output unmergeable by its own
    pre-commit gate, and every clean lane cost a hand-edit (2026-09-08).
    ``absent`` and ``format_noncompliant`` lanes keep the placeholder:
    they also carry zero findings, but they judged nothing, and calling
    that "clean" would be a lie the tally is designed to skip.
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest = result["manifest"]
    if disposition == "not-triaged" and result.get("status") == "clean":
        disposition = clean_disposition(manifest)
    if disposition != "not-triaged":
        problems = check_disposition(disposition, len(result["findings"]))
        if problems:
            raise ValueError("ledger disposition fails the gates: " + "; ".join(problems))
    return (
        f"| {date} | {result['seat']} | {result['target']}; "
        f"host={result.get('host') or 'unknown'}, "
        f"self_review={json.dumps(result.get('self_review'))}, "
        f"claude_auth={result.get('claude_auth') or 'n/a'} | "
        f"{len(manifest['sent'])} sent / {len(manifest['omitted'])} omitted | "
        f"{len(result['findings'])} ({result['status']}) | {disposition} |"
    )


def load_review_result(path: Path) -> dict[str, Any]:
    """Parse a captured ``run_review`` stdout file.

    The result is the LAST non-empty line: a capture made with the
    pre-#2524 snippet carries structlog's digest line ahead of the JSON,
    and the parse must not fail on it (retro 2026-09-11 item 1).
    """
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"{path}: no review result found (empty file)")
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: last line is not a JSON review result: {exc}") from exc
    if not isinstance(result, dict) or "manifest" not in result or "findings" not in result:
        raise ValueError(f"{path}: last line is not a run_review result")
    return result


def ledger_cli(argv: list[str] | None = None) -> int:
    """``python -m attune.roundtable ledger`` — render (and append) an R5 ledger row.

    The skill's step 4 used to be "append ``review.ledger_row(result)``",
    and every session hand-wrote the same dozen lines to load the
    capture, pass the disposition and validate it (retro 2026-09-12
    item 1). Exit 1 with the gate problems on stderr when the
    disposition would fail the ledger gates; nothing is appended then.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m attune.roundtable ledger",
        description="Render the R5 dogfood-ledger row for a captured cross-review result.",
    )
    parser.add_argument("--result", required=True, type=Path, help="captured run_review stdout")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--disposition", help="disposition text (validated against the gates)")
    group.add_argument("--disposition-file", type=Path, help="file holding the disposition text")
    parser.add_argument(
        "--append",
        type=Path,
        metavar="RECEIPTS_MD",
        help="append the row to this ledger file after printing it",
    )
    args = parser.parse_args(argv)
    disposition = "not-triaged"
    if args.disposition is not None:
        disposition = args.disposition.strip()
    elif args.disposition_file is not None:
        disposition = args.disposition_file.read_text(encoding="utf-8").strip()
    try:
        row = ledger_row(load_review_result(args.result), disposition)
    except ValueError as exc:
        print(f"ledger: {exc}", file=sys.stderr)
        return 1
    print(row)
    if args.append is not None:
        with args.append.open("a", encoding="utf-8") as handle:
            handle.write(row + "\n")
    return 0
