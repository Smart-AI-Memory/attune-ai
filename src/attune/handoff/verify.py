"""Read-only git state reads and drift detection for handoff packets.

Design D2/D3 (docs/specs/cross-provider-session-handoff/design.md):
every git call here is read-only; drift results are report-only
warnings, never blocking and never auto-fixed.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_GIT_TIMEOUT_SECONDS = 15.0

#: Days before a packet earns the ``packet_stale_days`` warning.
STALE_AFTER_DAYS = 7

#: The only git subcommands this module may run (read-only guard).
_ALLOWED_SUBCOMMANDS = frozenset({"branch", "rev-parse", "merge-base", "diff", "status"})


class GitReadError(RuntimeError):
    """A read-only git command failed."""


def _git(repo_root: Path, *args: str) -> str:
    """Run an allowlisted read-only git command and return stdout.

    Raises:
        GitReadError: on a non-allowlisted subcommand, a non-zero
            exit, or a timeout.

    """
    if not args or args[0] not in _ALLOWED_SUBCOMMANDS:
        raise GitReadError(f"subcommand not allowlisted: {args[:1]}")
    try:
        result = subprocess.run(  # noqa: S603 - fixed binary, allowlisted args
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("handoff_git_read_failed", args=args, error=str(exc))
        raise GitReadError(f"git {' '.join(args)}: {exc}") from exc
    if result.returncode != 0:
        raise GitReadError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def slugify_branch(branch: str) -> str:
    """Contract slug rule: ``/`` becomes ``-`` (no other rewriting)."""
    return branch.replace("/", "-")


def snapshot(repo_root: Path, base_ref: str = "origin/main") -> dict[str, Any]:
    """Read the VERIFIED git facts for a packet (R1).

    Every field comes from git at call time; caller input never
    enters this dict. ``merge_base``/``changed_files`` degrade to
    ``None``/``[]`` with an explicit ``merge_base_error`` rather
    than guessing.
    """
    branch = _git(repo_root, "branch", "--show-current")
    head_sha = _git(repo_root, "rev-parse", "HEAD")
    facts: dict[str, Any] = {
        "branch": branch,
        "head_sha": head_sha,
        "base_ref": base_ref,
        "merge_base": None,
        "changed_files": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        merge_base = _git(repo_root, "merge-base", "HEAD", base_ref)
        facts["merge_base"] = merge_base
        raw = _git(repo_root, "diff", "--name-only", merge_base, "HEAD")
        facts["changed_files"] = sorted(line for line in raw.splitlines() if line)
    except GitReadError as exc:
        facts["merge_base_error"] = str(exc)
    return facts


def _packet_age_days(created_at: str) -> float | None:
    try:
        created = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).total_seconds() / 86400.0


def drift(
    meta: dict[str, Any],
    repo_root: Path,
    ignore_paths: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """The D3 drift matrix: report-only warning dicts.

    Codes: ``branch_missing``, ``head_moved``, ``files_diverged``,
    ``packet_stale_days``, ``dirty_tree``. ``ignore_paths`` (repo-
    relative, POSIX) are excluded from the dirty-tree check — the
    packet file itself must not flag the resume that reads it.
    """
    warnings: list[dict[str, Any]] = []
    branch = meta.get("branch") or ""

    try:
        _git(repo_root, "rev-parse", "--verify", f"refs/heads/{branch}")
        branch_exists = True
    except GitReadError:
        branch_exists = False
        warnings.append({"code": "branch_missing", "detail": f"branch {branch!r} not found"})

    current_head = _git(repo_root, "rev-parse", "HEAD")
    if meta.get("head_sha") and current_head != meta["head_sha"]:
        warnings.append(
            {
                "code": "head_moved",
                "detail": f"packet {meta['head_sha'][:9]} vs current " f"{current_head[:9]}",
            }
        )

    if branch_exists and meta.get("merge_base"):
        try:
            raw = _git(repo_root, "diff", "--name-only", meta["merge_base"], "HEAD")
            current_files = sorted(line for line in raw.splitlines() if line)
            if current_files != sorted(meta.get("changed_files") or []):
                warnings.append(
                    {
                        "code": "files_diverged",
                        "detail": {
                            "packet": meta.get("changed_files") or [],
                            "current": current_files,
                        },
                    }
                )
        except GitReadError as exc:
            warnings.append({"code": "files_diverged", "detail": str(exc)})

    age = _packet_age_days(meta.get("created_at", ""))
    if age is not None and age > STALE_AFTER_DAYS:
        warnings.append({"code": "packet_stale_days", "detail": round(age, 1)})

    def _ignored(entry: str) -> bool:
        # Untracked dirs surface as ``dir/`` — an ignore path inside
        # that dir still means "only the packet lives there".
        return any(
            entry == p or (entry.endswith("/") and p.startswith(entry)) for p in ignore_paths
        )

    porcelain = [
        line
        for line in _git(repo_root, "status", "--porcelain").splitlines()
        if not _ignored(line[3:].strip().strip('"'))
    ]
    if porcelain:
        warnings.append({"code": "dirty_tree", "detail": "uncommitted changes present"})

    return warnings
