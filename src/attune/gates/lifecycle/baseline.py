"""The mandatory mechanical baseline gates (spec-lifecycle-gates RR-4).

Three fully-autonomous gates, each returning a :class:`GateReceipt`:

- **format-lint** — the round-table compiler lints, called directly
  (never re-implemented).
- **symbol-reality** — every path/module a document cites must
  resolve against the tree. Born from live evidence: the drafter of
  this very spec confabulated seven module paths in its first
  producing run (decisions.md, 2026-07-19).
- **falsifiability** — acceptance bullets must name a receipt type
  or a probe that would fail; "configured/registered/exits-0"
  phrasings are flagged (the "registered ≠ working" lesson,
  mechanized).

CI enforcers (rules-residency, complexity ratchet, lessons
golden-smoke, doc-import audit) are CITED by the ladder, not wrapped
here — they keep failing CI directly (design ruling).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from attune.roundtable import compiler

from .protocol import GateReceipt

#: `[[?slug]]`-style annotation marking a deliberately-not-yet-built
#: symbol (the memory-corpus escape hatch, ported per RR-4).
_NOT_YET_RE = re.compile(r"\[\[\?[\w./-]+\]\]")

#: Backticked tokens that look like paths (contain a slash or end in
#: .py/.md) or importable dotted modules under the attune namespace.
_PATH_TOKEN_RE = re.compile(r"`([\w./~-]+/[\w./~-]+|[\w./-]+\.(?:py|md))`")
_MODULE_TOKEN_RE = re.compile(r"`(attune(?:\.\w+)+)`")

#: Receipt-type vocabulary a falsifiable acceptance bullet may name
#: (the delegation-receipts taxonomy) plus probe-ish words.
_RECEIPT_WORDS_RE = re.compile(
    r"\b(suite|behavioral|live-fire|metric|evidence-chain|test|probe|assert|"
    r"exit[s]? non-zero|fails?\b)",
    re.IGNORECASE,
)
_BANNED_PHRASES_RE = re.compile(
    r"\b(configured|registered|wired up|exits? 0|exits? successfully)\b",
    re.IGNORECASE,
)


def format_lint_gate(document: str, kind: str, *, phase: str, target: str) -> GateReceipt:
    """Run the round-table compiler lint for ``kind`` (draft/critique/final)."""
    lint = getattr(compiler, f"lint_{kind}")
    problems = lint(document)
    return GateReceipt(
        gate_id="format-lint",
        phase=phase,
        target=target,
        state="REVISE" if problems else "PASS",
        findings=list(problems),
        proposed_disposition="return to author seat" if problems else "proceed",
    )


def _resolves(token: str, roots: tuple[Path, ...]) -> bool:
    if token.startswith("~"):
        # Runtime home-dir data path (a config convention, not a repo
        # citation) — exempt; the tree cannot vouch for user state.
        return True
    if "/" in token or token.endswith((".py", ".md")):
        return any((root / token).exists() for root in roots)
    try:
        return importlib.util.find_spec(token) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def symbol_reality_gate(
    document: str,
    project_root: Path,
    *,
    phase: str,
    target: str,
    extra_roots: tuple[Path, ...] = (),
) -> GateReceipt:
    """Every cited path/module resolves, or the gate blocks (RR-4).

    Resolution tries ``project_root``, any ``extra_roots`` (the
    runner passes the spec dir, so ``decisions.md``-style relative
    citations resolve), and the repo-idiomatic ``src/attune``
    prefix (prose cites ``ops/runner.py`` for
    ``src/attune/ops/runner.py``). Tokens covered by a ``[[?slug]]``
    not-yet-built annotation on the same line are exempt — the
    deliberate-future-work escape hatch. ``~``-prefixed runtime data
    paths are exempt (live-fire finding, T4).
    """
    roots = (project_root, *extra_roots, project_root / "src", project_root / "src" / "attune")
    missing: list[str] = []
    checked = 0
    for line in document.splitlines():
        if _NOT_YET_RE.search(line):
            continue
        tokens = _PATH_TOKEN_RE.findall(line) + _MODULE_TOKEN_RE.findall(line)
        for token in tokens:
            checked += 1
            if not _resolves(token, roots):
                missing.append(token)
    state = "BLOCKED" if missing else "PASS"
    return GateReceipt(
        gate_id="symbol-reality",
        phase=phase,
        target=target,
        state=state,
        findings=[f"cited but unresolvable: {m}" for m in dict.fromkeys(missing)],
        evidence_refs=[f"checked {checked} cited tokens against {project_root}"],
        proposed_disposition=(
            "re-ground every citation before this document advances" if missing else "proceed"
        ),
    )


def falsifiability_gate(document: str, *, phase: str, target: str) -> GateReceipt:
    """Acceptance bullets carry a receipt type or failing probe (RR-4)."""
    findings: list[str] = []
    for line in document.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        banned = _BANNED_PHRASES_RE.search(stripped)
        if banned and not _RECEIPT_WORDS_RE.search(stripped):
            findings.append(
                f"unfalsifiable phrasing ({banned.group(0)!r}) with no receipt/probe: "
                f"{stripped[:80]!r}"
            )
    return GateReceipt(
        gate_id="falsifiability",
        phase=phase,
        target=target,
        state="REVISE" if findings else "PASS",
        findings=findings,
        proposed_disposition=(
            "name a receipt type or failing probe per flagged bullet" if findings else "proceed"
        ),
    )
