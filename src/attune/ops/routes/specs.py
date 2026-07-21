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

import logging
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from attune.ops import dismiss_store, pending_writes
from attune.ops.security import require_client_token

# The pure data layer lives in attune.ops.specs_data (framework-free) so
# the base CLI / curator can list specs without importing FastAPI. Re-export
# here for backward compatibility — existing callers (dashboard route, tests)
# still do `from attune.ops.routes.specs import SpecRecord, ...`.
from attune.ops.specs_data import (  # noqa: F401
    _PHASE_FILES,
    _STATUS_LIKE_RE,
    _STATUS_RE,
    SpecPhase,
    SpecRecord,
    _extract_status,
    _list_specs_in_root,
    _newest_md_mtime,
    _resolved_roots,
    _scan_spec_dir,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/specs", tags=["specs"])

# Statuses that count as "completion-like" for dismiss-clear purposes.
# A status PUT to anything OUTSIDE this set clears any dismiss entry for
# the spec — re-completion can then re-surface naturally. See
# docs/specs/ops-specs-completion-candidates/ (Phase 2 dismiss semantics).
_COMPLETE_LIKE_STATUSES: frozenset[str] = frozenset({"complete", "completed", "done"})

# SHA-256 hex strings are 64 chars of [0-9a-f]. Validate body inputs to
# the dismiss endpoint match this shape — guards against arbitrary
# string content landing in the persisted store.
_SNAPSHOT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


# `_PHASE_FILES` and `_STATUS_RE` are imported from attune.ops.specs_data
# (see the re-export import above).

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
                "lifecycle": s.lifecycle,
                "stage": s.stage,
                "next_phase": s.next_phase,
                "next_action": s.next_action,
            }
            for s in specs
        ],
    }


@router.get("/completion-candidates")
async def list_completion_candidates(request: Request) -> dict:
    """Return "Ready to close?" candidates for the Specs page.

    Gated on BOTH ``config.specs_candidates_enabled`` AND
    ``config.allow_run`` — read-only mode hides the section entirely
    (no point surfacing confirm buttons that would 403). When either
    is off, returns ``{"enabled": false, "candidates": []}`` without
    invoking the detector (zero gh-API cost on disabled servers).

    Detector caches results for 5 minutes in-memory per the spec's
    Q2 resolution; repeated calls within that window are cheap.

    See ``docs/specs/ops-specs-completion-candidates/`` for the
    detector design.
    """
    from attune.ops.completion_candidates import detect_candidates

    config = request.app.state.config
    if not getattr(config, "specs_candidates_enabled", False):
        return {"enabled": False, "candidates": []}
    if not getattr(config, "allow_run", False):
        return {"enabled": False, "candidates": []}

    candidates = detect_candidates(config)
    return {
        "enabled": True,
        "candidates": [
            {
                "slug": c.slug,
                "path": c.path,
                "current_status": c.current_status,
                "evidence": c.evidence,
                "snapshot_hash": c.snapshot_hash,
            }
            for c in candidates
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
        # newline="\n" keeps LF on every platform — Windows text-mode
        # translation would otherwise stamp CRLF into tracked LF markdown.
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, target)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: cleanup path — remove the temp file regardless of
        # which write/replace step raised, then re-raise so the caller
        # still sees the original failure.
        Path(tmp).unlink(missing_ok=True)
        raise


class UnsafeStatusRewrite(ValueError):
    """A status flip that would duplicate or destroy an existing line.

    Raised by :func:`_rewrite_status_line` when the file's status line
    is descriptive (chair-ruled prose, shipped-evidence annotations) or
    in a shape the rewriter cannot parse. The route maps this to a 409
    — a status stamp must be additive and idempotent or not happen at
    all (2026-07-19 usage-signals corruption postmortem).
    """


# Leading tokens a flip may safely replace. Anything else — "R6 spend
# alarm shipped …", "requirements chair-ruled per item" — is descriptive
# content, not a status token, and replacing it destroys information.
_FLIPPABLE_TOKENS: frozenset[str] = frozenset(
    {
        "draft",
        "in-review",
        "approved",
        "in-progress",
        "implemented",
        "complete",
        "completed",
        "done",
        "shipped",
        "closed",
        "retired",
        "superseded",
        "parked",
        "paused",
        "blocked",
        "deferred",
        "pending",
        "open",
        "not",  # "not started"
        "active",
        "stale",
        "living",
        "ongoing",
        "resolved",
    }
)

_LEADING_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z-]*")


