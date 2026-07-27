"""Per-page maintenance contract for regeneration safety.

A documentation page declares how it is maintained in its frontmatter::

    maintenance: auto | manual | hybrid

- ``auto`` (the default, and what an absent field means) — fully
  generated; regen may overwrite freely.
- ``manual`` — human-owned; regen never overwrites it (drift is
  reported, not corrected). The legacy ``status: manual`` field is
  honored as an alias so existing hand-written pages keep working.
- ``hybrid`` — a generated baseline with hand-written regions fenced
  by ``<!-- attune:manual:start -->`` / ``<!-- attune:manual:end -->``.
  Regen rewrites everything OUTSIDE the fences and preserves the text
  INSIDE them.

Why the contract is load-bearing: staleness is detected by content
hash, so a human-edited page always looks "drifted." Without this
contract the regen loop would overwrite curated pages. The merge is
deliberately conservative — matched fence pairs only — and **fails
safe**: if the regenerated content and the on-disk file don't share
the same fence structure, the on-disk hand-written text is never
dropped. The caller keeps the existing file instead.

This mirrors the conservative matched-fence approach of
:func:`attune.authoring.polish._strip_wrapping_fence` (the 0.16/0.17
fence-strip fix).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from attune.authoring.staleness import _read_frontmatter_value

logger = logging.getLogger(__name__)

AUTO = "auto"
MANUAL = "manual"
HYBRID = "hybrid"
VALID_MODES = (AUTO, MANUAL, HYBRID)

#: Markers delimiting a hand-written region inside a ``hybrid`` page.
#: HTML comments so they're invisible in rendered markdown (S7).
MANUAL_FENCE_START = "<!-- attune:manual:start -->"
MANUAL_FENCE_END = "<!-- attune:manual:end -->"

#: One matched fence pair, non-greedy body. Sequential pairs match
#: left-to-right; nested pairs leave the regex count below the raw
#: marker count, which :func:`_fences_balanced` rejects.
_FENCE_RE = re.compile(
    re.escape(MANUAL_FENCE_START) + r"(.*?)" + re.escape(MANUAL_FENCE_END),
    re.DOTALL,
)


class HybridMergeError(Exception):
    """Raised when hybrid regions cannot be merged safely (fail-safe)."""


def read_maintenance_mode(text: str) -> str:
    """Resolve a page's maintenance mode from its content.

    Reads the ``maintenance:`` frontmatter field; falls back to the
    legacy ``status: manual`` alias; defaults to ``auto``. An
    unrecognized value also resolves to ``auto`` — we fail *open* to
    today's behavior rather than accidentally freezing a page.
    """
    value = _read_frontmatter_value(text, "maintenance")
    if value is not None:
        normalized = value.strip().lower()
        return normalized if normalized in VALID_MODES else AUTO
    if _read_frontmatter_value(text, "status") == "manual":
        return MANUAL
    return AUTO


def extract_manual_regions(text: str) -> list[str]:
    """Return the body of each matched manual-fence pair, in order."""
    return _FENCE_RE.findall(text)


def _fences_balanced(text: str) -> bool:
    """True when every start marker pairs with a following end marker.

    Catches unbalanced counts and nested fences: a nested pair makes
    the matched-pair count fall below the raw marker count.
    """
    starts = text.count(MANUAL_FENCE_START)
    ends = text.count(MANUAL_FENCE_END)
    if starts != ends:
        return False
    return len(_FENCE_RE.findall(text)) == starts


def merge_hybrid(*, regenerated: str, existing: str) -> str:
    """Splice the existing file's manual regions into regenerated content.

    The regenerated content must carry the same number of matched
    manual-fence pairs as the existing file (the template emits the
    fence anchors; the human filled them in on disk). Each pair in the
    regenerated content, in order, has its body replaced by the
    corresponding body from the existing file.

    Raises:
        HybridMergeError: if either side has unbalanced/nested fences,
            or the pair counts differ. Dropping hand-written content
            is never acceptable, so the caller must NOT overwrite.
    """
    if not _fences_balanced(existing):
        raise HybridMergeError("existing file has unbalanced manual fences")
    if not _fences_balanced(regenerated):
        raise HybridMergeError("regenerated content has unbalanced manual fences")

    existing_regions = extract_manual_regions(existing)
    regen_pairs = regenerated.count(MANUAL_FENCE_START)
    if regen_pairs != len(existing_regions):
        raise HybridMergeError(
            f"fence-pair count mismatch: regenerated has {regen_pairs}, "
            f"existing has {len(existing_regions)}"
        )

    regions = iter(existing_regions)

    def _replace(_match: re.Match[str]) -> str:
        return MANUAL_FENCE_START + next(regions) + MANUAL_FENCE_END

    return _FENCE_RE.sub(_replace, regenerated)


def _carry_maintenance_field(*, target: str, source: str) -> str:
    """Preserve an explicit ``maintenance:`` field across a regen.

    Regenerated content comes from the template and lacks the
    human-declared ``maintenance:`` field, so copy it over from the
    on-disk file (injected as the first frontmatter line). No-op when
    the source has no explicit field or the target already carries one.
    """
    mode = _read_frontmatter_value(source, "maintenance")
    if mode is None:
        return target
    if _read_frontmatter_value(target, "maintenance") is not None:
        return target
    if not target.startswith("---\n"):
        return target
    return target.replace("---\n", f"---\nmaintenance: {mode}\n", 1)


def resolve_write_content(out_path: Path, regenerated: str) -> str:
    """Apply the maintenance contract, returning the content to write.

    - No existing file, or ``auto`` → return ``regenerated`` (carrying
      over an explicit ``maintenance:`` field if the file declared one).
    - ``hybrid`` → merge the on-disk manual regions into the
      regenerated content. On any unsafe condition, return the existing
      file unchanged (fail safe — never drop hand-written content).

    ``manual`` pages never reach here: they're skipped upstream in
    ``generator.prepare_polish_phase`` (see ``_is_manual``).
    """
    if not out_path.exists():
        return regenerated
    try:
        existing = out_path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - defensive
        logger.debug("Cannot read %s for maintenance contract: %s", out_path, exc)
        return regenerated

    if read_maintenance_mode(existing) == HYBRID:
        try:
            merged = merge_hybrid(regenerated=regenerated, existing=existing)
        except HybridMergeError as exc:
            logger.warning(
                "Hybrid merge skipped for %s (%s); preserving on-disk "
                "manual content, not overwriting",
                out_path,
                exc,
            )
            return existing
        return _carry_maintenance_field(target=merged, source=existing)

    return _carry_maintenance_field(target=regenerated, source=existing)


# ---------------------------------------------------------------------------
# Derived maintenance report (spec task 1.5)
#
# The report is a *view*: it reads each page's frontmatter (the source of
# truth) and enumerates the mode. It never writes — it's for auditing and
# for the one-time triage that flips genuinely-curated pages off ``auto``.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PageMaintenance:
    """One page and its resolved maintenance mode."""

    path: Path
    mode: str


def scan_maintenance(roots: Iterable[Path]) -> list[PageMaintenance]:
    """Resolve the maintenance mode of every ``*.md`` page under ``roots``.

    Each root is walked recursively. Missing roots are skipped. Results
    are sorted by path for stable output. Unreadable files are omitted
    (a read error means we can't classify the page; nothing to report).
    """
    pages: list[PageMaintenance] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for md in sorted(root.rglob("*.md")):
            resolved = md.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                text = md.read_text(encoding="utf-8")
            except OSError as exc:
                logger.debug("Skipping unreadable page %s: %s", md, exc)
                continue
            pages.append(PageMaintenance(path=md, mode=read_maintenance_mode(text)))
    return pages


def format_maintenance_report(
    pages: list[PageMaintenance],
    *,
    base: Path | None = None,
    show_auto: bool = False,
) -> str:
    """Render a human-readable maintenance report grouped by mode.

    By default only the curated modes (``manual``/``hybrid``) are listed
    — those are the pages a reader needs to know are protected. Pass
    ``show_auto=True`` to list ``auto`` pages too. ``base``, when given,
    is stripped from each path for compact display.
    """

    def _display(path: Path) -> str:
        # Forward slashes regardless of OS so the report is portable and
        # stable across platforms (Windows would otherwise emit backslashes).
        if base is not None:
            try:
                return path.relative_to(base).as_posix()
            except ValueError:
                pass
        return path.as_posix()

    counts = {AUTO: 0, MANUAL: 0, HYBRID: 0}
    for page in pages:
        counts[page.mode] = counts.get(page.mode, 0) + 1

    lines = ["## Maintenance report", ""]
    lines.append(
        f"{len(pages)} page(s) — {counts[AUTO]} auto, "
        f"{counts[MANUAL]} manual, {counts[HYBRID]} hybrid"
    )

    listed_modes = [MANUAL, HYBRID] + ([AUTO] if show_auto else [])
    for mode in listed_modes:
        in_mode = [p for p in pages if p.mode == mode]
        if not in_mode:
            continue
        lines += ["", f"### {mode} ({len(in_mode)})"]
        lines += [f"- {_display(p.path)}" for p in in_mode]

    if not show_auto and counts[AUTO]:
        lines += ["", f"({counts[AUTO]} auto page(s) omitted; pass --all to list them)"]

    return "\n".join(lines)
