"""Specs API — read-only endpoints for federated spec listing + drill-in.

Phase 1 of docs/specs/ops-specs-features/. Mirrors attune-gui's
`sidecar/attune_gui/routes/cowork_specs.py` GET endpoints for the
listing + read paths; status flip and other write tools come in
Phase 2.

The endpoints:

    GET /api/specs           — list all specs across configured roots
                               with phase status for each
    GET /api/specs/{slug}    — return content of phase files for one spec

Roots are configured via the `--specs-root` CLI flag on `attune ops`
(defaults to `<project-root>/docs/specs/`). Multiple roots are
supported for federated listing across project boundaries.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

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
