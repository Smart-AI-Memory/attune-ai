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
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from attune.memory.verdict_log import VerdictRecord, canonical_digest, latest_verdicts

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
    #: Canonical content digest (description + body, formatting-normalised).
    #: Compared against the digest recorded at verdict time to decide
    #: whether a ``verified:`` date is still bound to what it verified.
    digest: str = ""

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
    #: Per-file ``(stem, basis_label, age_days)``, aligned row-for-row with
    #: ``ranked`` — see :func:`resolve_age_basis` for the label vocabulary
    #: (P2 task 2). Days are basis-aware so a report can never show an age
    #: that contradicts the basis it states (codex D11 finding).
    age_bases: tuple[tuple[str, str, int], ...] = ()
    #: Which signal ordered ``ranked``: ``age-only`` (no frequency
    #: evidence supplied) or ``age×frequency`` (P3 task 5). Stated so a
    #: report can never imply a basis it didn't use.
    rank_basis: str = "age-only"
    #: Per-file ``(stem, serve_count)`` aligned with ``ranked`` — empty
    #: under ``age-only``.
    serves_by_stem: tuple[tuple[str, int], ...] = ()
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


# A YAML block-scalar header: ``>`` or ``|``, optionally an indentation
# indicator digit and/or chomping ``+``/``-`` (either order), optionally a
# trailing comment. Codex D11 finding: the earlier fixed set missed ``>2`` /
# ``|2-`` / ``> # comment`` forms, silently discarding their continuation.
_BLOCK_SCALAR_RE = re.compile(r"^[>|](?:[0-9][+-]?|[+-][0-9]?)?(?:\s+#.*)?$")


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
    return bool(_BLOCK_SCALAR_RE.match(value))


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
        digest=canonical_digest(fields.get("description"), body),
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


def resolve_age_basis(
    mem: CuratedMemory, latest_verdict: VerdictRecord | None = None
) -> tuple[date, str]:
    """Decide which date ages this memory, and label the decision.

    The basis labels, in decreasing trust (P2 task 2 + task 4):

    - ``verified`` — ``verified:`` present AND the verdict log's digest
      matches the current content: the date is bound to what it verified.
    - ``verified-unbound`` — ``verified:`` present but no verdict record
      exists to bind it. The date stands (backward compatible with a
      hand-set field), but nothing proves what content it endorsed.
    - ``invalidated`` — a verdict record exists and its digest does NOT
      match: the content changed substantively since verification, so the
      ``verified:`` date is void and mtime (the edit) ages it (D6 #2).
    - ``tombstoned`` — the latest verdict is ``wrong``: the memory is
      known-bad and kept only for its pointer/link integrity and its
      "we believed X" value (D6 #3). Checked FIRST — a tombstone applies
      whether or not the file carries ``verified:`` (codex D11 finding:
      the earlier ordering hid tombstones on unverified files).
    - ``mtime`` — no ``verified:`` at all; the known-bad-proxy fallback.

    Args:
        mem: The memory to age.
        latest_verdict: The memory's most recent verdict record, if any.

    Returns:
        ``(basis_date, basis_label)``.
    """
    if latest_verdict is not None and latest_verdict.verdict == "wrong":
        return mem.mtime_date, "tombstoned"
    if mem.verified is None:
        return mem.mtime_date, "mtime"
    if latest_verdict is None:
        return mem.verified, "verified-unbound"
    if latest_verdict.digest == mem.digest:
        return mem.verified, "verified"
    return mem.mtime_date, "invalidated"


def unverified_age_days(
    mem: CuratedMemory,
    today: date | None = None,
    latest_verdict: VerdictRecord | None = None,
) -> int:
    """Days since a human last confirmed this memory is still true.

    ``verified:`` is preferred when present; :func:`resolve_age_basis`
    decides whether it still binds. Without it this falls back to file
    mtime, which is a **known-bad proxy**: it records the last edit, so a
    bulk reformat reads as a fresh confirmation. The fallback ships anyway
    because it errs in the safe direction — mtime makes memories look
    *fresher* than they are, so the signal under-warns rather than
    over-warns.

    Args:
        mem: The memory to age.
        today: Reference date; defaults to the current date. Injectable so
            tests need no clock control.
        latest_verdict: The stem's most recent verdict record, if any —
            supplies the digest binding (P2 task 4).

    Returns:
        Whole days, floored at zero.
    """
    reference = today or date.today()
    basis, _ = resolve_age_basis(mem, latest_verdict)
    return max(0, (reference - basis).days)


