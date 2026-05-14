"""Specs API — endpoints for federated spec listing, drill-in, and status flip.

Phases 1 + 2 of docs/specs/ops-specs-features/. Mirrors attune-gui's
`sidecar/attune_gui/routes/cowork_specs.py` GET endpoints (Phase 1)
and the PUT status-flip endpoint (Phase 2).

The endpoints:

    GET /api/specs                          — list specs across roots
    GET /api/specs/{slug}                   — read phase-file contents
    PUT /api/specs/{slug}/{phase}/status    — rewrite **Status** line

Roots are configured via the `--specs-root` CLI flag on `attune ops`
(defaults to `<project-root>/docs/specs/`). Multiple roots are
supported for federated listing across project boundaries.

The status-flip endpoint is gated by ``config.allow_run`` — when the
server runs with ``--read-only``, mutations are rejected with 403.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

router = APIRouter(prefix="/api/specs", tags=["specs"])


# Phase files we recognize. Match attune-gui's convention; decisions.md is
# attune-ai's additional convention and is included for parity with current
# specs (probe-c, ops-specs-features, etc. all use decisions.md as the
# primary doc).
_PHASE_FILES: tuple[str, ...] = (
    "decisions.md",
    "requirements.md",
    "design.md",
    "tasks.md",
)

# Status line pattern — accepts both Markdown bolding conventions:
#   **Status:** value   (colon inside the bolding — attune-ai convention)
#   **Status**: value   (colon outside — attune-gui convention)
# Captures the value, stripping trailing whitespace.
_STATUS_RE = re.compile(
    r"^\s*\*\*Status(?::\*\*|\*\*:)\s*(.+?)\s*$",
    re.MULTILINE,
)

# Phase file names (without `.md`) accepted by the status-flip endpoint.
# Derived from `_PHASE_FILES` so the two stay in lockstep.
_VALID_PHASES: tuple[str, ...] = tuple(p.removesuffix(".md") for p in _PHASE_FILES)

# Statuses we accept on a PUT — mirrors attune-gui's set so callers can use
# the same vocabulary across both dashboards. "completed" and "done" are
# accepted aliases for "complete".
_VALID_STATUSES: tuple[str, ...] = (
    "draft",
    "in-review",
    "approved",
    "complete",
    "completed",
    "done",
)

# Slug rule: lowercase letters/digits/dashes, must start with letter/digit,
# max 63 chars. Matches attune-gui's `_SLUG_RE` so the two endpoints agree.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


@dataclass(frozen=True)
class SpecPhase:
    """One phase file's status snapshot."""

    name: str  # "decisions" / "requirements" / "design" / "tasks"
    file: str  # e.g. "decisions.md"
    exists: bool
    status: str | None  # parsed from `**Status**:` line, or None if absent


@dataclass(frozen=True)
class SpecRecord:
    """One spec's summary — directory + status of each phase file present."""

    slug: str  # directory name
    root: str  # absolute path of the containing root
    path: str  # absolute path of the spec directory
    phases: list[SpecPhase]
    # ISO-8601 timestamp of the most recently modified *.md file in the
    # spec directory (any kind — `decisions.md`, `_sequencing.md`,
    # `audit.md`, etc.). None if the directory has no .md files at all
    # (which shouldn't happen since _list_specs_in_root requires at
    # least one canonical phase file, but handled defensively).
    last_modified: str | None = None


def _extract_status(text: str) -> str | None:
    """Pull the value after `**Status**:` from a markdown file."""
    match = _STATUS_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def _scan_spec_dir(spec_dir: Path) -> list[SpecPhase]:
    """List the phase files in one spec directory with their statuses."""
    phases: list[SpecPhase] = []
    for phase_file in _PHASE_FILES:
        file_path = spec_dir / phase_file
        name = phase_file.removesuffix(".md")
        if not file_path.is_file():
            phases.append(SpecPhase(name=name, file=phase_file, exists=False, status=None))
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            # INTENTIONAL: an unreadable phase file is reported as
            # existing-but-statusless rather than failing the whole listing.
            phases.append(SpecPhase(name=name, file=phase_file, exists=True, status=None))
            continue
        phases.append(
            SpecPhase(name=name, file=phase_file, exists=True, status=_extract_status(text))
        )
    return phases


