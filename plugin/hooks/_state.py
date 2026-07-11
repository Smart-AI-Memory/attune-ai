"""Shared state-discovery helpers for session-continuity hooks.

Pure-Python module — no Claude Code SDK calls, no network I/O.
Used by `spec_orient.py`, `compact_warning.py`, and the
`/handoff` slash command.

Three responsibilities:

1. ``discover_specs(roots)`` — walk every ``specs/`` directory
   under ``roots`` for in-flight specs, returns most-recently
   modified first.
2. ``git_state(cwd)`` — branch + last commit + uncommitted file
   list. Tolerates missing git or non-repo paths.
3. ``session_sentinel_path(session_id)`` — the once-per-session
   file used by ``compact_warning.py`` so the warning fires
   exactly once.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

# ── Drift-cache read (spec-status-integrity, design §3) ───────
#
# ``spec_audit.py --pr-links`` writes ``.attune/spec-drift.json`` per
# workspace root; ``spec_orient`` reads it back so the SessionStart
# annotation stays offline (the hook's no-network invariant). Entries
# older than one weekly-CI period + slack are ignored.
_DRIFT_CACHE_MAX_AGE_SECONDS = 8 * 24 * 60 * 60


def read_drift_cache(roots: list[Path], now: float | None = None) -> dict[str, dict]:
    """Merge fresh drift-cache entries across workspace roots.

    Returns ``{"<layer>/<slug>": {verdict, prs, signal}}`` from every
    root whose ``.attune/spec-drift.json`` is present, well-formed, and
    fresher than :data:`_DRIFT_CACHE_MAX_AGE_SECONDS`. Anything else —
    absent file, malformed JSON, wrong shapes, stale ``generated_at`` —
    contributes nothing and never raises (the cache is advisory; the
    annotation simply falls back to current behavior).
    """
    current = time.time() if now is None else now
    merged: dict[str, dict] = {}
    for root in roots:
        cache_path = Path(root) / ".attune" / "spec-drift.json"
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        generated = data.get("generated_at")
        if not isinstance(generated, int | float):
            continue
        if current - float(generated) > _DRIFT_CACHE_MAX_AGE_SECONDS:
            continue
        specs = data.get("specs")
        if not isinstance(specs, dict):
            continue
        for key, entry in specs.items():
            if isinstance(key, str) and isinstance(entry, dict):
                merged.setdefault(key, entry)
    return merged


# Phases checked, highest-priority first. The first phase file
# present in a spec directory determines the displayed phase
# and status.
_PHASE_FILES: tuple[tuple[str, str], ...] = (
    ("tasks", "tasks.md"),
    ("design", "design.md"),
    ("requirements", "requirements.md"),
)

# Robust to markdown bold variants around the label and colon:
# ``Status:``, ``**Status**:``, ``**Status:**`` (colon inside the bold),
# ``*Status*:``. Brittleness here was a real bug — a ``**Status:**
# complete`` header matched none of the old pattern and the spec stayed
# in-flight despite being marked done (see decisions.md DECIDE-2).
_STATUS_LINE = re.compile(
    r"^\s*\**\s*Status\**\s*:\s*\**\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Self-truthing additions — match terminal signals anywhere in
# the spec file (not just the header), so a stale "draft" header
# above a closed checklist doesn't keep the spec in-flight.
#
# NB: no ``$`` anchor and a ``\b`` after the verdict, so an
# *informative* terminal line — ``Status: complete (2026-06-09) —
# shipped #694`` — is recognized, not just the bare ``Status:
# complete``. Before this, the natural human format was silently
# ignored and the spec stayed in-flight forever despite being marked
# done (see decisions.md DECIDE-2).
_TERMINAL_LINE = re.compile(
    r"^\s*\**\s*(?:Spec\s+)?Status\**\s*:\s*\**\s*"
    r"(closed|complete|completed|retired|superseded|shipped|done|implemented)\b",
    re.IGNORECASE | re.MULTILINE,
)
_CHECKLIST_HEADING = re.compile(
    r"^##\s+Completion\s+checklist\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_CHECKLIST_LINE = re.compile(
    r"^\s*-\s*\[([ xX])\]\s+(.*?)\s*$",
    re.MULTILINE,
)
_DEFERRED_MARKERS = re.compile(
    r"(~~.*?~~|\bdeferred\b|\bN/A\b|\bwon't\s+do\b)",
    re.IGNORECASE,
)
_NEXT_H2 = re.compile(r"^##\s+", re.MULTILINE)
_TERMINAL_VERDICTS = frozenset(
    {
        "closed",
        "complete",
        "completed",
        "retired",
        "superseded",
        "shipped",
        "done",
        # spec-status-integrity additions (design §1): ``implemented``
        # and the bare check glyphs are terminal — the wild-scan found
        # both in real headers.
        "implemented",
        "✓",
        "✅",
    }
)
# Ongoing-by-design statuses: a living roadmap / continuous program is not
# pending work, so it should NOT show as in-flight — but it is also not
# "done". Excluded from the in-flight list, kept distinct from terminal.
_ONGOING_VERDICTS = frozenset({"living", "ongoing"})
# Parked-semantics statuses (spec-status-integrity, design §1): work
# deliberately on hold. Skipped by drift checks and excluded from the
# in-flight orientation list; the audit still lists them (as parked).
_PARKED_VERDICTS = frozenset({"parked", "paused", "blocked", "deferred"})

# Leading alphabetic word of a status value, for first-word tokenization:
# ``complete (2026-06-09) — shipped #694`` -> ``complete``.
_LEADING_WORD = re.compile(r"[a-zA-Z]+")


def _leading_verdict(status: str) -> str:
    """Return the lowercased leading word of a status value, or ``""``.

    Status headers are written informatively (``complete (date) —
    reason``), so terminal/ongoing recognition keys off the FIRST word,
    not exact-string membership. This is the fix for the class of bug
    where a correctly-marked-``complete`` spec stayed in-flight forever
    because ``"complete (date) — ..."`` is not in ``_TERMINAL_VERDICTS``.

    A bare check glyph (``✓`` / ``✅``) leading the value is returned
    as-is — the glyphs are members of ``_TERMINAL_VERDICTS``
    (spec-status-integrity, design §1) but are not alphabetic, so the
    word regex would otherwise skip past them to whatever word follows.
    """
    stripped = status.strip().lstrip("*_`").strip()
    for glyph in ("✅", "✓"):
        if stripped.startswith(glyph):
            return glyph
    # search (not match) so a stray leading ``**``/punctuation doesn't
    # swallow the verdict — the first alphabetic run is the word we want.
    m = _LEADING_WORD.search(status)
    return m.group(0).lower() if m else ""


# ── Status-vocabulary lint (spec-status-integrity, design §1) ─
#
# The canonical vocabulary for NEW specs. Historical aliases
# (``_TERMINAL_VERDICTS`` / ``_ONGOING_VERDICTS`` members and the
# in-flight forms below) stay accepted — no mass rewrite of ~127
# existing status lines — but the lint steers authors to these 8.
_CANONICAL_STATUS_TOKENS = (
    "draft",
    "in-review",
    "approved",
    "in-progress",
    "implemented",
    "complete",
    "superseded",
    "parked",
)
# In-flight forms honored by the checker (design §2): the canonical
# in-flight 4 plus the historical ``not started`` / ``open`` / ``pending``.
# ``not`` is the leading token of ``not started``.
_IN_FLIGHT_TOKENS = frozenset(
    {"draft", "in-review", "approved", "in-progress", "not", "open", "pending"}
)
# Lint tokenization keeps hyphens (``in-review``), unlike
# ``_LEADING_WORD`` which stops at the first non-alpha char.
_LINT_TOKEN = re.compile(r"[A-Za-z][A-Za-z-]*")


def lint_status_token(status: str) -> str | None:
    """Lint a status value's leading token against the known vocabulary.

    Returns ``None`` when the leading token is recognized — one of the
    canonical 8, a historical terminal/ongoing alias, a parked-family
    token, an accepted in-flight form, or a bare check glyph. Otherwise
    returns a one-line ``unparseable`` message naming the canonical 8;
    the token is never guessed at.
    """
    stripped = status.strip().lstrip("*_`").strip()
    for glyph in ("✅", "✓"):
        if stripped.startswith(glyph):
            return None
    match = _LINT_TOKEN.search(status)
    token = match.group(0).lower() if match else ""
    recognized = (
        _TERMINAL_VERDICTS | _ONGOING_VERDICTS | _PARKED_VERDICTS | _IN_FLIGHT_TOKENS
    ) | set(_CANONICAL_STATUS_TOKENS)
    if token in recognized:
        return None
    shown = token or status.strip() or "(empty)"
    return f'unparseable status "{shown}" — use one of: ' + ", ".join(_CANONICAL_STATUS_TOKENS)


# ── PR-reference extraction (spec-status-integrity, design §1) ──
#
# ``extract_pr_refs()`` parses the four PR-citation styles found in the
# wild (workspace spec design.md §1): explicit ``PR #212`` /
# ``PRs #303, #304`` lists, bare ``#1191`` (ambiguous — may be an
# issue; resolved at check time via the pulls API, merged-only), and
# the markdown pull-URL — the required style for cross-repo refs.
# Code fences and inline code spans are blanked first so quoted
# examples (`` `#NNN` `` in docs) never count as citations.
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_PULL_URL = re.compile(r"https://github\.com/(?P<repo>[\w.-]+/[\w.-]+)/pull/(?P<number>\d+)\b")
# Whole markdown links are blanked AFTER pull-URLs are extracted, so a
# link text like ``[#95](…/pull/95)`` doesn't ALSO scan as a bare
# current-repo ref — and issue-links yield nothing at all.
_MD_LINK = re.compile(r"\[[^\]\n]*\]\([^)\n]*\)")
_PR_LIST = re.compile(r"\bPRs?\s*#\d+(?:\s*,\s*#\d+)*", re.IGNORECASE)
_REF_NUMBER = re.compile(r"#(\d+)")
# Bare ``#NNN``: not preceded by a word char / ``#`` / ``/`` (rejects
# ``foo#12``, anchors, URL paths) and not followed by a word char
# (rejects ``#12abc``).
_BARE_REF = re.compile(r"(?<![\w#/])#(\d+)(?![\w#])")


@dataclass(frozen=True)
class PrRef:
    """One PR citation extracted from a spec's text.

    ``repo`` is the explicit ``owner/name`` slug from a pull-URL
    citation; ``None`` means "current repo". ``explicit`` is True when
    the citation is unambiguously a PR (``PR #N`` / ``PRs #N, …`` /
    pull-URL); a bare ``#NNN`` is ``explicit=False`` — it may be an
    issue, which the checker resolves via the pulls API at check time.
    """

    number: int
    repo: str | None = None
    explicit: bool = False


def _blank(match: re.Match[str]) -> str:
    """Length-preserving mask so match positions stay comparable."""
    return " " * (match.end() - match.start())


def extract_pr_refs(text: str) -> list[PrRef]:
    """Extract PR citations from spec text — deduped, document order.

    Styles recognized (workspace design §1): ``PR #212``,
    ``PRs #303, #304``, bare ``#1191``, and
    ``https://github.com/<owner>/<repo>/pull/<n>`` (markdown-wrapped or
    bare). Duplicate ``(repo, number)`` pairs collapse to the earliest
    occurrence, upgraded to ``explicit`` if any occurrence was.
    """
    scrubbed = _CODE_FENCE.sub(_blank, text)
    scrubbed = _INLINE_CODE.sub(_blank, scrubbed)

    hits: list[tuple[int, str | None, int, bool]] = []  # (pos, repo, number, explicit)

    for match in _PULL_URL.finditer(scrubbed):
        hits.append((match.start(), match.group("repo"), int(match.group("number")), True))
    # Blank markdown links wholesale (pull-URLs already harvested), then
    # any bare pull-URLs outside links, before the plain-text scans.
    scrubbed = _MD_LINK.sub(_blank, scrubbed)
    scrubbed = _PULL_URL.sub(_blank, scrubbed)

    for match in _PR_LIST.finditer(scrubbed):
        for num in _REF_NUMBER.finditer(match.group(0)):
            hits.append((match.start() + num.start(), None, int(num.group(1)), True))
    scrubbed = _PR_LIST.sub(_blank, scrubbed)

    for match in _BARE_REF.finditer(scrubbed):
        hits.append((match.start(), None, int(match.group(1)), False))

    # Dedupe on (repo, number): earliest position wins the slot; the
    # explicit flag is OR-merged across occurrences.
    best: dict[tuple[str | None, int], tuple[int, bool]] = {}
    for pos, repo, number, explicit in hits:
        key = (repo, number)
        if key in best:
            prev_pos, prev_explicit = best[key]
            best[key] = (prev_pos, prev_explicit or explicit)
        else:
            best[key] = (pos, explicit)
    ordered = sorted(best.items(), key=lambda item: item[1][0])
    return [
        PrRef(number=number, repo=repo, explicit=explicit)
        for (repo, number), (_pos, explicit) in ordered
    ]


# ── Deliverables block (spec-status-integrity, DECIDE-3) ──────
#
# A machine-readable "## Deliverables" section names the paths/globs
# (and optional symbols) a spec ships. The staleness classifier checks
# them for existence on disk so a spec whose work shipped but whose
# Status line still says draft/approved can be flagged. Grammar lives
# in the spec's design.md §"Data contract".
_DELIVERABLES_HEADING = re.compile(
    r"^##\s+Deliverables\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# One deliverable: ``- <path-or-glob>`` with an optional
# `` — symbol: <name>`` (em-dash or ``--``) suffix; the path may be
# backtick-wrapped. The pattern is non-greedy so the symbol suffix is
# split off rather than swallowed.
_DELIVERABLE_ITEM = re.compile(
    r"^\s*-\s+"
    r"`?(?P<pattern>[^`\s][^`]*?)`?"
    r"(?:\s+(?:—|--)\s*symbol:\s*(?P<symbol>\S+))?"
    r"\s*$",
)
# A lone ``- N/A`` / ``- None`` item ⇒ docs-only sentinel. Tolerant of
# italic/backtick wrappers (``_None_``) and a trailing period/ellipsis.
_DELIVERABLE_NA = re.compile(
    r"^\s*-\s+[_*`]*\s*(?:N/?A|None)\s*(?:\.{1,3})?\s*[_*`]*\s*$",
    re.IGNORECASE,
)
# Opt-out line, matched anywhere in the file (mirrors the terminal-line
# anywhere-scan): a deliberate long-lived draft suppresses the check.
_DRIFT_OPT_OUT = re.compile(
    r"^\s*drift-check:\s*ignore\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Glob metacharacters — a deliverable pattern containing any of these is
# resolved by splitting off the literal-prefix dir and globbing the tail
# inside it (pathlib ``**`` does not recurse into symlinked dirs
# reliably, so we glob from the already-symlink-followed prefix).
_GLOB_CHARS = re.compile(r"[*?\[]")


# Sentinel TTL: anything older than this on a SessionStart prune
# sweep is considered orphaned from an ungraceful exit.
_SENTINEL_TTL_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class DeliverableEntry:
    """One declared deliverable from a spec's ``## Deliverables`` block.

    ``pattern`` is a repo-prefixed path or glob (e.g.
    ``attune-ai/plugin/hooks/spec_audit.py`` or
    ``attune-gui/tests/**/test_bar.py``). ``symbol`` is an optional
    grep target (function / class name) that must also be present in a
    matched file before the entry counts as resolved.
    """

    pattern: str
    symbol: str = ""


@dataclass(frozen=True)
class DeliverableSpec:
    """Parsed ``## Deliverables`` contract for one spec.

    ``is_na`` marks the docs-only sentinel (a lone ``- N/A`` item);
    ``opt_out`` marks a deliberate ``drift-check: ignore`` suppression.
    Both keep a spec out of ``suspected-stale`` without silent magic.
    """

    entries: tuple[DeliverableEntry, ...] = ()
    is_na: bool = False
    opt_out: bool = False


@dataclass(frozen=True)
class SpecInfo:
    """One in-flight spec discovered under a workspace root."""

    slug: str
    """Directory name, e.g. ``precompact-sessionstart-hooks``."""

    path: Path
    """Absolute path to the spec directory."""

    layer: str
    """Layer slug (``workspace`` for root specs, else
    ``attune-rag`` / ``attune-help`` / etc.)."""

    phase: str
    """``requirements`` | ``design`` | ``tasks``."""

    status: str
    """Verbatim status line value, lowercased
    (e.g. ``approved``, ``in-progress``, ``draft``).

    Raw header value, preserved for back-compat. Consumers that
    care about completion-state reconciliation should read
    ``effective_status`` instead.
    """

    mtime: float
    """Most-recent mtime across spec files (seconds since epoch)."""

    # Self-truthing additions (2026-06-02). All optional with safe
    # defaults so existing positional constructors don't break.
    effective_status: str = ""
    """Reconciled status — overrides ``status`` when a terminal
    signal (completed checklist / explicit closed line) is found
    deeper in the file. Falls back to ``status`` when no terminal
    signal is present. See DECIDE-1 in the spec's decisions.md."""

    status_source: str = "header"
    """Where ``effective_status`` came from — one of
    ``"header"`` / ``"checklist"`` / ``"terminal-line"``."""

    status_conflict: bool = False
    """True when ``effective_status`` overrode a non-terminal
    ``status`` (i.e. header drifted away from completion state).
    spec_orient renders a one-line hint when True."""

    # spec-status-integrity additions (2026-06-17). Optional with safe
    # defaults so existing positional/keyword constructors don't break
    # (same discipline as the 2026-06-02 self-truthing fields above).
    deliverables: tuple[DeliverableEntry, ...] = ()
    """Deliverables parsed from the chosen phase file's
    ``## Deliverables`` block; empty when none are declared."""

    staleness: str = "unknown"
    """Staleness verdict from ``classify_staleness`` — one of
    ``ok`` / ``suspected-stale`` / ``unknown`` / ``partial`` /
    ``docs-only`` / ``opted-out``. See DECIDE-3..5."""