def _leading_token(value: str) -> str:
    """Lowercased leading word of a status value (hyphens kept).

    Leading check glyphs (``✓`` / ``✅``) are decorators, not the token —
    ``✓ Resolved (2026-05-11)`` reads as ``resolved`` (same treatment as
    ``_state.py``'s ``_leading_verdict``).
    """
    stripped = value.strip().lstrip("*_`✓✅ \t")
    match = _LEADING_TOKEN_RE.match(stripped)
    return match.group(0).lower() if match else ""


def _rewrite_status_line(original: str, status: str) -> str:
    """Return ``original`` with its first **Status** line replaced by ``status``.

    Preserves any trailing annotation after the canonical status token —
    so ``**Status:** approved (2026-05-09) — Phase A`` flipping to
    ``in-review`` becomes ``**Status:** in-review (2026-05-09) — Phase A``,
    not just ``**Status:** in-review``. The annotation is whatever follows
    the first delimiter (em-dash, hyphen-with-spaces, open-paren, or
    comma) in the previous value.

    If NO status-like line exists anywhere, inserts ``**Status:** {status}``
    near the top (after the first ``# `` heading if present). Running the
    same flip twice is byte-idempotent.

    Raises :class:`UnsafeStatusRewrite` instead of writing when the flip
    would lose information (guards from the 2026-07-19 usage-signals
    corruption):

    - the first status-like line is a shape the strict pattern cannot
      parse (e.g. ``**Status: chair-ruled per item**``) — rewriting
      would previously INSERT a duplicate ``**Status:**`` line above it;
    - the existing value's leading word is not a recognized status token
      (``R6 spend alarm shipped …``) — replacing it destroys the record.
    """
    match = _STATUS_RE.search(original)
    status_like = _STATUS_LIKE_RE.search(original)
    if match is None:
        if status_like is not None:
            raise UnsafeStatusRewrite(
                "existing status line is in a shape this endpoint cannot "
                f"safely rewrite: {status_like.group(0).strip()!r} — edit the file directly"
            )
        lines = original.splitlines()
        stamp = f"**Status:** {status}"
        insert_at = 1 if lines and lines[0].startswith("# ") else 0
        block = ([""] if insert_at else []) + [stamp]
        if len(lines) > insert_at and lines[insert_at].strip():
            block.append("")
        lines[insert_at:insert_at] = block
        new_text = "\n".join(lines)
        if not new_text.endswith("\n"):
            new_text += "\n"
        return new_text

    if status_like is not None and status_like.start() < match.start():
        # An earlier, unparseable status-ish line is the document's real
        # header; rewriting the later strict match would corrupt prose.
        raise UnsafeStatusRewrite(
            "first status line is in a shape this endpoint cannot safely "
            f"rewrite: {status_like.group(0).strip()!r} — edit the file directly"
        )

    old_value = match.group(1)
    if _leading_token(old_value) not in _FLIPPABLE_TOKENS:
        raise UnsafeStatusRewrite(
            f"existing status value {old_value!r} is descriptive, not a "
            "status token — flipping it would destroy information; edit the file directly"
        )

    annotation = _extract_status_annotation(old_value)
    new_value = (status + annotation) if annotation else status
    # Splice by span (never re.sub): with re.MULTILINE a pattern-level
    # sub over surrounding whitespace previously swallowed the blank
    # lines around the status line.
    start, end = match.span()
    return f"{original[:start]}**Status:** {new_value}{original[end:]}"


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


