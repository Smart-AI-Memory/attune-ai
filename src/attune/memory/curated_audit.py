"""Advisory staleness audit for curated markdown memory corpora.

Curated memories are human-authored markdown files with YAML frontmatter,
indexed by a sibling ``MEMORY.md``. Unlike the raw session stash they carry
no TTL and no recency decay, so nothing tells a reading session how long it
has been since anyone confirmed a claim is still true.

This module supplies that signal. It is **advisory by construction** — every
function here is a pure read. Nothing in this module writes to a corpus,
deletes a memory, or decides whether a claim is true.

Two rules from ``docs/specs/memory-status-integrity/decisions.md`` are load
bearing here, and both are easy to violate by accident:

D1 — **Label, never suppress by age.** Age is *anti-correlated* with
wrongness in a real corpus: the oldest memories are settled ``feedback`` and
``user`` rules, while the memories that actually rot assert mutable state.
Nothing here may filter a memory out of a result on the basis of age.

D3 — **No corpus path is hardcoded.** Callers supply roots, which is what
lets one implementation serve both the attune-shipped store and a personal
corpus living outside every repo.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

#: Frontmatter keys the curated schema permits at the top level.
ALLOWED_TOP_LEVEL_KEYS = frozenset({"name", "description", "metadata"})

#: Keys the curated schema permits inside ``metadata:``.
ALLOWED_METADATA_KEYS = frozenset({"type"})

#: Extra keys under ``metadata:`` are provenance injected by the Claude Code
#: auto-memory graph (``node_type``, ``originSessionId``, …), not drift.
#:
#: The canonical linter (``~/.claude/hooks/memory_lint.py``) tolerates them
#: whenever a valid ``metadata.type`` is present, and flags ``node_type`` only
#: when it is used as a *substitute* for ``metadata.type`` — the original
#: schema drift the rule was written to catch. This module matches that
#: behaviour deliberately: reporting provenance as a violation would put the
#: sweep in permanent disagreement with the enforcement mechanism and train
#: readers to ignore it.
TOLERATE_METADATA_PROVENANCE = True

#: The canonical linter's ALLOWED_TYPES (``~/.claude/hooks/memory_lint.py``),
#: mirrored exactly. This deliberately does NOT include ``lesson`` — the
#: linter maps ``lesson_*`` stems to ``feedback`` and flags ``type: lesson``
#: as a violation, so the sweep must too (decision D4: the enforcement code
#: is the authority; an earlier draft of this set included ``lesson`` and put
#: the two implementations in disagreement).
LINTER_ALLOWED_TYPES = frozenset({"user", "feedback", "project", "reference"})

#: Backward-compatible alias for the previous name. The old set wrongly
#: included ``lesson``; keep the alias pointing at the corrected set so any
#: external caller inherits the fix rather than the bug.
KNOWN_TYPES = LINTER_ALLOWED_TYPES

#: How fast a claim of each type goes stale, per design.md § ranking model.
#:
#: These scale age into risk. ``project`` memories assert mutable state (CI
#: status, PR state, in-flight work) and rot fastest; ``feedback`` and
#: ``user`` encode settled process rules and profile, and barely rot at all.
#: Ranking by raw age instead would march a reviewer through correct process
#: rules before reaching the one stale CI claim — the same sign error D1
#: rejects for suppression.
VOLATILITY_BY_TYPE: dict[str, float] = {
    "project": 1.00,
    "reference": 0.60,
    # ``lesson`` is NOT a valid metadata.type (see LINTER_ALLOWED_TYPES) but
    # is kept here so a file carrying it still ranks sensibly while its
    # invalid type is reported. Ranking tolerance ≠ schema tolerance.
    "lesson": 0.40,
    "feedback": 0.15,
    "user": 0.10,
}

#: Volatility for a memory whose type is missing or unrecognised. Deliberately
#: high — an unclassifiable memory should surface for review, not hide.
DEFAULT_VOLATILITY = 0.75

#: The index file that must carry a pointer for every memory.
INDEX_FILENAME = "MEMORY.md"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_INDEX_LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")


@dataclass(frozen=True)
class CuratedMemory:
    """One curated memory file, parsed but not judged."""

    path: Path
    name: str | None
    description: str | None
    mem_type: str | None
    verified: date | None
    mtime_date: date
    unknown_keys: tuple[str, ...]
    links: tuple[str, ...]
    deferred_links: tuple[str, ...]

    @property
    def stem(self) -> str:
        """Filename without the ``.md`` suffix — the corpus-wide identity."""
        return self.path.stem


@dataclass(frozen=True)
class AuditReport:
    """The result of an advisory sweep. Purely descriptive."""

    ranked: tuple[tuple[CuratedMemory, float], ...] = ()
    schema_violations: tuple[tuple[Path, tuple[str, ...]], ...] = ()
    invalid_types: tuple[tuple[Path, str], ...] = ()
    name_mismatches: tuple[Path, ...] = ()
    broken_links: tuple[tuple[Path, str], ...] = ()
    orphans: tuple[Path, ...] = ()
    dangling_pointers: tuple[tuple[Path, str], ...] = ()
    age_basis: str = "mtime"
    scanned: int = 0
    roots: tuple[Path, ...] = field(default=())

    @property
    def clean(self) -> bool:
        """True when no integrity problem was found (staleness aside)."""
        return not (
            self.schema_violations
            or self.invalid_types
            or self.name_mismatches
            or self.broken_links
            or self.orphans
            or self.dangling_pointers
        )


def _parse_frontmatter(text: str) -> tuple[dict[str, str], list[str], str]:
    """Parse the fixed two-level curated schema without a YAML dependency.

    The curated schema is shallow and closed: three permitted top-level keys,
    one permitted key inside ``metadata``. Parsing it directly keeps this
    module importable anywhere and avoids depending on a YAML library that
    the consuming layer may not install.

    Args:
        text: Full file contents.

    Returns:
        ``(fields, unknown_keys, body)``. ``fields`` maps a normalised key
        (``name``, ``description``, ``metadata.type``, ``verified``) to its
        raw string value. ``unknown_keys`` lists keys the schema forbids,
        nested ones prefixed ``metadata.``.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, [], text

    block = match.group(1)
    body = text[match.end() :]
    fields: dict[str, str] = {}
    unknown: list[str] = []
    in_metadata = False
    # Top-level key whose value was a YAML block-scalar indicator (``>``,
    # ``|`` and their chomping variants) — its indented continuation lines
    # are VALUE content, not keys.
    block_key: str | None = None
    block_parts: list[str] = []

    for raw_line in block.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indented = raw_line[:1].isspace()
        line = raw_line.strip()

        if indented and not in_metadata:
            # P2 gate (D6#1): indented continuation lines outside
            # ``metadata:`` — folded/literal scalars, wrapped values — must
            # never parse as top-level keys. The canonical linter counts
            # only non-indented keys; before this alignment a continuation
            # line containing ``:`` false-positived as an unknown key on
            # exactly the multi-line files the loop depends on.
            if block_key is not None:
                block_parts.append(line)
            continue

        if block_key is not None:  # a non-indented line ends the scalar
            if block_parts:
                fields[block_key] = " ".join(block_parts)
            block_key, block_parts = None, []

        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("\"'")

        if indented:  # only reachable inside ``metadata:``
            _record_metadata_key(key, value, fields, unknown)
            continue

        in_metadata = key == "metadata"
        if key == "metadata":
            continue
        if _record_top_level_key(key, value, fields, unknown):
            block_key, block_parts = key, []

    if block_key is not None and block_parts:
        fields[block_key] = " ".join(block_parts)

    return fields, unknown, body