@dataclass(frozen=True)
class GitState:
    """Snapshot of the worktree's git state at hook fire time."""

    branch: str
    last_sha: str
    last_subject: str
    uncommitted: tuple[str, ...]


def _read_phase(path: Path) -> tuple[str, str]:
    """Return ``(status, full_text)`` from a phase file.

    Status is the lowercased value from the first ``**Status:**``
    line, or empty string if absent. The full text is returned so
    the reconciler can scan for terminal signals deeper in the file
    without re-reading from disk.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", ""
    match = _STATUS_LINE.search(text)
    status = match.group(1).strip().lower() if match else ""
    return status, text


def _read_status(path: Path) -> str:
    """Return the lowercased status from a phase file, or empty.

    Back-compat shim — prefer ``_read_phase`` when you also need the
    full text for reconciliation.
    """
    status, _ = _read_phase(path)
    return status


def _completion_signal(text: str) -> tuple[str | None, str]:
    """Read terminal markers from a phase file's text.

    Looks for two signals:

    1. **Terminal-line scan** — explicit ``Spec status: closed`` /
       ``Status: complete`` / etc. anywhere in the file.
    2. **Completion-checklist scan** — a ``## Completion checklist``
       section where all non-deferred rows are checked.

    Returns ``(verdict, source)``:
        - verdict: ``"closed"`` / ``"complete"`` / ``"retired"`` /
          ``"superseded"`` if a terminal signal exists, else None.
        - source: ``"terminal-line"`` / ``"checklist"`` when verdict
          is non-None, else ``"header"``.
    """
    # 1. Terminal-line scan — short-circuit on first hit.
    match = _TERMINAL_LINE.search(text)
    if match:
        return match.group(1).lower(), "terminal-line"

    # 2. Completion-checklist scan.
    heading = _CHECKLIST_HEADING.search(text)
    if heading is None:
        return None, "header"

    section_start = heading.end()
    next_heading = _NEXT_H2.search(text, section_start)
    section_end = next_heading.start() if next_heading else len(text)
    section = text[section_start:section_end]

    items = list(_CHECKLIST_LINE.finditer(section))
    if not items:
        return None, "header"

    checked = 0
    outstanding = 0
    for item in items:
        box, body = item.group(1), item.group(2)
        if _DEFERRED_MARKERS.search(body):
            continue  # deferred — not outstanding
        if box.strip().lower() == "x":
            checked += 1
        else:
            outstanding += 1

    # All non-deferred items checked, AND at least one was checked
    # (guard against empty / all-deferred sections producing a
    # spurious "complete" verdict).
    if checked > 0 and outstanding == 0:
        return "complete", "checklist"

    return None, "header"


def deliverables_for_spec(text: str) -> DeliverableSpec:
    """Parse a spec's ``## Deliverables`` block into a contract.

    Same regex-driven style as ``_completion_signal``. The section is
    bounded by the ``## Deliverables`` heading and the next ``## `` (via
    ``_NEXT_H2``). Each list item becomes a ``DeliverableEntry``; a lone
    ``- N/A`` item sets ``is_na``; a ``drift-check: ignore`` line found
    anywhere in the file sets ``opt_out``.

    A malformed or empty block yields zero entries (so the classifier
    reports ``unknown``, never a false ``suspected-stale``). The opt-out
    scan is independent of the section, mirroring the terminal-line scan.
    """
    opt_out = bool(_DRIFT_OPT_OUT.search(text))

    heading = _DELIVERABLES_HEADING.search(text)
    if heading is None:
        return DeliverableSpec(opt_out=opt_out)

    section_start = heading.end()
    next_heading = _NEXT_H2.search(text, section_start)
    section_end = next_heading.start() if next_heading else len(text)
    section = text[section_start:section_end]

    entries: list[DeliverableEntry] = []
    is_na = False
    for line in section.splitlines():
        if not line.lstrip().startswith("-"):
            continue
        if _DELIVERABLE_NA.match(line):
            is_na = True
            continue
        match = _DELIVERABLE_ITEM.match(line)
        if match is None:
            continue
        pattern = match.group("pattern").strip()
        if not pattern:
            continue
        symbol = (match.group("symbol") or "").strip()
        entries.append(DeliverableEntry(pattern=pattern, symbol=symbol))

    return DeliverableSpec(entries=tuple(entries), is_na=is_na, opt_out=opt_out)


def _reconcile_status(header_status: str, phase_text: str) -> tuple[str, str, bool]:
    """Reconcile header status against completion signals.

    DECIDE-1 (decisions.md): terminal signal wins over stale
    non-terminal headers. Falls back to header when no terminal
    signal is present.

    Returns ``(effective_status, status_source, status_conflict)``.
    """
    verdict, source = _completion_signal(phase_text)
    if verdict is None:
        return header_status, "header", False

    # Terminal signal exists. Per DECIDE-1, terminal wins.
    # First-word tokenization so an informative header (``complete
    # (date) — reason``) is recognized as terminal, not just the bare
    # word — otherwise we'd flag a spurious conflict against a header
    # that actually agrees with the body signal.
    header_is_terminal = _leading_verdict(header_status) in _TERMINAL_VERDICTS
    return verdict, source, not header_is_terminal


def _split_glob(pattern: str) -> tuple[str, str]:
    """Split a path-glob into ``(literal_prefix, glob_tail)``.

    The literal prefix is the leading run of ``/``-separated segments
    that contain no glob metacharacters; the tail is the remainder
    (which begins at the first segment that does). A plain path with no
    glob yields an empty tail. Splitting lets the caller resolve the
    prefix directory (following any symlink) and then glob the tail
    *inside* the real directory — avoiding pathlib's unreliable
    ``**``-across-symlink recursion (D-4).
    """
    parts = pattern.split("/")
    literal: list[str] = []
    for i, part in enumerate(parts):
        if _GLOB_CHARS.search(part):
            return "/".join(literal), "/".join(parts[i:])
        literal.append(part)
    return "/".join(literal), ""


def _symbol_present(files: list[Path], symbol: str) -> bool:
    """True if ``symbol`` appears as a substring in any of ``files``.

    v1 uses plain substring matching (decisions.md "Open" — AST-accurate
    detection is out of scope). Unreadable files are skipped.
    """
    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if symbol in content:
            return True
    return False


def _resolve_entry(entry: DeliverableEntry, roots: list[Path]) -> bool:
    """True if a deliverable resolves to an on-disk file under any root.

    Resolution semantics (D-4):

    - The pattern is repo-prefixed (``attune-rag/src/...``) and every
      layer is a symlink under the workspace root, so ``root / pattern``
      follows the symlink without ``.resolve()`` (which would escape the
      root — see ``reference_sibling_editable_venvs``).
    - Globs are split into a literal prefix + tail; the prefix dir is
      resolved first, then the tail is globbed inside it.
    - When ``entry.symbol`` is set, at least one matched file must also
      contain the symbol (substring grep) for the entry to resolve.
    """
    prefix, tail = _split_glob(entry.pattern)
    for root in roots:
        matched: list[Path] = []
        if tail:
            base = root / prefix if prefix else root
            try:
                if not base.is_dir():
                    continue
                matched = [p for p in base.glob(tail) if p.is_file()]
            except OSError:
                continue
        else:
            candidate = root / entry.pattern
            try:
                if not candidate.exists():
                    continue
                if candidate.is_file():
                    matched = [candidate]
                else:
                    # Directory deliverable — existence is the signal; a
                    # symbol grep over a directory is meaningless.
                    if not entry.symbol:
                        return True
                    continue
            except OSError:
                continue
        if not matched:
            continue
        if entry.symbol:
            if _symbol_present(matched, entry.symbol):
                return True
            continue
        return True
    return False


def classify_staleness(spec_text: str, header_status: str, roots: list[Path]) -> str:
    """Classify a spec's staleness from its declared deliverables.

    Returns one of (design.md §"Classifier", D-5 — require ALL):

    - ``opted-out``       — a ``drift-check: ignore`` line is present.
    - ``docs-only``       — the ``- N/A`` docs-only sentinel.
    - ``unknown``         — no Deliverables block, zero parseable
      entries, or entries declared but none present yet (genuinely
      pre-implementation — no actionable signal).
    - ``partial``         — at least one entry resolves, but not all
      (mid-implementation; never flagged, to keep the warning quiet).
    - ``suspected-stale`` — ALL entries resolve AND the (reconciled)
      status is still non-terminal: work shipped, status didn't.
    - ``ok``              — all entries resolve AND the status is
      already terminal/ongoing.
    """
    spec = deliverables_for_spec(spec_text)
    if spec.opt_out:
        return "opted-out"
    if spec.is_na:
        return "docs-only"
    if not spec.entries:
        return "unknown"

    resolved = sum(1 for entry in spec.entries if _resolve_entry(entry, roots))
    if resolved == 0:
        return "unknown"
    if resolved < len(spec.entries):
        return "partial"

    # Every declared deliverable resolves. Reconcile the header against
    # any in-body terminal signal (DECIDE-1) so a spec already marked
    # done deeper in the file is not falsely flagged.
    effective, _source, _conflict = _reconcile_status(header_status, spec_text)
    lead = _leading_verdict(effective)
    # Parked-family statuses are deliberately on hold — skipped by drift
    # checks (design §1), so they classify ``ok`` alongside terminal.
    if lead in _TERMINAL_VERDICTS or lead in _ONGOING_VERDICTS or lead in _PARKED_VERDICTS:
        return "ok"
    return "suspected-stale"


def _phase_for_dir(
    spec_dir: Path,
) -> tuple[str, str, str, str, bool, str, float] | None:
    """Pick the highest-priority phase file present in a spec dir.

    Returns ``(phase, raw_status, effective_status, status_source,
    status_conflict, phase_text, mtime)``:

    - ``phase`` — ``requirements`` / ``design`` / ``tasks``
    - ``raw_status`` — verbatim header status, lowercased
    - ``effective_status`` — reconciled verdict (terminal signal
      wins over a stale header per DECIDE-1)
    - ``status_source`` — ``"header"`` / ``"checklist"`` /
      ``"terminal-line"``
    - ``status_conflict`` — True when ``effective_status`` overrode
      a non-terminal ``raw_status``
    - ``phase_text`` — full text of the chosen phase file, so the
      caller can parse the Deliverables block and classify staleness
      without re-reading from disk
    - ``mtime`` — most recent across all phase files (fresh-file
      bumps the spec to the top of the list)

    Returns ``None`` when no phase file is readable.
    """
    chosen: tuple[str, str, str, str, bool, str] | None = None
    latest_mtime = 0.0
    for phase, fname in _PHASE_FILES:
        fpath = spec_dir / fname
        if not fpath.is_file():
            continue
        try:
            file_mtime = fpath.stat().st_mtime
        except OSError:
            continue
        if file_mtime > latest_mtime:
            latest_mtime = file_mtime
        if chosen is None:
            raw_status, phase_text = _read_phase(fpath)
            effective, source, conflict = _reconcile_status(raw_status, phase_text)
            chosen = (phase, raw_status, effective, source, conflict, phase_text)
    if chosen is None:
        return None
    return (*chosen, latest_mtime)


def _is_in_flight(phase: str, effective_status: str) -> bool:
    """Decide whether a spec is in-flight per the reconciled verdict.

    Rules (keyed off the status's FIRST WORD, so an informative
    header like ``complete (2026-06-09) — shipped #694`` is recognized,
    not just the bare verdict — see DECIDE-2):
    - First word is terminal (closed / complete / completed / retired
      / superseded / shipped / done) → done, exclude — regardless of
      phase.
    - First word is ongoing-by-design (living / ongoing) → a continuous
      program / living roadmap is not pending work, exclude.
    - First word is parked-family (parked / paused / blocked /
      deferred) → deliberately on hold, not pending work, exclude
      (spec-status-integrity, design §1).
    - Empty status (malformed) → still in-flight (don't drop a
      working spec because the heading was malformed).
    - Anything else (draft / approved / in-progress / …) → in-flight.

    The historical "tasks + complete only" rule is subsumed; a
    requirements.md with a body ``Status: closed`` is excluded too
    (the self-truthing improvement).
    """
    lead = _leading_verdict(effective_status)
    if lead in _TERMINAL_VERDICTS or lead in _ONGOING_VERDICTS or lead in _PARKED_VERDICTS:
        return False
    return True


def _layer_for(roots: list[Path], base: Path) -> str:
    """Resolve the layer slug for a spec's base directory.

    ``base`` is the directory that *contains* the spec subdir
    (``specs`` or ``docs/specs``) — either the workspace root or a
    layer dir.

    Workspace-root specs → ``workspace``.
    Layer specs (``<workspace>/attune-rag/...``) → ``attune-rag``.
    """
    if base in roots:
        return "workspace"
    return base.name or "workspace"


# Spec-subdir conventions probed under each root and layer dir.
# attune-gui and workspace-root specs live in ``specs/``;
# attune-rag/author/help keep theirs in ``docs/specs/``. Probing both
# lets one identical hook serve every repo (supersedes a per-repo
# config). Root-level matches are processed before layer matches so a
# root ``docs/specs`` is attributed to ``workspace`` (see dedup below).
_SPEC_SUBDIRS: tuple[str, ...] = ("specs", "docs/specs")


def discover_specs(roots: list[Path], include_terminal: bool = False) -> list[SpecInfo]:
    """Walk ``specs/`` directories under each root for in-flight specs.

    Args:
        roots: Workspace roots to scan. Each root is checked for a
            top-level ``specs/`` and for ``<root>/<layer>/specs/``
            directories (one nested level only — no recursive walk).
        include_terminal: When False (default), terminal/ongoing specs
            are excluded — the in-flight-only view ``spec_orient`` wants.
            When True, every spec is returned with its staleness verdict
            populated — the full table ``spec_audit`` prints.

    Returns:
        ``SpecInfo`` list, most-recently modified first. Tolerates
        missing dirs and malformed status lines. Each result carries its
        parsed ``deliverables`` and ``staleness`` verdict.
    """
    found: list[SpecInfo] = []
    seen: set[Path] = set()
    for root in roots:
        # (base, specs_dir) pairs. ``base`` is the dir that contains the
        # spec subdir and decides the layer label. Root-level bases are
        # listed first so a ``docs/specs`` at the root is attributed to
        # ``workspace`` before the layer walk reaches the same path.
        candidate_bases: list[tuple[Path, Path]] = [(root, root / sub) for sub in _SPEC_SUBDIRS]
        try:
            for entry in sorted(root.iterdir()):
                if entry.is_dir():
                    candidate_bases.extend((entry, entry / sub) for sub in _SPEC_SUBDIRS)
        except OSError:
            continue
        for base, specs_dir in candidate_bases:
            if not specs_dir.is_dir():
                continue
            try:
                spec_dirs = sorted(p for p in specs_dir.iterdir() if p.is_dir())
            except OSError:
                continue
            for spec_dir in spec_dirs:
                resolved = spec_dir.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                phase_info = _phase_for_dir(spec_dir)
                if phase_info is None:
                    continue
                (
                    phase,
                    raw_status,
                    effective,
                    source,
                    conflict,
                    phase_text,
                    mtime,
                ) = phase_info
                if not include_terminal and not _is_in_flight(phase, effective):
                    continue
                deliverable_spec = deliverables_for_spec(phase_text)
                staleness = classify_staleness(phase_text, raw_status, roots)
                found.append(
                    SpecInfo(
                        slug=spec_dir.name,
                        path=spec_dir,
                        layer=_layer_for(roots, base),
                        phase=phase,
                        status=raw_status,
                        mtime=mtime,
                        effective_status=effective,
                        status_source=source,
                        status_conflict=conflict,
                        deliverables=deliverable_spec.entries,
                        staleness=staleness,
                    )
                )
    found.sort(key=lambda s: s.mtime, reverse=True)
    return found


def _run_git(cwd: Path, *args: str) -> str:
    """Run a git command and return stdout, or empty on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def git_state(cwd: Path) -> GitState:
    """Return branch, last commit, and uncommitted files for ``cwd``.

    Empty fields when ``cwd`` isn't a git repo or git is missing.
    """
    branch = _run_git(cwd, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if not branch:
        return GitState(branch="", last_sha="", last_subject="", uncommitted=())
    log_output = _run_git(cwd, "log", "-1", "--format=%h%x09%s")
    last_sha = ""
    last_subject = ""
    if log_output:
        parts = log_output.strip().split("\t", 1)
        last_sha = parts[0]
        if len(parts) > 1:
            last_subject = parts[1]
    porcelain = _run_git(cwd, "status", "--porcelain")
    uncommitted: list[str] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        # Porcelain format: ``XY <path>`` (status flags + space + path).
        path = line[3:].strip()
        if path:
            uncommitted.append(path)
    return GitState(
        branch=branch,
        last_sha=last_sha,
        last_subject=last_subject,
        uncommitted=tuple(uncommitted),
    )


def _sentinel_dir() -> Path:
    """Resolve the directory used for once-per-session sentinels.

    Honors ``ATTUNE_AI_SENTINEL_DIR`` for tests; otherwise uses
    ``~/.attune``. The Claude Code session-state directory is
    not documented as an env var as of 2026-05, so the
    ``~/.attune`` fallback is the primary path.
    """
    override = os.environ.get("ATTUNE_AI_SENTINEL_DIR")
    if override:
        return Path(override)
    return Path.home() / ".attune"


def session_sentinel_path(session_id: str | None) -> Path:
    """Path to the once-per-session compact-warning sentinel.

    Uses a sanitized session id so the path stays inside the
    sentinel dir even with weird inputs.
    """
    base = _sentinel_dir()
    safe = "unknown"
    if session_id:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:64] or "unknown"
    return base / f".compact-warned-{safe}"


