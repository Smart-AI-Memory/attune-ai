# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Curating sweep (R3) — dedupe, lint, flag, compose ONE digest.

The sweep never ships anything: it composes a one-screen digest for
chair approval (R4 — chip click spawns the approve-and-PR session,
which runs ``apply``).

Memory lint is NOT wired in Phase 1: no ratified kind targets a
memory directory, and the home linter
(``~/.claude/hooks/memory_lint.py``) takes ``--check-all DIR`` /
stdin-JSON hook input rather than a file argument, so a per-artifact
call could only ever fail open. Wire it when a memory-targeting kind
lands (recorded in the spec's D3).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from attune.docs_outbox.routing import OUTBOX_TARGETS
from attune.docs_outbox.store import (
    DIGEST_NAME,
    Artifact,
    OutboxStatus,
    _atomic_write,
    archive_swept,
    list_artifacts,
    outbox_dir,
    outbox_status,
)
from attune.security.path_validation import _validate_file_path

#: Chair reviews these anyway — the flag is a hint, not a gate.
_CORE_WORTHY_TERMS = (
    "secret",
    "credential",
    "security",
    "data loss",
    "destructive",
    "corrupt",
    "leak",
    "revoke",
)


@dataclass
class SweepResult:
    """Everything the digest (and the approve session) needs."""

    kept: list[Artifact] = field(default_factory=list)
    dropped_duplicates: list[Artifact] = field(default_factory=list)
    related_slugs: list[str] = field(default_factory=list)
    core_worthy: list[str] = field(default_factory=list)
    lint_issues: dict[str, list[str]] = field(default_factory=dict)
    apply_failures: dict[str, str] = field(default_factory=dict)
    status: OutboxStatus | None = None
    digest: str = ""

    @property
    def clean(self) -> bool:
        return not self.lint_issues


def _dedupe(artifacts: list[Artifact]) -> tuple[list[Artifact], list[Artifact], list[str]]:
    """Drop exact duplicates (keep earliest); flag same-slug kin.

    The duplicate key is ``(kind, target, body)``, not the body alone:
    two artifacts with identical prose bound for DIFFERENT files are
    two pieces of work, and dropping one silently loses it.
    """
    kept: list[Artifact] = []
    dropped: list[Artifact] = []
    seen: set[str] = set()
    slug_counts: dict[tuple[str, str], int] = {}
    for artifact in artifacts:
        payload = f"{artifact.kind}\0{artifact.target}\0{artifact.body.strip()}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if digest in seen:
            dropped.append(artifact)
            continue
        seen.add(digest)
        kept.append(artifact)
        key = (artifact.kind, artifact.slug)
        slug_counts[key] = slug_counts.get(key, 0) + 1
    related = sorted(f"{kind}/{slug}" for (kind, slug), n in slug_counts.items() if n > 1)
    return kept, dropped, related


def _lint(artifact: Artifact, repo_root: Path, claimed: set[str]) -> list[str]:
    """Structural lint; every issue blocks apply for that artifact.

    ``claimed`` accumulates targets claimed by earlier artifacts in the
    SAME sweep, so two artifacts creating the same new file collide at
    lint time instead of one silently overwriting the other.
    """
    issues = list(artifact.issues)
    # The kind is read off disk, so it is NOT guaranteed to have come
    # through write_artifact's routing gate — an unrecognized kind must
    # never reach apply, where it would take the file-replacing branch.
    if not artifact.kind:
        issues.append("missing kind")
    elif artifact.kind not in OUTBOX_TARGETS:
        issues.append(f"kind {artifact.kind!r} is not an outbox kind")
    if not artifact.target:
        issues.append("missing target")
    elif Path(artifact.target).is_absolute() or artifact.target.startswith(("/", "\\")):
        # startswith covers rooted paths ("/etc/x"), which Windows
        # does not consider absolute but must still be rejected.
        issues.append("target must be repo-relative")
    elif not artifact.target.endswith(".md"):
        issues.append("target must be a .md file")
    else:
        default = OUTBOX_TARGETS.get(artifact.kind)
        if default and artifact.target != default:
            # Kinds with a default target are mechanically routed (R2):
            # an appending kind pointed anywhere else could append prose
            # into an unrelated tracked file.
            issues.append(f"kind {artifact.kind!r} must target {default}")
        try:
            _validate_file_path(str(repo_root / artifact.target), allowed_dir=str(repo_root))
        except ValueError as exc:
            issues.append(f"target rejected: {exc}")
        if not default:
            if (repo_root / artifact.target).exists():
                issues.append("target already exists — refusing overwrite")
            elif artifact.target in claimed:
                issues.append("another artifact in this sweep already claims this target")
            else:
                claimed.add(artifact.target)
    if not artifact.body.strip():
        issues.append("empty body")
    elif artifact.kind == "lesson" and not artifact.body.lstrip().startswith("- **"):
        # The lessons index (attune.lessons) anchors entry parsing on
        # lines starting "- **"; an unbulleted entry appends cleanly
        # but is invisible to recall.
        issues.append("lesson body must start with '- **' (bulleted bold title)")
    return issues


def run_sweep(repo_root: Path, attune_home: Path | None = None) -> SweepResult:
    """Collect -> dedupe -> lint -> flag -> compose; write digest.md."""
    result = SweepResult(status=outbox_status(attune_home))
    artifacts = list_artifacts(attune_home)
    result.kept, result.dropped_duplicates, result.related_slugs = _dedupe(artifacts)
    claimed: set[str] = set()
    for artifact in result.kept:
        issues = _lint(artifact, repo_root, claimed)
        if issues:
            result.lint_issues[artifact.path.name] = issues
        if artifact.kind == "lesson" and any(
            term in artifact.body.lower() for term in _CORE_WORTHY_TERMS
        ):
            result.core_worthy.append(artifact.path.name)
    result.digest = _compose_digest(result)
    if result.kept or result.dropped_duplicates:
        _atomic_write(outbox_dir(attune_home) / DIGEST_NAME, result.digest)
    return result


def _cell(text: str) -> str:
    """Escape a value for a markdown table cell."""
    return text.replace("|", "\\|")


def _compose_digest(result: SweepResult) -> str:
    """One-screen markdown digest — the chip's payload (R4)."""
    status = result.status
    lines = ["# Docs outbox digest", ""]
    if not result.kept and not result.dropped_duplicates:
        lines += ["Outbox is empty — nothing to sweep.", ""]
        return "\n".join(lines)
    if status is None:  # pragma: no cover — run_sweep always sets it
        return "\n".join(lines)
    stale = " — **STALE (2+ days), sweep overdue**" if status.stale else ""
    lines += [
        f"{status.count} pending, oldest {status.oldest_days}d{stale}",
        "",
        "| Artifact | Kind | Target | Flags |",
        "|---|---|---|---|",
    ]
    for artifact in result.kept:
        flags = []
        if artifact.path.name in result.core_worthy:
            flags.append("core-worthy?")
        if f"{artifact.kind}/{artifact.slug}" in result.related_slugs:
            flags.append("related-slug")
        flags.extend(result.lint_issues.get(artifact.path.name, []))
        lines.append(
            f"| {artifact.path.name} | {artifact.kind} | {_cell(artifact.target)} "
            f"| {_cell('; '.join(flags)) or '—'} |"
        )
    for artifact in result.dropped_duplicates:
        lines.append(
            f"| ~~{artifact.path.name}~~ | {artifact.kind} | — | exact duplicate, dropped |"
        )
    lines += [
        "",
        "Approve: run `python -m attune.docs_outbox apply` in a repo",
        "session, commit the changes, and open ONE auto-merge PR.",
        "Artifacts with lint issues are skipped by apply.",
        "",
    ]
    return "\n".join(lines)


def apply_sweep(
    repo_root: Path, attune_home: Path | None = None, result: SweepResult | None = None
) -> list[Path]:
    """Write clean artifacts into the repo; archive them as swept.

    Lessons append to their target in timestamp order; reports,
    drafts, and plans create their target file. Artifacts with lint
    issues stay in the outbox untouched. Returns changed repo paths.
    """
    result = result or run_sweep(repo_root, attune_home)
    changed: list[Path] = []
    for artifact in result.kept:
        if artifact.path.name in result.lint_issues:
            continue
        try:
            target = _apply_one(artifact, repo_root)
        except (OSError, ValueError) as exc:
            # One bad artifact must not abort the batch, and must not
            # be archived — it stays pending for the next sweep.
            result.apply_failures[artifact.path.name] = str(exc)
            continue
        # Archive immediately, per artifact: a crash later in the loop
        # must never leave an APPLIED artifact still pending, which
        # would re-apply (and duplicate) it on the next run.
        archive_swept([artifact], attune_home)
        if target not in changed:
            changed.append(target)
    archive_swept(result.dropped_duplicates, attune_home)
    _refresh_digest(repo_root, attune_home)
    return changed


def _apply_one(artifact: Artifact, repo_root: Path) -> Path:
    """Write one artifact into the repo; return the changed path."""
    target = repo_root / artifact.target
    _validate_file_path(str(target), allowed_dir=str(repo_root))
    target.parent.mkdir(parents=True, exist_ok=True)
    body = artifact.body if artifact.body.endswith("\n") else artifact.body + "\n"
    if OUTBOX_TARGETS.get(artifact.kind) and target.exists():
        existing = target.read_text(encoding="utf-8")
        joiner = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        body = existing + joiner + body
    _atomic_write(target, body)
    return target


def _refresh_digest(repo_root: Path, attune_home: Path | None) -> None:
    """Rewrite digest.md post-apply so the chip can't show a stale batch."""
    digest = outbox_dir(attune_home) / DIGEST_NAME
    remaining = run_sweep(repo_root, attune_home)
    if not remaining.kept and not remaining.dropped_duplicates and digest.exists():
        digest.unlink()