def _record_metadata_key(key: str, value: str, fields: dict[str, str], unknown: list[str]) -> None:
    """Record one ``metadata:`` child, flagging keys the schema forbids."""
    if key in ALLOWED_METADATA_KEYS:
        fields[f"metadata.{key}"] = value
    else:
        unknown.append(f"metadata.{key}")


_BLOCK_SCALAR_INDICATORS = frozenset({">", "|", ">-", "|-", ">+", "|+"})


def _record_top_level_key(key: str, value: str, fields: dict[str, str], unknown: list[str]) -> bool:
    """Record one top-level key. True when its value opens a block scalar.

    ``verified:`` is the P2 field. Tolerated (never flagged) before P2
    ships so an early adopter's file does not read as a violation.
    """
    if key == "verified":
        fields["verified"] = value
    elif key in ALLOWED_TOP_LEVEL_KEYS:
        fields[key] = value
    else:
        unknown.append(key)
        return False
    return value in _BLOCK_SCALAR_INDICATORS


def _parse_date(value: str | None) -> date | None:
    """Parse an ISO-8601 date, tolerating a full timestamp. None when unusable."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        logger.debug("unparseable verified date: %r", value)
        return None


def load_memory(path: Path) -> CuratedMemory:
    """Parse a single curated memory file.

    Never raises on malformed content — a file that cannot be parsed still
    yields a ``CuratedMemory`` with empty fields, because a sweep that dies
    on one bad file reports nothing about the other 265.

    Args:
        path: Path to a ``.md`` memory file.

    Returns:
        The parsed memory.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("unreadable memory %s: %s", path, exc)
        text = ""

    fields, unknown, body = _parse_frontmatter(text)
    # Provenance keys under ``metadata:`` are legitimate when the memory
    # carries a valid type — see TOLERATE_METADATA_PROVENANCE. When the type
    # is missing or unrecognised they stay reported, because that is the
    # substitute-for-type drift the canonical linter exists to catch.
    if TOLERATE_METADATA_PROVENANCE and fields.get("metadata.type") in LINTER_ALLOWED_TYPES:
        unknown = [key for key in unknown if not key.startswith("metadata.")]

    all_links = _LINK_RE.findall(body)
    try:
        # Local date, deliberately — it is compared against ``date.today()``,
        # which is also local. Reading mtime as UTC while comparing to a local
        # today put every non-UTC user off by a day (caught by the clock-tz
        # matrix in America/Anchorage: 60 where 61 was correct).
        mtime = datetime.fromtimestamp(path.stat().st_mtime).date()
    except OSError:
        mtime = date.today()

    return CuratedMemory(
        path=path,
        name=fields.get("name"),
        description=fields.get("description"),
        mem_type=fields.get("metadata.type"),
        verified=_parse_date(fields.get("verified")),
        mtime_date=mtime,
        unknown_keys=tuple(unknown),
        links=tuple(link for link in all_links if not link.startswith("?")),
        deferred_links=tuple(link[1:] for link in all_links if link.startswith("?")),
    )