def prune_stale_sentinels(now: float | None = None) -> int:
    """Delete sentinel files older than the TTL.

    Returns the number of files removed. Safe to call when the
    sentinel dir doesn't exist.
    """
    sentinel_dir = _sentinel_dir()
    if not sentinel_dir.is_dir():
        return 0
    cutoff = (now if now is not None else time.time()) - _SENTINEL_TTL_SECONDS
    removed = 0
    try:
        entries = list(sentinel_dir.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if not entry.name.startswith(".compact-warned-"):
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def workspace_roots(cwd: Path | None = None) -> list[Path]:
    """Best-effort guess at workspace roots to scan for specs.

    Order:
    1. ``ATTUNE_AI_WORKSPACE_ROOTS`` env var
       (``os.pathsep``-separated: ``:`` on POSIX, ``;`` on Windows).
    2. The given ``cwd`` (or the process cwd).
    3. ``~/attune`` if it exists and isn't already in the list.
    """
    override = os.environ.get("ATTUNE_AI_WORKSPACE_ROOTS")
    if override:
        return [Path(p) for p in override.split(os.pathsep) if p]
    base = (cwd or Path.cwd()).resolve()
    roots: list[Path] = [base]
    home_workspace = Path.home() / "attune"
    if home_workspace.is_dir() and home_workspace.resolve() not in {r.resolve() for r in roots}:
        roots.append(home_workspace)
    return roots
