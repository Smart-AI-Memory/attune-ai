"""Solution materializer — round-table V2-P3.

Members are text-in/text-out (R1): a proposed solution arrives as
TEXT — full-file blocks or a unified diff. This module is the
moderator's side of the bargain: parse the proposal, validate every
path, materialize it in an ISOLATED scratch git worktree (never a
tracked branch), run the named checks serially, and return
receipts. A failing candidate is returned failed-with-receipts —
never silently dropped, never laundered green (TAC-4). The repair
round and cross-seat review are loop orchestration in the skill;
this module owns the mechanics.

Proposal text format (antigravity's apply-ready contract,
table-v2-001): one or more fenced full-file blocks::

    --- file: path/to/target.py
    ```
    <complete new file content>
    ```

or a standard unified diff (``diff --git`` / ``---``/``+++``
headers), applied with ``git apply``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 — fixed argv git/check commands, never shell=True
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

#: Output kept per check (tail — failure summaries live at the end).
RECEIPT_TAIL_CHARS = 2000

_CHECK_TIMEOUT = 600

_FILE_BLOCK_RE = re.compile(
    r"^--- file:\s*(?P<path>\S+)\s*\n```[a-zA-Z0-9_-]*\n(?P<body>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


class ProposalError(ValueError):
    """A member proposal that cannot be safely materialized."""


@dataclass
class CheckReceipt:
    """One validation command's outcome — the chair-facing evidence."""

    label: str
    argv: list[str]
    exit_code: int
    tail: str

    @property
    def passed(self) -> bool:
        """True when the command exited 0."""
        return self.exit_code == 0


@dataclass
class Candidate:
    """A materialized proposal plus its validation receipts."""

    worktree: Path
    files: list[str]
    receipts: list[CheckReceipt] = field(default_factory=list)

    @property
    def green(self) -> bool:
        """True only when every receipt passed (and at least one ran)."""
        return bool(self.receipts) and all(r.passed for r in self.receipts)


def _validate_rel_path(raw: str) -> str:
    """Reject absolute, traversal, and git-internal paths (security).

    Raises:
        ProposalError: On any path that could escape the scratch
            worktree or touch git internals.
    """
    path = raw.strip()
    if not path:
        raise ProposalError("empty file path in proposal")
    pure = Path(path)
    if pure.is_absolute() or path.startswith(("~", "\\")) or re.match(r"^[A-Za-z]:", path):
        raise ProposalError(f"absolute path rejected: {path!r}")
    parts = pure.parts
    if ".." in parts:
        raise ProposalError(f"path traversal rejected: {path!r}")
    if parts and parts[0] == ".git":
        raise ProposalError(f"git-internal path rejected: {path!r}")
    return path


def parse_proposal(text: str) -> dict[str, str]:
    """Parse full-file blocks from a member proposal.

    Returns:
        Mapping of validated relative path -> complete file content.
        Empty when the text carries no file blocks (it may instead be
        a unified diff — see :func:`materialize`).

    Raises:
        ProposalError: On an invalid target path.
    """
    return {
        _validate_rel_path(m.group("path")): m.group("body") for m in _FILE_BLOCK_RE.finditer(text)
    }


def _git(worktree: Path | None, *args: str) -> subprocess.CompletedProcess:
    argv = ["git", *(("-C", str(worktree)) if worktree else ()), *args]
    return subprocess.run(  # nosec B603 — fixed argv, shell=False
        argv, capture_output=True, text=True, timeout=_CHECK_TIMEOUT
    )


def _diff_paths(diff_text: str) -> list[str]:
    """Validate and return every target path named by a unified diff."""
    paths: list[str] = []
    for m in re.finditer(r"^\+\+\+ (?:b/)?(\S+)", diff_text, re.MULTILINE):
        raw = m.group(1)
        if raw != "/dev/null":
            paths.append(_validate_rel_path(raw))
    if not paths:
        raise ProposalError("unified diff names no target files")
    return paths