def volatility(mem_type: str | None) -> float:
    """Return how fast this memory type goes stale. See VOLATILITY_BY_TYPE."""
    if mem_type is None:
        return DEFAULT_VOLATILITY
    return VOLATILITY_BY_TYPE.get(mem_type, DEFAULT_VOLATILITY)


#: Frequency-factor floor for never-served memories (P3 task 5, R6).
#: Deliberately > 0: an unserved memory is DEPRIORITIZED, never exempt —
#: a 200-day project claim at the floor still ages into review
#: eventually, so nothing rots forever outside the queue (D8 boundary:
#: this reorders REVIEW attention only; recall surfaces never filter).
FREQUENCY_FLOOR = 0.25


def frequency_factor(serves: int) -> float:
    """Scale review rank by how often a memory is actually served (R6).

    Log-scaled so the term rewards "served at all / served often"
    without letting a hot memory drown everything: 0 serves → the
    floor, 1 serve → ~0.94, 30 serves (every session for a month) →
    ~3.7. The exact proof-case shape: an 8-week-stale memory injected
    into every session must outrank a 9-week-stale one nobody recalls.

    Args:
        serves: Serve count over the reader's window
            (:func:`attune.memory.serve_telemetry.serve_counts`).

    Returns:
        A positive multiplier for :func:`risk_score`.
    """
    return FREQUENCY_FLOOR + math.log1p(max(0, serves))


def risk_score(
    mem: CuratedMemory,
    today: date | None = None,
    latest_verdict: VerdictRecord | None = None,
    serves: int | None = None,
) -> float:
    """Rank a memory's need for human review: age × volatility × frequency.

    This orders *review attention* only. Per D1 it must never be used to drop
    a memory from a recall result — a high score means "ask a human", not
    "hide it".

    Args:
        mem: The memory to score.
        today: Reference date; defaults to the current date.
        latest_verdict: The stem's most recent verdict record, if any.
        serves: Serve count over the telemetry window. ``None`` means "no
            frequency evidence available" and applies a NEUTRAL factor —
            the ranking stays age-only rather than pretending every
            memory is unserved (P3 task 5).

    Returns:
        A non-negative score. Higher means review sooner.
    """
    base = unverified_age_days(mem, today, latest_verdict) * volatility(mem.mem_type)
    if serves is None:
        return base
    return base * frequency_factor(serves)


#: Tier thresholds over the age × volatility risk score (P2 task 8).
#: Calibrated against the live corpus: a settled feedback rule stays
#: "settled" for years (volatility 0.15 → ~66 days per risk point), while
#: a project claim crosses "suspect" in ~6 weeks untouched.
TIER_SETTLED_MAX = 10.0
TIER_CHECK_MAX = 45.0

#: The three epistemic tiers, least to most concerning (D6 #5).
EPISTEMIC_TIERS = ("settled", "check-before-acting", "suspect")


def epistemic_tier(mem_type: str | None, basis: str, days: int) -> str:
    """Discrete trust tier for a memory: settled / check-before-acting / suspect.

    D6 #5: "N days unverified" is a number without calibration — the reading
    model has no base rate for 90 days on ``reference`` vs ``project``. The
    tier folds age, type volatility, and verification state into one word.

    ``tombstoned`` and ``invalidated`` are suspect regardless of age — a
    judged-wrong or verification-voided memory cannot out-rank its basis.

    Args:
        mem_type: The memory's ``metadata.type`` (None tolerated).
        basis: The age-basis label from :func:`resolve_age_basis`.
        days: Basis-aware unverified age in days.

    Returns:
        One of :data:`EPISTEMIC_TIERS`.
    """
    if basis in {"tombstoned", "invalidated"}:
        return "suspect"
    risk = days * volatility(mem_type)
    if risk <= TIER_SETTLED_MAX:
        return "settled"
    if risk <= TIER_CHECK_MAX:
        return "check-before-acting"
    return "suspect"


