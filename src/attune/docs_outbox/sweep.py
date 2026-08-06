# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Curating sweep (R3) — dedupe, lint, flag, compose ONE digest.

The sweep never ships anything: it composes a one-screen digest for
chair approval (R4 — chip click spawns the approve-and-PR session,
which runs ``apply``). Memory lint runs best-effort when the home
linter exists; its absence degrades silently.
"""

from __future__ import annotations

import hashlib
import subprocess  # nosec B404 — fixed argv, home lint script, never shell=True
import sys
from dataclasses import dataclass, field
from pathlib import Path

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

_MEMORY_LINT = Path.home() / ".claude" / "hooks" / "memory_lint.py"


@dataclass
class SweepResult:
    """Everything the digest (and the approve session) needs."""

    kept: list[Artifact] = field(default_factory=list)
    dropped_duplicates: list[Artifact] = field(default_factory=list)
    related_slugs: list[str] = field(default_factory=list)
    core_worthy: list[str] = field(default_factory=list)
    lint_issues: dict[str, list[str]] = field(default_factory=dict)
    status: OutboxStatus | None = None
    digest: str = ""

    @property
    def clean(self) -> bool:
        return not self.lint_issues


def _dedupe(artifacts: list[Artifact]) -> tuple[list[Artifact], list[Artifact], list[str]]:
    """Drop exact-body duplicates (keep earliest); flag same-slug kin."""
    kept: list[Artifact] = []
    dropped: list[Artifact] = []
    seen_bodies: dict[str, Artifact] = {}
    slug_counts: dict[tuple[str, str], int] = {}
    for artifact in artifacts:
        digest = hashlib.sha256(artifact.body.strip().encode("utf-8")).hexdigest()
        if digest in seen_bodies:
            dropped.append(artifact)
            continue
        seen_bodies[digest] = artifact
        kept.append(artifact)
        key = (artifact.kind, artifact.slug)
        slug_counts[key] = slug_counts.get(key, 0) + 1
    related = sorted(f"{kind}/{slug}" for (kind, slug), n in slug_counts.items() if n > 1)
    return kept, dropped, related


def _memory_lint(artifact: Artifact) -> list[str]:
    """Home memory linter, best effort — only for memory-dir targets."""
    if "/memory/" not in artifact.target.replace("\\", "/"):
        return []
    if not _MEMORY_LINT.is_file():
        return []
    try:
        proc = subprocess.run(  # nosec B603 — fixed script, no shell
            [sys.executable, str(_MEMORY_LINT), str(artifact.path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        detail = (proc.stdout or proc.stderr or "").strip()
        return [f"memory lint: {detail[:200]}" if detail else "memory lint failed"]
    return []


def _lint(artifact: Artifact, repo_root: Path) -> list[str]:
    """Structural lint; every issue blocks apply for that artifact."""
    issues = list(artifact.issues)
    if not artifact.kind:
        issues.append("missing kind")
    if not artifact.target:
        issues.append("missing target")
    elif Path(artifact.target).is_absolute() or artifact.target.startswith(("/", "\\")):
        # startswith covers rooted paths ("/etc/x"), which Windows
        # does not consider absolute but must still be rejected.
        issues.append("target must be repo-relative")
    else:
        try:
            _validate_file_path(str(repo_root / artifact.target), allowed_dir=str(repo_root))
        except ValueError as exc:
            issues.append(f"target rejected: {exc}")
    if not artifact.body.strip():
        issues.append("empty body")
    if artifact.kind in ("report", "draft", "plan") and artifact.target:
        if (repo_root / artifact.target).exists():
            issues.append("target already exists — refusing overwrite")
    issues.extend(_memory_lint(artifact))
    return issues


def run_sweep(repo_root: Path, attune_home: Path | None = None) -> SweepResult:
    """Collect -> dedupe -> lint -> flag -> compose; write digest.md."""
    result = SweepResult(status=outbox_status(attune_home))
    artifacts = list_artifacts(attune_home)
    result.kept, result.dropped_duplicates, result.related_slugs = _dedupe(artifacts)
    for artifact in result.kept:
        issues = _lint(artifact, repo_root)
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
            f"| {artifact.path.name} | {artifact.kind} | {artifact.target} "
            f"| {'; '.join(flags) or '—'} |"
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
    applied: list[Artifact] = []
    for artifact in result.kept:
        if artifact.path.name in result.lint_issues:
            continue
        target = repo_root / artifact.target
        _validate_file_path(str(target), allowed_dir=str(repo_root))
        target.parent.mkdir(parents=True, exist_ok=True)
        body = artifact.body if artifact.body.endswith("\n") else artifact.body + "\n"
        if artifact.kind == "lesson" and target.exists():
            existing = target.read_text(encoding="utf-8")
            joiner = (
                "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
            )
            target.write_text(existing + joiner + body, encoding="utf-8")
        else:
            target.write_text(body, encoding="utf-8")
        changed.append(target)
        applied.append(artifact)
    archive_swept(applied + result.dropped_duplicates, attune_home)
    return changed
