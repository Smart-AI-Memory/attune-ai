"""Append-only verdict history for curated memory corpora (P2 task 4).

The advisory sweep (:mod:`attune.memory.curated_audit`) is read-only by
construction, so the write-capable half of P2 lives here: a per-corpus
append-only JSONL log of human verdicts, plus the canonical content
digest that BINDS a verification to the content it verified.

Design rules, from ``docs/specs/memory-status-integrity/decisions.md`` D6:

- ``verified:`` in frontmatter is a bare human-set date. The BINDING —
  who verified, when, and a digest of what they saw — lives in this log,
  because the curated frontmatter schema is closed and must stay closed.
- A **substantive** edit invalidates verification: the current canonical
  digest no longer matches the digest recorded at verdict time. A
  formatting-only change (trailing whitespace, blank-line runs, line
  endings) canonicalises identically and preserves it.
- The log is **append-only**: the failure mode to design against is a
  thoughtless bulk "keep all" — history makes that visible, a mutable
  date would hide it.
- ``wrong`` verdicts TOMBSTONE, never delete — deletion breaks
  ``MEMORY.md`` pointers and ``[[links]]``, and "we believed X, it was
  wrong" is itself high-value memory.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

#: Per-corpus verdict log, sibling to ``MEMORY.md``. A dotfile so corpus
#: scanners that glob ``*.md`` never see it.
VERDICTS_FILENAME = ".verdicts.jsonl"

#: The three verdicts of the review loop (D6 #3).
VERDICT_VALUES = frozenset({"keep", "wrong", "sharper"})


@dataclass(frozen=True)
class VerdictRecord:
    """One human verdict on one curated memory, at one point in time.

    Attributes:
        stem: The memory's filename stem — its corpus-wide identity.
        verdict: One of :data:`VERDICT_VALUES`.
        digest: Canonical content digest at verdict time; the binding.
        who: Who rendered the verdict (human identity, not a model name).
        at: ISO-8601 UTC timestamp.
    """

    stem: str
    verdict: str
    digest: str
    who: str
    at: str

    def __post_init__(self) -> None:
        if self.verdict not in VERDICT_VALUES:
            raise ValueError(
                f"invalid verdict {self.verdict!r}; expected one of {sorted(VERDICT_VALUES)}"
            )

    @classmethod
    def create(cls, stem: str, verdict: str, digest: str, who: str) -> VerdictRecord:
        """Build a record stamped with the current UTC time."""
        return cls(
            stem=stem,
            verdict=verdict,
            digest=digest,
            who=who,
            at=datetime.now(timezone.utc).isoformat(),
        )


def canonical_digest(description: str | None, body: str) -> str:
    """Digest the SUBSTANCE of a memory, ignoring formatting noise.

    Canonicalisation collapses ALL whitespace to a single-space token
    stream — so line re-wraps, trailing whitespace, blank-line churn, and
    CRLF conversions (the edits bulk migrations and format-on-save hooks
    make) all produce the same digest and preserve verification, while
    any change to the words breaks it and invalidates (D6 #2).

    The digest covers ``description`` + body — the two fields a reading
    session actually consumes. ``verified:`` itself is deliberately
    outside the digest, or recording a verification would invalidate it.

    Args:
        description: The frontmatter description, if any.
        body: The markdown body after the frontmatter.

    Returns:
        A sha256 hex digest.
    """
    tokens = " ".join(f"{description or ''}\n{body}".split())
    return hashlib.sha256(tokens.encode("utf-8")).hexdigest()


def append_verdict(root: Path, record: VerdictRecord) -> Path:
    """Append one verdict to the corpus's log. The only writer in P2.

    Args:
        root: Corpus root directory (the ``MEMORY.md`` sibling level).
        record: The verdict to append.

    Returns:
        The log path written.

    Raises:
        ValueError: If ``root`` is not an existing directory or fails
            path validation.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise ValueError(f"corpus root is not a directory: {root_path}")
    log_path = _validate_file_path(str(root_path / VERDICTS_FILENAME), allowed_dir=str(root_path))
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return log_path


def load_verdicts(root: Path) -> list[VerdictRecord]:
    """Read a corpus's verdict history, oldest first. Fail-open.

    A malformed line is skipped with a log warning rather than raising —
    one corrupt append must not disable the whole binding check, and the
    safe degradation for a missing record is "unbound", which the read
    side already treats as the honest default.

    Args:
        root: Corpus root directory.

    Returns:
        Records in file order; empty when no log exists.
    """
    log_path = Path(root) / VERDICTS_FILENAME
    try:
        raw = log_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("unreadable verdict log %s: %s", log_path, exc)
        return []

    records: list[VerdictRecord] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            records.append(
                VerdictRecord(
                    stem=data["stem"],
                    verdict=data["verdict"],
                    digest=data["digest"],
                    who=data["who"],
                    at=data["at"],
                )
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("skipping malformed verdict line %s:%d: %s", log_path, lineno, exc)
    return records


def latest_verdicts(root: Path) -> dict[str, VerdictRecord]:
    """Map each stem to its most recent verdict (append order wins).

    Args:
        root: Corpus root directory.

    Returns:
        Latest record per stem; empty when no log exists.
    """
    latest: dict[str, VerdictRecord] = {}
    for record in load_verdicts(root):
        latest[record.stem] = record
    return latest
