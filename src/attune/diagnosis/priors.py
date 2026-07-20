"""Lesson-prior recall — the diagnoser remembers before it spelunks
(advanced-debugging-plugin RR-4).

Queries the ``idx:attune_memory`` index (kept warm by the SessionStart
hydration hook) with terms extracted from the failure's error shape.
Redis unavailability degrades to an EXPLICIT no-priors state recorded
on the DiagnosisRecord — never a silent skip, never a block (RR-4
inverts the usual degrade-silently memory rule: the record must say
why priors are missing).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_INDEX = "idx:attune_memory"

#: Error-shape token patterns, in extraction order: exception classes
#: (``ValueError``), dotted module paths (``attune.ops.runner``),
#: backtick-quoted names, ``*.py`` basenames, and snake_case
#: identifiers (``sdk_error_kind`` — live defect D17: real ops
#: symptoms carry bare identifiers, not tracebacks).
_TERM_PATTERNS = (
    re.compile(r"\b[A-Z][A-Za-z0-9_]*(?:Error|Exception)\b"),
    re.compile(r"\b[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]+){1,}\b"),
    re.compile(r"`([^`\n]{2,60})`"),
    re.compile(r"\b([A-Za-z0-9_]+\.py)\b"),
    re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b"),
)

#: Plain-word fallback (D17): fires ONLY when every shape pattern
#: missed — terse operational symptoms ("path argument is required")
#: previously extracted zero terms and degraded priors on 3/3 real
#: records (2026-07-20). Generic failure vocabulary is stopworded so
#: the fallback recalls the SPECIFIC nouns, not "failed"/"error".
_PLAIN_WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b")
_FALLBACK_STOPWORDS = frozenset(
    {
        "and",
        "are",
        "argument",
        "been",
        "being",
        "code",
        "command",
        "error",
        "exit",
        "failed",
        "failure",
        "for",
        "from",
        "has",
        "have",
        "into",
        "missing",
        "none",
        "not",
        "null",
        "required",
        "run",
        "the",
        "that",
        "this",
        "unknown",
        "was",
        "were",
        "with",
        "without",
        "workflow",
    }
)


def extract_error_terms(text: str, *, limit: int = 8) -> list[str]:
    """Extract dedup'd error-shape terms from failure text.

    Shape patterns lead; when ALL of them miss (the terse-symptom
    class), a stopword-filtered plain-word fallback supplies terms so
    priors recall never degrades to ``no-terms-extracted`` on text
    that carries any signal at all.
    """
    terms: list[str] = []
    for pattern in _TERM_PATTERNS:
        for match in pattern.findall(text or ""):
            token = match.strip() if isinstance(match, str) else match[0].strip()
            if token and token not in terms:
                terms.append(token)
            if len(terms) >= limit:
                return terms
    if terms:
        return terms
    for match in _PLAIN_WORD_RE.findall(text or ""):
        token = match.strip()
        if token.lower() in _FALLBACK_STOPWORDS or token in terms:
            continue
        terms.append(token)
        if len(terms) >= limit:
            break
    return terms


@dataclass
class PriorsResult:
    """Recalled lesson priors, or an explicit reason there are none."""

    lessons: list[str] = field(default_factory=list)  # "name — description"
    degraded: str | None = None


def recall_priors(
    terms: list[str],
    *,
    client: Any = None,
    limit: int = 5,
) -> PriorsResult:
    """OR-join ``terms`` against the memory index; degrade explicitly.

    Args:
        terms: Error-shape terms from :func:`extract_error_terms`.
        client: Optional connected ``redis.Redis`` (tests inject this).
            When None, one is created from ``REDIS_URL``.
        limit: Max lessons returned.
    """
    if not terms:
        return PriorsResult(degraded="no-terms-extracted")
    if client is None:
        try:
            import redis  # noqa: PLC0415 — optional dependency
        except ImportError:
            return PriorsResult(degraded="redis-package-not-installed")
        url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
    # OR-join (plain multi-word queries AND-join and miss paraphrases).
    query = "|".join(t.replace("|", " ") for t in terms)
    try:
        raw = client.execute_command(
            "FT.SEARCH",
            MEMORY_INDEX,
            query,
            "RETURN",
            "2",
            "name",
            "description",
            "LIMIT",
            "0",
            str(limit),
        )
    except Exception as exc:  # noqa: BLE001 — any transport error degrades
        logger.debug("diagnosis priors recall failed: %s", exc)
        return PriorsResult(degraded=f"recall-failed: {type(exc).__name__}")
    return PriorsResult(lessons=_parse_search_reply(raw))


def _parse_search_reply(raw: Any) -> list[str]:
    """Parse an FT.SEARCH reply: [count, key, [f, v, ...], key, ...]."""
    lessons: list[str] = []
    if not isinstance(raw, list | tuple) or len(raw) < 3:
        return lessons
    for i in range(2, len(raw), 2):
        fields_raw = raw[i]
        if not isinstance(fields_raw, list | tuple):
            continue
        pairs = {
            _text(fields_raw[j]): _text(fields_raw[j + 1]) for j in range(0, len(fields_raw) - 1, 2)
        }
        name = pairs.get("name", "")
        description = pairs.get("description", "")
        if name or description:
            lessons.append(f"{name} — {description}".strip(" —"))
    return lessons


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
