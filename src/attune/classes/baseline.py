"""Release-audit baseline resolution (release-audit-stage R3 step 0).

The stage asks what class of defect *this release* could have
introduced, so every later step is relative to one resolved point:

    git diff $(git merge-base <last-release-tag> HEAD)..HEAD

with a ``--baseline <ref>`` override. The resolved SHA is recorded in
the manifest (R7) so a reader can reproduce exactly what was swept.

**Fails closed, never guesses** (R3): no release tag, a shallow clone,
or an unresolvable override raises :class:`BaselineError` rather than
falling back to a default range. A guessed range would make the whole
audit assert something untrue — an empty sweep reads identically
whether the diff is clean or the range was wrong.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Baseline", "BaselineError", "resolve_baseline", "changed_files", "deleted_files"]

#: Release tags look like ``v1.2.3``. Anything else (a moved pointer, a
#: dated snapshot tag) is not a release boundary and must not silently
#: become one.
_RELEASE_TAG = re.compile(r"^v\d+\.\d+\.\d+$")

#: Extensions the rule pack cannot parse. Kept in step with the sweep's
#: own filters (R1: "binary/generated files are excluded by the same
#: filters the sweep suite used") — the sweep only parses Python.
_SCANNABLE_SUFFIXES = frozenset({".py"})


class BaselineError(RuntimeError):
    """Preflight failure — the audit has no valid range to work from.

    Carries ``reason`` so a caller can render a structured diagnostic
    instead of a bare string.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class Baseline:
    """One resolved audit range."""

    #: The tag the range starts from, or None when explicitly overridden.
    tag: str | None
    #: The merge-base SHA the sweep is relative to (full 40 chars).
    baseline_sha: str
    #: The commit being audited (full 40 chars).
    head_sha: str
    #: How the range was chosen — "last-release-tag" or "override".
    source: str
    #: Repo-relative paths added or modified in the range, scannable only.
    changed: tuple[str, ...] = field(default=())
    #: Scannable paths DELETED in the range. Skipped by the sweep (there
    #: is nothing left to scan) but load-bearing for the packet's public
    #: symbol delta — a deleted module is the clearest surface removal
    #: there is, and 14.0.0's own breaking change lives in one.
    deleted: tuple[str, ...] = field(default=())

    @property
    def tag_range(self) -> str:
        """Human-readable range for the packet header (R4 §0)."""
        return f"{self.tag or self.baseline_sha[:9]}..{self.head_sha[:9]}"


def _git(repo_root: Path, *args: str, check: bool = True) -> str:
    """Run one git command in ``repo_root`` and return stripped stdout."""
    try:
        result = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BaselineError("git-unavailable", f"{args[0]}: {exc}") from exc
    if check and result.returncode != 0:
        raise BaselineError(
            "git-failed", f"{' '.join(args)}: {result.stderr.strip() or result.returncode}"
        )
    return result.stdout.strip()


def _assert_full_clone(repo_root: Path) -> None:
    """A shallow clone cannot resolve a merge-base — fail closed (R3)."""
    if _git(repo_root, "rev-parse", "--is-shallow-repository") == "true":
        raise BaselineError(
            "shallow-clone",
            "merge-base against a release tag needs full history; "
            "fetch with --unshallow before auditing",
        )


def last_release_tag(repo_root: Path) -> str:
    """Newest ``vX.Y.Z`` tag by version order.

    Sorted by ``version:refname`` rather than commit date so a tag
    pushed late for an older release cannot masquerade as the latest.
    """
    raw = _git(repo_root, "tag", "--list", "v*", "--sort=-version:refname")
    for line in raw.splitlines():
        candidate = line.strip()
        if _RELEASE_TAG.match(candidate):
            return candidate
    raise BaselineError(
        "no-release-tag",
        "no vX.Y.Z tag found; pass --baseline <ref> to audit an explicit range",
    )


def changed_files(repo_root: Path, baseline_sha: str, head: str = "HEAD") -> tuple[str, ...]:
    """Scannable repo-relative paths added or modified in the range.

    R1 scan-path semantics: deleted files are skipped (nothing left to
    scan), a rename scans the NEW path, and files the rule pack cannot
    parse are excluded by the same filter the sweep uses.
    """
    raw = _git(repo_root, "diff", "--name-status", "-M", f"{baseline_sha}..{head}")
    paths: list[str] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status.startswith("D"):
            continue  # deleted — nothing to scan
        # A rename/copy row is "R100\told\tnew"; scan the new path.
        path = parts[-1]
        if Path(path).suffix in _SCANNABLE_SUFFIXES:
            paths.append(path)
    # Deterministic order so a packet hash is stable across runs.
    return tuple(sorted(dict.fromkeys(paths)))


def deleted_files(repo_root: Path, baseline_sha: str, head: str = "HEAD") -> tuple[str, ...]:
    """Scannable repo-relative paths DELETED in the range.

    The sweep skips these, but the packet's §0 symbol delta must not:
    removing a module removes every public name it exported.
    """
    raw = _git(repo_root, "diff", "--name-status", "-M", f"{baseline_sha}..{head}")
    paths = [
        parts[1]
        for line in raw.splitlines()
        if (parts := line.split("\t")) and len(parts) >= 2 and parts[0].startswith("D")
        if Path(parts[1]).suffix in _SCANNABLE_SUFFIXES
    ]
    return tuple(sorted(dict.fromkeys(paths)))


def resolve_baseline(
    repo_root: Path | None = None,
    *,
    override: str | None = None,
    head: str = "HEAD",
) -> Baseline:
    """Resolve the audit range, or raise :class:`BaselineError`.

    Args:
        repo_root: Repository to audit; defaults to the current directory.
        override: An explicit ref to diff from (``--baseline``). When
            given, no tag lookup happens — the caller has named the range.
        head: The commit being audited.

    Returns:
        A :class:`Baseline` with both SHAs resolved to full 40 characters
        and the scannable changed-file list attached.

    Raises:
        BaselineError: No release tag, a shallow clone, or a ref that
            does not resolve. Never returns a guessed range.

    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    _assert_full_clone(root)

    head_sha = _git(root, "rev-parse", head)

    if override is not None:
        try:
            start = _git(root, "rev-parse", override)
        except BaselineError as exc:
            raise BaselineError("bad-baseline-ref", f"{override!r} does not resolve") from exc
        tag: str | None = None
        source = "override"
    else:
        tag = last_release_tag(root)
        start = _git(root, "rev-parse", tag)
        source = "last-release-tag"

    merge_base = _git(root, "merge-base", start, head_sha)

    return Baseline(
        tag=tag,
        baseline_sha=merge_base,
        head_sha=head_sha,
        source=source,
        changed=changed_files(root, merge_base, head_sha),
        deleted=deleted_files(root, merge_base, head_sha),
    )