def _record_pending_write(
    *,
    target: Path,
    before_text: str,
    after_text: str,
    project_root: Path | str,
    request: Request,
) -> None:
    """Best-effort journal append for a successful spec-status write.

    Honors D5 in docs/specs/dashboard-pending-writes-journal/decisions.md:
    journal failures MUST NOT block the calling write endpoint. Wraps the
    entire body so any defect in the journal layer — including ones that
    bypass ``append_entry``'s internal try/except — surfaces as a WARNING
    log, not a 500 response.
    """
    import hashlib

    try:
        project_root_path = Path(project_root)
        try:
            rel_file_path = target.relative_to(project_root_path).as_posix()
        except ValueError:
            # target lives outside project_root (e.g. spec lives in a
            # sibling repo via --specs-root). Fall back to absolute.
            rel_file_path = target.as_posix()
        before_sha = hashlib.sha256(before_text.encode("utf-8")).hexdigest()
        after_sha = hashlib.sha256(after_text.encode("utf-8")).hexdigest()
        entry = pending_writes.make_entry(
            endpoint="PUT /api/specs/{slug}/{phase}/status",
            action="set_spec_status",
            file_path=rel_file_path,
            project_root=str(project_root_path),
            before_sha256=before_sha,
            after_sha256=after_sha,
        )
        # Allow tests / dev to override the journal path via app.state.
        journal_path = getattr(request.app.state, "pending_writes_journal_path", None)
        pending_writes.append_entry(entry, journal_path=journal_path)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: D5 contract — journal failure must never block the
        # actual write. Log + swallow at the route boundary as defense in
        # depth, even though append_entry catches internally.
        logger = logging.getLogger(__name__)
        logger.warning("pending_writes: journal append failed for %s: %s", target, exc)


@router.put("/{slug}/{phase}/status")
async def update_phase_status(
    slug: str,
    phase: str,
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
    _client: None = Depends(require_client_token),  # noqa: B008
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

    try:
        new_text = _rewrite_status_line(original, status)
    except UnsafeStatusRewrite as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        _atomic_write(target, new_text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"write failed: {exc}") from exc

    # Append a pending-writes journal entry so the edit is durable
    # across sessions even before it's committed to git. Best-effort:
    # journal failures log a WARNING and do not block this endpoint.
    # See docs/specs/dashboard-pending-writes-journal/ for the design.
    _record_pending_write(
        target=target,
        before_text=original,
        after_text=new_text,
        project_root=getattr(config, "project_root", matched_root),
        request=request,
    )

    # On successful flip AWAY from a complete-like status, clear any
    # dismiss entry for this slug. Re-completion can then re-surface
    # the candidate naturally. See docs/specs/ops-specs-completion-
    # candidates/ (Phase 2 dismiss semantics).
    if status.lower() not in _COMPLETE_LIKE_STATUSES:
        try:
            dismiss_store.clear(slug, config)
        except OSError:
            # Best-effort: failing to clear the dismiss doesn't
            # roll back the status write. Logged at WARN by the
            # store's own atomic-write path.
            pass

    return {
        "slug": slug,
        "phase": phase,
        "file": f"{phase}.md",
        "status": status,
        "root": str(matched_root),
        "path": str(target),
    }


@router.post("/{slug}/completion-candidates/dismiss")
async def dismiss_completion_candidate(
    slug: str,
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
    _client: None = Depends(require_client_token),  # noqa: B008
) -> dict[str, Any]:
    """Suppress a completion candidate for the default TTL (14 days).

    Body: ``{"snapshot_hash": "<64-hex-chars>"}``.

    The hash comes from the client (echoed back from the GET response)
    so we can guarantee the dismiss-state aligns with what the user
    actually saw. Race-defends against new signal landing between GET
    and POST — if signal changed, the dismissed snapshot won't match
    the next detector run's snapshot and the candidate re-surfaces.

    Gated on ``config.allow_run`` — read-only mode returns 403, same
    as the existing status-flip endpoint.
    """
    config = request.app.state.config
    if not getattr(config, "allow_run", False):
        raise HTTPException(
            status_code=403,
            detail="server is read-only; dismiss is disabled",
        )

    _validate_slug(slug)

    snapshot_hash = body.get("snapshot_hash")
    if not isinstance(snapshot_hash, str) or not _SNAPSHOT_HASH_RE.match(snapshot_hash):
        raise HTTPException(
            status_code=422,
            detail="body must include `snapshot_hash` (64-char hex string)",
        )

    try:
        dismiss_store.save(slug, snapshot_hash, config)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"dismiss persist failed: {exc}") from exc
    return {"ok": True}