def scan_corpus(roots: Iterable[Path]) -> list[CuratedMemory]:
    """Load every curated memory under the given roots.

    Args:
        roots: Directories to scan, recursively. Missing roots are skipped.

    Returns:
        Parsed memories, sorted by path. The index file itself is excluded.
    """
    memories: list[CuratedMemory] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            logger.debug("skipping missing corpus root: %s", root)
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name == INDEX_FILENAME or path in seen:
                continue
            seen.add(path)
            memories.append(load_memory(path))
    return memories


def unverified_age_days(mem: CuratedMemory, today: date | None = None) -> int:
    """Days since a human last confirmed this memory is still true.

    P2 will supply a real ``verified:`` date. Until then this falls back to
    file mtime, which is a **known-bad proxy**: it records the last edit, so a
    bulk reformat reads as a fresh confirmation. The fallback ships anyway
    because it errs in the safe direction — mtime makes memories look
    *fresher* than they are, so the signal under-warns rather than
    over-warns.

    Args:
        mem: The memory to age.
        today: Reference date; defaults to the current date. Injectable so
            tests need no clock control.

    Returns:
        Whole days, floored at zero.
    """
    reference = today or date.today()
    # P2: prefer mem.verified once the schema carries it.
    basis = mem.verified or mem.mtime_date
    return max(0, (reference - basis).days)


def volatility(mem_type: str | None) -> float:
    """Return how fast this memory type goes stale. See VOLATILITY_BY_TYPE."""
    if mem_type is None:
        return DEFAULT_VOLATILITY
    return VOLATILITY_BY_TYPE.get(mem_type, DEFAULT_VOLATILITY)


def risk_score(mem: CuratedMemory, today: date | None = None) -> float:
    """Rank a memory's need for human review: age scaled by type volatility.

    This orders *review attention* only. Per D1 it must never be used to drop
    a memory from a recall result — a high score means "ask a human", not
    "hide it".

    Args:
        mem: The memory to score.
        today: Reference date; defaults to the current date.

    Returns:
        A non-negative score. Higher means review sooner.
    """
    return unverified_age_days(mem, today) * volatility(mem.mem_type)


def format_age_annotation(days: int) -> str:
    """Render the reader-facing staleness label.

    A pure function of days so plain-text and HTML surfaces emit the same
    signal. This annotation is the entire mitigation for D1's label-only
    posture, which is why it is mandatory on every recall surface rather
    than optional decoration.

    Args:
        days: Days unverified, from :func:`unverified_age_days`.

    Returns:
        A short parenthetical, e.g. ``⟨61 days unverified⟩``.
    """
    if days <= 0:
        return "⟨verified today⟩"
    if days == 1:
        return "⟨1 day unverified⟩"
    return f"⟨{days} days unverified⟩"


def annotate(text: str, mem: CuratedMemory, today: date | None = None) -> str:
    """Append the staleness label to a rendered memory line.

    Args:
        text: The already-rendered memory text.
        mem: The memory it came from.
        today: Reference date; defaults to the current date.

    Returns:
        ``text`` with the annotation appended.
    """
    return f"{text}  {format_age_annotation(unverified_age_days(mem, today))}"


def _index_texts(roots: Iterable[Path]) -> dict[Path, str]:
    """Map each directory containing an index to that index's raw text."""
    texts: dict[Path, str] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for index in sorted(root.rglob(INDEX_FILENAME)):
            try:
                texts[index.parent] = index.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("unreadable index %s: %s", index, exc)
    return texts


