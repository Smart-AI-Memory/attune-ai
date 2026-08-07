# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Outbox store (R1) — flat dir, per-artifact timestamped files.

Concurrent writers are conflict-free by construction: every artifact
is its own file (``20260806-1432-lesson-<slug>.md``); the sweep
concatenates in timestamp order. No long-lived branch, no armed-PR
window. Writes are atomic (temp file + ``os.replace``) and validated
with :func:`attune.security.path_validation._validate_file_path`.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from attune.docs_outbox.routing import OUTBOX_TARGETS, route
from attune.security.path_validation import _validate_file_path

OUTBOX_SUBDIR = "docs-outbox"
SWEPT_SUBDIR = "swept"
DIGEST_NAME = "digest.md"
STALE_AGE_DAYS = 2.0

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
#: Timestamped artifact files only — digest.md and swept/ never match.
_ARTIFACT_GLOB = "[0-9]*.md"
_NAME_RE = re.compile(
    r"^(?P<ts>\d{8}-\d{4})-(?P<kind>[a-z]+)-(?P<slug>[a-z0-9-]+?)(?:-(?P<serial>\d{3}))?\.md$"
)


@dataclass
class Artifact:
    """One parsed outbox artifact."""

    path: Path
    kind: str
    slug: str
    target: str
    created: datetime
    body: str
    serial: int = 1
    issues: list[str] = field(default_factory=list)


@dataclass
class OutboxStatus:
    """Monitoring shape for the ops inbox row (R3)."""

    count: int
    oldest_days: float
    stale: bool


def outbox_dir(attune_home: Path | None = None) -> Path:
    """The outbox directory, created on first use."""
    base = Path(attune_home) if attune_home is not None else Path.home() / ".attune"
    out = base / OUTBOX_SUBDIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def _atomic_write(target: Path, text: str) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.stem}.", suffix=".tmp", dir=str(target.parent)
    )
    try:
        # newline="\n" keeps LF on every platform — Windows text-mode
        # translation would otherwise stamp CRLF into tracked LF markdown
        # (the #1488 class; the repo also runs a mixed-line-ending hook).
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, target)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_artifact(
    kind: str,
    slug: str,
    body: str,
    target: str | None = None,
    attune_home: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Write one artifact to the outbox; return its path.

    Raises:
        ValueError: for merge-now kinds (write those directly and
            ship them in-session), bad slugs, or a missing target on
            kinds without a default.
    """
    if route(kind) != "outbox":
        raise ValueError(
            f"kind {kind!r} routes merge-now — edit the file directly and ship it "
            "in-session (R2); the outbox refuses it by design"
        )
    if not _SLUG_RE.match(slug):
        raise ValueError(f"slug {slug!r} must be lowercase kebab-case ([a-z0-9-])")
    resolved_target = target or OUTBOX_TARGETS[kind]
    if not resolved_target:
        raise ValueError(f"kind {kind!r} has no default target — pass one explicitly")
    if not body.strip():
        raise ValueError("artifact body is empty")

    out_dir = outbox_dir(attune_home)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M")
    if not body.endswith("\n"):
        body += "\n"
    text = f"---\nkind: {kind}\nslug: {slug}\ntarget: {resolved_target}\n---\n\n{body}"

    # Exclusive create, not check-then-act: two processes computing the
    # same name in the same minute must not have one silently overwrite
    # the other (the conflict-free-by-construction promise).
    for serial in range(1, 1000):
        suffix = "" if serial == 1 else f"-{serial:03d}"
        path = out_dir / f"{stamp}-{kind}-{slug}{suffix}.md"
        _validate_file_path(str(path), allowed_dir=str(out_dir))
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return path
    raise ValueError(f"more than 999 artifacts named {stamp}-{kind}-{slug} in one minute")


def _parse(path: Path) -> Artifact:
    """Parse one artifact file; malformed fields become issues."""
    match = _NAME_RE.match(path.name)
    kind = match.group("kind") if match else ""
    slug = match.group("slug") if match else path.stem
    serial = int(match.group("serial") or 1) if match else 1
    # An unparseable name gets the epoch, not "now": a hand-dropped file
    # must still age into the stale warning rather than look forever fresh.
    created = datetime.min
    if match:
        try:
            created = datetime.strptime(match.group("ts"), "%Y%m%d-%H%M")
        except ValueError:
            pass
    front: dict[str, str] = {}
    body = ""
    issues: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as exc:
        return Artifact(path, kind, slug, "", created, "", serial, [f"unreadable: {exc}"])
    if lines and lines[0].strip() == "---":
        end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), None)
        if end is not None:
            for line in lines[1:end]:
                key, _, value = line.partition(":")
                if _:
                    front[key.strip()] = value.strip()
            body = "".join(lines[end + 1 :]).lstrip("\n")
    if not front:
        issues.append("missing frontmatter")
        body = "".join(lines)
    return Artifact(
        path=path,
        kind=front.get("kind", kind),
        slug=front.get("slug", slug),
        target=front.get("target", ""),
        created=created,
        body=body,
        serial=serial,
        issues=issues,
    )


def list_artifacts(attune_home: Path | None = None) -> list[Artifact]:
    """All pending artifacts, oldest first.

    Sorted by (timestamp, serial), NOT by filename: a same-minute
    collision writes ``…-slug-002.md``, which sorts BEFORE ``…-slug.md``
    lexicographically and would apply the two out of order.
    """
    out_dir = outbox_dir(attune_home)
    artifacts = [_parse(p) for p in out_dir.glob(_ARTIFACT_GLOB)]
    artifacts.sort(key=lambda a: (a.created, a.serial, a.path.name))
    return artifacts


def outbox_status(attune_home: Path | None = None) -> OutboxStatus:
    """Pending count + oldest age; ``stale`` fires at 2 days (AC-4)."""
    artifacts = list_artifacts(attune_home)
    if not artifacts:
        return OutboxStatus(count=0, oldest_days=0.0, stale=False)
    now = datetime.now()
    oldest = min(a.created for a in artifacts)
    oldest_days = max((now - oldest).total_seconds() / 86400.0, 0.0)
    return OutboxStatus(
        count=len(artifacts),
        oldest_days=round(oldest_days, 1),
        stale=oldest_days >= STALE_AGE_DAYS,
    )


def archive_swept(artifacts: list[Artifact], attune_home: Path | None = None) -> Path:
    """Move applied artifacts into ``swept/<date>/``; return that dir."""
    out_dir = outbox_dir(attune_home)
    dest = out_dir / SWEPT_SUBDIR / datetime.now().strftime("%Y%m%d")
    dest.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        target = dest / artifact.path.name
        _validate_file_path(str(target), allowed_dir=str(out_dir))
        os.replace(artifact.path, target)
    return dest
