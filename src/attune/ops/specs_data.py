"""Spec listing — framework-free data layer.

The pure spec-discovery logic (dataclasses + filesystem readers) used by
BOTH the ops web route (``attune.ops.routes.specs``) and the base-CLI
curator (``attune.curator.sources.specs``). It lives here, free of any
web-framework import, so importing the spec model never drags FastAPI
into a default ``pip install attune-ai`` (where ``[ops]`` extras —
fastapi/uvicorn — are absent). The route module re-exports these names
for backward compatibility.

See docs/specs/ops-specs-features/ for the endpoint design; this module
is just the data half, split out so the CLI can use it without the web
stack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

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
#
# NB: horizontal whitespace ONLY ([ \t]*, never \s*). With re.MULTILINE,
# a leading/trailing \s* spans newlines, so a re.sub over the match
# silently swallowed the blank lines around the status line — the
# 2026-07-19 usage-signals corruption (blank line after the H1 deleted).
_STATUS_RE = re.compile(
    r"^[ \t]*\*\*Status(?::\*\*|\*\*:)[ \t]*(.+?)[ \t]*$",
    re.MULTILINE,
)

# Third convention seen in the wild (usage-signals requirements.md):
# the whole line bolded with the colon inside — ``**Status: value**``,
# optionally followed by trailing prose. Parsed for listing; the writer
# treats it as descriptive (refuses to rewrite it).
_STATUS_WRAPPED_RE = re.compile(
    r"^[ \t]*\*\*Status:[ \t]*([^*\n]+?)[ \t]*\*\*",
    re.MULTILINE,
)

# Liberal detector for "some kind of status line exists" — any bold /
# plain ``Status:`` label at line start, any case. Used by the writer
# so it NEVER inserts a second status line above a variant it cannot
# parse (the duplicate-``**Status:** approved`` corruption shape).
_STATUS_LIKE_RE = re.compile(
    r"^[ \t]*\**[ \t]*Status\**[ \t]*:",
    re.IGNORECASE | re.MULTILINE,
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
    # ISO-8601 timestamp of the most recently modified *.md file in the
    # spec directory (any kind — `decisions.md`, `_sequencing.md`,
    # `audit.md`, etc.). None if the directory has no .md files at all
    # (which shouldn't happen since _list_specs_in_root requires at
    # least one canonical phase file, but handled defensively).
    last_modified: str | None = None
    # Phases waived by `PHASE-WAIVED: <phase>` chair lines in this
    # spec's decisions.md (see `_scan_waived_phases`). Only consulted
    # by stage derivation for phase files that are ABSENT.
    waived_phases: tuple[str, ...] = ()
    # Lifecycle bucket derived from `phases` + `last_modified` via
    # `attune.ops.spec_lifecycle.derive_lifecycle`. Computed in
    # `__post_init__` so callers don't need to coordinate. `init=False`
    # keeps the constructor signature backward-compatible with the many
    # `SpecRecord(slug=..., phases=..., last_modified=...)` test fixtures.
    # One of: "paused", "parked", "complete", "stale", "draft",
    # "approved-not-shipped", "active". See
    # [docs/specs/ops-specs-page-refinement/decisions.md](../../../docs/specs/ops-specs-page-refinement/decisions.md).
    lifecycle: str = field(init=False, default="")
    # Pipeline stage + next transition (spec-lifecycle-gates UI phase):
    # derived from the phase statuses via `derive_stage`, same
    # single-source discipline as `lifecycle`. `next_phase_status` is
    # the current status string of the phase the next action targets,
    # threaded so the page's status editor can prefill it.
    stage: str = field(init=False, default="")
    next_phase: str | None = field(init=False, default=None)
    next_action: str = field(init=False, default="")
    next_phase_status: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        # Lazy import to avoid any chance of an import cycle between
        # routes/specs.py and spec_lifecycle.py (defensive; no cycle
        # exists today since spec_lifecycle uses a structural Protocol).
        from attune.ops.spec_lifecycle import derive_lifecycle, derive_stage

        # Frozen dataclass — use object.__setattr__ to set the field.
        object.__setattr__(self, "lifecycle", derive_lifecycle(self))
        info = derive_stage(self)
        object.__setattr__(self, "stage", info.stage)
        object.__setattr__(self, "next_phase", info.next_phase)
        object.__setattr__(self, "next_action", info.next_action)
        status = None
        if info.next_phase is not None:
            for p in self.phases:
                if p.name == info.next_phase:
                    status = p.status
                    break
        object.__setattr__(self, "next_phase_status", status)


def _extract_status(text: str) -> str | None:
    """Pull the value after `**Status**:` from a markdown file.

    Falls back to the fully-bolded ``**Status: value**`` convention so
    specs using that shape list with their real status instead of None.
    """
    match = _STATUS_RE.search(text) or _STATUS_WRAPPED_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


# Chair waiver line for a phase, committed in decisions.md — the same
# chair-line-in-decisions pattern as `P4-ROTATION: armed`. Example:
# `PHASE-WAIVED: design (2026-07-20 — thread q-..., see entry below)`.
# Only the phase token is machine-read; the parenthetical is provenance
# for humans. A waiver affects stage derivation ONLY for phases whose
# file is absent — an existing file's own status always governs.
_PHASE_WAIVED_RE = re.compile(r"^PHASE-WAIVED:\s*([a-z]+)", re.MULTILINE)


def _scan_waived_phases(decisions_text: str | None) -> tuple[str, ...]:
    """Return phases waived by chair lines in a spec's decisions.md text."""
    if not decisions_text:
        return ()
    valid = {p.removesuffix(".md") for p in _PHASE_FILES}
    return tuple(m for m in _PHASE_WAIVED_RE.findall(decisions_text) if m in valid)


def _scan_spec_dir(spec_dir: Path) -> tuple[list[SpecPhase], str | None]:
    """List the phase files in one spec directory with their statuses.

    Returns the phases plus the decisions.md text (None if absent or
    unreadable) so callers can derive waivers without a second read.
    """
    phases: list[SpecPhase] = []
    decisions_text: str | None = None
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
        if phase_file == "decisions.md":
            decisions_text = text
        phases.append(
            SpecPhase(name=name, file=phase_file, exists=True, status=_extract_status(text))
        )
    return phases, decisions_text


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
        phases, decisions_text = _scan_spec_dir(child)
        records.append(
            SpecRecord(
                slug=child.name,
                root=str(root),
                path=str(child),
                phases=phases,
                last_modified=_newest_md_mtime(child),
                waived_phases=_scan_waived_phases(decisions_text),
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