def _is_pointed_at(stem: str, index_text: str) -> bool:
    """True when the index mentions this memory in any form.

    The canonical linter accepts a bare ``stem.md`` mention as well as a
    markdown link, because some indexes are tables rather than link lists.
    Matching only the link form reported 21 false orphans against the real
    corpus on 2026-08-07 — the requirement is "indexed", not a syntax.
    """
    return f"{stem}.md" in index_text


def _pointer_integrity(
    memories: Sequence[CuratedMemory],
    known_stems: set[str],
    roots: tuple[Path, ...],
) -> tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]:
    """Cross-check memories against their ``MEMORY.md`` indexes, both ways.

    Returns ``(orphans, dangling)``: files with no index pointer, and index
    pointers with no file. When no roots are given, pointer integrity is
    skipped (both empty) rather than treated as failing.

    A corpus with no ``MEMORY.md`` carries no pointer requirement — the
    canonical linter self-skips it, and attune's own curated store is exactly
    that shape — so its files are never reported as orphans.
    """
    if not roots:
        return (), ()
    index_texts = _index_texts(roots)
    orphans = tuple(
        mem.path
        for mem in memories
        if mem.path.parent in index_texts
        and not _is_pointed_at(mem.stem, index_texts[mem.path.parent])
    )
    dangling = tuple(
        (directory / INDEX_FILENAME, stem)
        for directory, text in index_texts.items()
        for stem in sorted({Path(t).stem for t in _INDEX_LINK_RE.findall(text)} - known_stems)
    )
    return orphans, dangling


def _content_integrity(
    memories: Sequence[CuratedMemory],
    known_stems: set[str],
) -> tuple[
    tuple[tuple[Path, tuple[str, ...]], ...],
    tuple[tuple[Path, str], ...],
    tuple[Path, ...],
    tuple[tuple[Path, str], ...],
]:
    """Per-file schema, type, name, and link checks (no cross-file indexes).

    Returns ``(schema_violations, invalid_types, name_mismatches,
    broken_links)``. A PRESENT-but-unrecognised ``metadata.type`` is definite
    drift — exactly what the canonical linter flags. A MISSING type is
    deliberately not flagged: sweep roots may include corpora with a different
    file format (attune's personal topic/kind store) where the linter claims
    no jurisdiction. Value-drift is unambiguous; absence is not.
    """
    schema_violations = tuple((mem.path, mem.unknown_keys) for mem in memories if mem.unknown_keys)
    invalid_types = tuple(
        (mem.path, mem.mem_type)
        for mem in memories
        if mem.mem_type is not None and mem.mem_type not in LINTER_ALLOWED_TYPES
    )
    # ``name:`` must equal the filename stem — a mismatch breaks every
    # [[link]] that targets it, silently.
    name_mismatches = tuple(
        mem.path for mem in memories if mem.name is not None and mem.name != mem.stem
    )
    broken_links = tuple(
        (mem.path, link) for mem in memories for link in mem.links if link not in known_stems
    )
    return schema_violations, invalid_types, name_mismatches, broken_links


def audit(
    memories: Sequence[CuratedMemory],
    roots: Iterable[Path] = (),
    today: date | None = None,
) -> AuditReport:
    """Produce an advisory report over already-scanned memories.

    Checks corpus integrity (schema, link resolution, index pointers in both
    directions) and ranks every memory by review priority. Writes nothing.

    Args:
        memories: Parsed memories, typically from :func:`scan_corpus`.
        roots: Corpus roots, used to locate ``MEMORY.md`` index files. When
            omitted, pointer integrity is skipped rather than failed.
        today: Reference date; defaults to the current date.

    Returns:
        The report. ``ranked`` is ordered by descending risk.
    """
    roots = tuple(roots)
    known_stems = {mem.stem for mem in memories}

    schema_violations, invalid_types, name_mismatches, broken_links = _content_integrity(
        memories, known_stems
    )
    orphans, dangling = _pointer_integrity(memories, known_stems, roots)

    ranked = tuple(
        sorted(
            ((mem, risk_score(mem, today)) for mem in memories),
            key=lambda pair: (-pair[1], str(pair[0].path)),
        )
    )
    uses_verified = any(mem.verified is not None for mem in memories)

    return AuditReport(
        ranked=ranked,
        schema_violations=schema_violations,
        invalid_types=invalid_types,
        name_mismatches=name_mismatches,
        broken_links=broken_links,
        orphans=orphans,
        dangling_pointers=dangling,
        age_basis="verified" if uses_verified else "mtime",
        scanned=len(memories),
        roots=roots,
    )


def sweep(roots: Iterable[Path], today: date | None = None) -> AuditReport:
    """Scan and audit in one call — the entry point callers usually want.

    Args:
        roots: Corpus roots to scan recursively.
        today: Reference date; defaults to the current date.

    Returns:
        The advisory report.
    """
    roots = tuple(roots)
    return audit(scan_corpus(roots), roots=roots, today=today)