def _newest_md_mtime(spec_dir: Path) -> str | None:
    """Return the newest mtime across all `.md` files in the spec dir,
    formatted as a UTC ISO-8601 string. Catches edits to canonical phase
    files AND auxiliary content (`_sequencing.md`, `audit.md`, etc.)."""
    from datetime import datetime, timezone

    newest: float | None = None
    try:
        for md in spec_dir.glob("*.md"):
            try:
                mt = md.stat().st_mtime
            except OSError:
                continue
            if newest is None or mt > newest:
                newest = mt
    except OSError:
        return None
    if newest is None:
        return None
    return datetime.fromtimestamp(newest, tz=timezone.utc).isoformat()


def _list_specs_in_root(root: Path) -> list[SpecRecord]:
    """Find all spec directories under one root, with phase statuses."""
    if not root.is_dir():
        return []
    records: list[SpecRecord] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        # A spec dir must contain at least ONE of the recognized phase files;
        # otherwise it's just an unrelated subdirectory.
        has_phase = any((child / phase).is_file() for phase in _PHASE_FILES)
        if not has_phase:
            continue
        records.append(
            SpecRecord(
                slug=child.name,
                root=str(root),
                path=str(child),
                phases=_scan_spec_dir(child),
                last_modified=_newest_md_mtime(child),
            )
        )
    return records


def _resolved_roots(config) -> list[Path]:
    """Resolve the spec roots from config, defaulting to
    `<project-root>/docs/specs/` if none are configured."""
    roots = getattr(config, "specs_roots", ()) or ()
    if not roots:
        roots = (config.project_root / "docs" / "specs",)
    return [Path(r).expanduser().resolve() for r in roots]


@router.get("")
async def list_specs(request: Request) -> dict:
    """Federated listing across all configured spec roots.

    Naming collisions: if the same slug appears under multiple roots, both
    are returned; the client can decide what to do. We don't dedupe at the
    server level — preserving information beats hiding it.
    """
    config = request.app.state.config
    roots = _resolved_roots(config)
    specs: list[SpecRecord] = []
    for root in roots:
        specs.extend(_list_specs_in_root(root))
    return {
        "roots": [str(r) for r in roots],
        "specs": [
            {
                "slug": s.slug,
                "root": s.root,
                "path": s.path,
                "phases": [asdict(p) for p in s.phases],
            }
            for s in specs
        ],
    }


@router.get("/{slug}")
async def get_spec(slug: str, request: Request) -> dict:
    """Return phase-file contents for one spec.

    Looks up the slug across all configured roots and returns the first
    match. If the same slug exists in multiple roots, prefers the root that
    appears earliest in the configured list (which is also the root that
    listed first in `GET /api/specs`).
    """
    # Slug-safety: don't allow path traversal. Slugs are directory names,
    # not paths.
    if "/" in slug or ".." in slug or "\\" in slug:
        raise HTTPException(status_code=400, detail="invalid slug")

    config = request.app.state.config
    roots = _resolved_roots(config)
    for root in roots:
        spec_dir = root / slug
        if spec_dir.is_dir():
            phases = _scan_spec_dir(spec_dir)
            contents: dict[str, str | None] = {}
            for phase in phases:
                if not phase.exists:
                    contents[phase.name] = None
                    continue
                file_path = spec_dir / phase.file
                try:
                    contents[phase.name] = file_path.read_text(encoding="utf-8")
                except OSError:
                    contents[phase.name] = None
            return {
                "slug": slug,
                "root": str(root),
                "path": str(spec_dir),
                "phases": [asdict(p) for p in phases],
                "contents": contents,
            }
    raise HTTPException(status_code=404, detail=f"spec '{slug}' not found in any configured root")


# ---------------------------------------------------------------------------
# Phase 2 — status-flip write API
# ---------------------------------------------------------------------------


def _validate_slug(slug: str) -> None:
    """Reject slugs that fail the directory-name shape check."""
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                "invalid slug: must be lowercase letters/digits/dashes, "
                "start with a letter or digit, max 63 chars"
            ),
        )


def _validate_phase_name(phase: str) -> None:
    """Reject phase names not in the recognized set."""
    if phase not in _VALID_PHASES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown phase: {phase!r}. valid: {', '.join(_VALID_PHASES)}",
        )


def _validate_status_value(status: str) -> None:
    """Reject status values outside the accepted vocabulary."""
    if status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid status: {status!r}. valid: {', '.join(_VALID_STATUSES)}",
        )