def format_status_annotation(mem_type: str | None, basis: str, days: int) -> str:
    """Render the full epistemic STATUS label for a recall surface (task 8).

    Carries tier + author-class stand-in (the ``metadata.type``) +
    verification state, and for the most dangerous combination —
    ``suspect`` + ``project`` — an explicit instruction, because that is
    the exact shape of both proof-case failures.

    Args:
        mem_type: The memory's ``metadata.type``.
        basis: The age-basis label from :func:`resolve_age_basis`.
        days: Basis-aware unverified age in days.

    Returns:
        e.g. ``⟨suspect · project · 61d unverified⟩ — verify against the
        repo before acting``.
    """
    tier = epistemic_tier(mem_type, basis, days)
    state_by_basis = {
        "verified": f"verified {days}d ago",
        "verified-unbound": f"verified {days}d ago, unbound",
        "invalidated": "verification voided by edit",
        "tombstoned": "judged WRONG — kept as tombstone",
        "mtime": f"{days}d unverified",
    }
    state = state_by_basis.get(basis, f"{days}d unverified")
    label = f"⟨{tier} · {mem_type or 'untyped'} · {state}⟩"
    if tier == "suspect" and mem_type == "project":
        label += " — verify against the repo before acting"
    return label


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
    verdicts: Mapping[Path, VerdictRecord] | None = None,
    serves: Mapping[str, int] | None = None,
) -> AuditReport:
    """Produce an advisory report over already-scanned memories.

    Checks corpus integrity (schema, link resolution, index pointers in both
    directions) and ranks every memory by review priority. Writes nothing.

    Args:
        memories: Parsed memories, typically from :func:`scan_corpus`.
        roots: Corpus roots, used to locate ``MEMORY.md`` index files. When
            omitted, pointer integrity is skipped rather than failed.
        today: Reference date; defaults to the current date.
        verdicts: Latest verdict per memory PATH — path-keyed so a verdict
            in one corpus can never bind or tombstone a same-named memory
            in another (codex D11 finding). :func:`sweep` builds this map;
            omitted means every ``verified:`` reads unbound.
        serves: Per-stem serve counts over the telemetry window (P3 task
            5, from :func:`attune.memory.serve_telemetry.serve_counts`).
            ``None`` keeps the ranking age-only (no frequency evidence);
            a mapping — even an empty one — applies the frequency factor,
            with missing stems at the never-served floor.

    Returns:
        The report. ``ranked`` is ordered by descending risk;
        ``age_bases`` is aligned with it row-for-row.
    """
    roots = tuple(roots)
    verdicts = verdicts or {}
    known_stems = {mem.stem for mem in memories}

    schema_violations, invalid_types, name_mismatches, broken_links = _content_integrity(
        memories, known_stems
    )
    orphans, dangling = _pointer_integrity(memories, known_stems, roots)

    ranked = tuple(
        sorted(
            (
                (
                    mem,
                    risk_score(
                        mem,
                        today,
                        verdicts.get(mem.path),
                        None if serves is None else serves.get(mem.stem, 0),
                    ),
                )
                for mem in memories
            ),
            key=lambda pair: (-pair[1], str(pair[0].path)),
        )
    )
    age_bases = tuple(
        (
            mem.stem,
            resolve_age_basis(mem, verdicts.get(mem.path))[1],
            unverified_age_days(mem, today, verdicts.get(mem.path)),
        )
        for mem, _ in ranked
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
        age_bases=age_bases,
        rank_basis="age-only" if serves is None else "age×frequency",
        serves_by_stem=(
            ()
            if serves is None
            else tuple((mem.stem, serves.get(mem.stem, 0)) for mem, _ in ranked)
        ),
        scanned=len(memories),
        roots=roots,
    )


def sweep(
    roots: Iterable[Path],
    today: date | None = None,
    serves: Mapping[str, int] | None = None,
) -> AuditReport:
    """Scan and audit in one call — the entry point callers usually want.

    Reads each root's verdict log (append-only, task 4) so ``verified:``
    dates are digest-checked; a root without a log degrades to unbound.
    Verdicts are scoped to their OWN root: a record in one corpus's log
    binds only files under that root, never a same-named memory elsewhere.

    ``serves`` is caller-supplied, never auto-loaded: reading the live
    telemetry sink is a side effect the CLIs opt into explicitly, so
    library callers and hermetic tests stay home-dir-clean.

    Args:
        roots: Corpus roots to scan recursively.
        today: Reference date; defaults to the current date.
        serves: Per-stem serve counts (see :func:`audit`).

    Returns:
        The advisory report.
    """
    roots = tuple(roots)
    memories = scan_corpus(roots)
    verdicts: dict[Path, VerdictRecord] = {}
    for root in roots:
        latest = latest_verdicts(root)
        if not latest:
            continue
        for mem in memories:
            if mem.stem in latest and root in mem.path.parents:
                verdicts[mem.path] = latest[mem.stem]
    return audit(memories, roots=roots, today=today, verdicts=verdicts, serves=serves)