def materialize(
    proposal_text: str,
    repo: Path,
    base_ref: str = "HEAD",
    scratch_root: Path | None = None,
) -> Candidate:
    """Materialize one member proposal into a fresh scratch worktree.

    The worktree is detached at ``base_ref`` under a temp directory —
    never a tracked branch; promotion to a real branch is a separate,
    chair-gated step. File-block proposals are written directly;
    otherwise the text is treated as a unified diff and applied with
    ``git apply`` (checked first, so a non-applying diff fails clean).

    Raises:
        ProposalError: Invalid paths, an unparseable/empty proposal,
            or a diff that does not apply.
        RuntimeError: Worktree creation failed.
    """
    root = scratch_root or Path(tempfile.gettempdir())
    worktree = root / f"rt-candidate-{uuid.uuid4().hex[:12]}"
    created = _git(repo, "worktree", "add", "--detach", str(worktree), base_ref)
    if created.returncode != 0:
        raise RuntimeError(f"worktree add failed: {created.stderr.strip()[:300]}")
    try:
        files = parse_proposal(proposal_text)
        if files:
            for rel, body in files.items():
                target = worktree / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
            touched = sorted(files)
        else:
            touched = _diff_paths(proposal_text)
            applied = subprocess.run(  # nosec B603 — fixed argv
                ["git", "-C", str(worktree), "apply", "-"],
                input=proposal_text,
                capture_output=True,
                text=True,
                timeout=_CHECK_TIMEOUT,
            )
            if applied.returncode != 0:
                raise ProposalError(f"diff does not apply: {applied.stderr.strip()[:300]}")
        return Candidate(worktree=worktree, files=touched)
    except Exception:
        discard(Candidate(worktree=worktree, files=[]))
        raise


def validate(candidate: Candidate, checks: list[tuple[str, list[str]]]) -> Candidate:
    """Run the named checks SERIALLY in the scratch worktree.

    Every check produces a :class:`CheckReceipt` with the exact output
    tail — including failures (TAC-4: failed candidates carry their
    receipts to the chair; they are never silently dropped). Checks
    run with cwd = the scratch worktree.
    """
    for label, argv in checks:
        try:
            proc = subprocess.run(  # nosec B603 — caller-fixed argv, shell=False
                argv,
                cwd=candidate.worktree,
                capture_output=True,
                text=True,
                timeout=_CHECK_TIMEOUT,
            )
            code, out = proc.returncode, (proc.stdout + proc.stderr).strip()
        except FileNotFoundError:
            code, out = 127, f"{argv[0]}: not found"
        except subprocess.TimeoutExpired:
            code, out = 124, f"timed out after {_CHECK_TIMEOUT}s"
        candidate.receipts.append(
            CheckReceipt(
                label=label, argv=list(argv), exit_code=code, tail=out[-RECEIPT_TAIL_CHARS:]
            )
        )
    return candidate


def diff_against_base(candidate: Candidate, repo: Path) -> str:
    """Return the candidate's diff vs its base — what the chair reviews."""
    proc = _git(candidate.worktree, "diff", "HEAD")
    untracked = _git(candidate.worktree, "ls-files", "--others", "--exclude-standard")
    parts = [proc.stdout]
    for new_file in untracked.stdout.split():
        shown = _git(candidate.worktree, "diff", "--no-index", "/dev/null", new_file)
        parts.append(shown.stdout)
    return "".join(parts)


def discard(candidate: Candidate) -> None:
    """Remove the scratch worktree (rejection or cleanup). Best-effort."""
    try:
        repo_probe = _git(candidate.worktree, "rev-parse", "--git-common-dir")
        common = repo_probe.stdout.strip()
        if common:
            repo = Path(common).parent if common.endswith(".git") else None
            _git(repo, "worktree", "remove", "--force", str(candidate.worktree))
    except (OSError, subprocess.SubprocessError):
        pass
    if candidate.worktree.exists():  # fallback when git couldn't remove it
        import shutil

        shutil.rmtree(candidate.worktree, ignore_errors=True)