def _atomic_write(target: Path, text: str) -> None:
    """Write ``text`` to ``target`` atomically via tempfile + os.replace.

    Mirrors attune-gui's `_fs.atomic_write` so a concurrent reader either
    sees the old file or the new one, never a partial write. Cleans up the
    temp file if anything raises before the rename lands.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, target)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: cleanup path — remove the temp file regardless of
        # which write/replace step raised, then re-raise so the caller
        # still sees the original failure.
        Path(tmp).unlink(missing_ok=True)
        raise


def _rewrite_status_line(original: str, status: str) -> str:
    """Return ``original`` with its first **Status** line replaced by ``status``.

    Preserves any trailing annotation after the canonical status token —
    so ``**Status:** approved (2026-05-09) — Phase A`` flipping to
    ``in-review`` becomes ``**Status:** in-review (2026-05-09) — Phase A``,
    not just ``**Status:** in-review``. The annotation is whatever follows
    the first delimiter (em-dash, hyphen-with-spaces, open-paren, or
    comma) in the previous value.

    If no recognized status line exists, inserts ``**Status:** {status}``
    near the top (after the first ``# `` heading if present).
    """
    match = _STATUS_RE.search(original)
    if match:
        old_value = match.group(1)
        annotation = _extract_status_annotation(old_value)
        new_value = (status + annotation) if annotation else status
        # Use a lambda for sub() so the replacement is treated as a
        # literal — `\g<...>` / numeric backrefs in annotations can't
        # accidentally trigger expansion.
        return _STATUS_RE.sub(lambda _m: f"**Status:** {new_value}", original, count=1)
    lines = original.splitlines()
    insert_at = 1 if lines and lines[0].startswith("# ") else 0
    lines.insert(insert_at, f"\n**Status:** {status}\n")
    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    return new_text


def _extract_status_annotation(old_value: str) -> str:
    """Return the trailing annotation portion of a status value.

    The annotation is everything from the first delimiter onward,
    preserving leading whitespace. Returns ``""`` if no delimiter found
    or the annotation contains only whitespace.

    Examples:
        "draft" -> ""
        "approved (2026-05-09)" -> " (2026-05-09)"
        "complete (2026-05-10) — Phase A" -> " (2026-05-10) — Phase A"
        "in-review — needs review" -> " — needs review"
        "approved, see notes" -> ", see notes"
    """
    # Scan ALL delimiters and pick the EARLIEST match — otherwise
    # "approved (2026) — Phase A" would split on " — " and lose " (2026)"
    # from the annotation. The em-dash-vs-hyphen tie-break only matters
    # if they're at the same position, which doesn't happen in practice.
    earliest = -1
    for delim in (" — ", " (", " - ", ", "):
        idx = old_value.find(delim)
        if idx >= 0 and (earliest < 0 or idx < earliest):
            earliest = idx
    if earliest < 0:
        return ""
    annotation = old_value[earliest:]
    return annotation if annotation.strip() else ""


@router.put("/{slug}/{phase}/status")
async def update_phase_status(
    slug: str,
    phase: str,
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
) -> dict[str, Any]:
    """Rewrite the ``**Status**`` line in the named phase file.

    Body: ``{"status": "<one of _VALID_STATUSES>"}``.

    Gated on ``config.allow_run`` — when the server runs with
    ``--read-only``, this returns 403.
    """
    config = request.app.state.config
    if not getattr(config, "allow_run", False):
        raise HTTPException(
            status_code=403,
            detail="server is read-only; status flip is disabled",
        )

    _validate_slug(slug)
    _validate_phase_name(phase)

    status = body.get("status")
    if not isinstance(status, str):
        raise HTTPException(
            status_code=422,
            detail="body must include `status` (string)",
        )
    _validate_status_value(status)

    roots = _resolved_roots(config)
    target: Path | None = None
    matched_root: Path | None = None
    for root in roots:
        candidate = root / slug / f"{phase}.md"
        if candidate.is_file():
            target = candidate
            matched_root = root
            break
    if target is None or matched_root is None:
        raise HTTPException(
            status_code=404,
            detail=f"{phase}.md not found for spec '{slug}' in any configured root",
        )

    try:
        original = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"read failed: {exc}") from exc

    new_text = _rewrite_status_line(original, status)

    try:
        _atomic_write(target, new_text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"write failed: {exc}") from exc

    return {
        "slug": slug,
        "phase": phase,
        "file": f"{phase}.md",
        "status": status,
        "root": str(matched_root),
        "path": str(target),
    }
