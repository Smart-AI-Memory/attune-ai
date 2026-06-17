#!/usr/bin/env python3
"""Spec status audit — flag specs whose deliverables shipped but status didn't.

On-demand / CI companion to the always-on ``spec_orient`` SessionStart
hint. Discovers every spec (including terminal ones), classifies each
against its declared ``## Deliverables`` block, and prints a matrix:

    Spec | Layer | Status | Staleness | Unresolved

D-7 — **warn by default, gate opt-in.** Exits ``0`` even when stale
specs exist; ``--strict`` exits ``1`` on any ``suspected-stale`` so a
repo can wire a hard CI gate. Crash-proof: any unexpected error prints
what we have and still exits ``0`` (warn-by-default never hard-fails).

Run via ``make spec-audit`` or ``python plugin/hooks/spec_audit.py``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

# Force utf-8 on stdout/stderr — the table uses ⚠ and an em-dash rule
# that Windows cp1252 can't encode (matches spec_orient.py).
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Hooks are invoked as standalone scripts; ensure sibling helpers resolve.
_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _state import (  # noqa: E402 — sys.path bootstrap above
    _resolve_entry,
    discover_specs,
    workspace_roots,
)

# Display order — suspected-stale rows surface first; ``ok`` sinks last.
_STALENESS_ORDER = {
    "suspected-stale": 0,
    "partial": 1,
    "unknown": 2,
    "docs-only": 3,
    "opted-out": 4,
    "ok": 5,
}
# Only suspected-stale gets a glyph; the rest render verbatim.
_STALENESS_LABEL = {"suspected-stale": "⚠ suspected-stale"}

_HEADERS = ("Spec", "Layer", "Status", "Staleness", "Unresolved")


@dataclass(frozen=True)
class AuditResult:
    """One spec's audit row."""

    slug: str
    layer: str
    status: str
    staleness: str
    resolved: int  # entries that resolve on disk
    total: int  # entries declared


def audit_specs(roots: list[Path] | None = None) -> list[AuditResult]:
    """Classify every discovered spec (terminal included) into a row.

    Resolution counts are recomputed per spec so the report can show how
    many declared deliverables are present. Per-spec failures degrade to
    a zero-count row rather than aborting the whole audit.
    """
    if roots is None:
        roots = workspace_roots()
    results: list[AuditResult] = []
    for spec in discover_specs(roots, include_terminal=True):
        total = len(spec.deliverables)
        resolved = 0
        # Counts only matter where resolution actually ran (partial shows
        # "N of M"; suspected-stale/ok are all-resolve by definition).
        if total and spec.staleness in ("partial", "suspected-stale", "ok"):
            try:
                resolved = sum(1 for e in spec.deliverables if _resolve_entry(e, roots))
            except Exception:  # noqa: BLE001 — one bad spec must not abort the audit
                resolved = 0
        results.append(
            AuditResult(
                slug=spec.slug,
                layer=spec.layer,
                status=spec.status or "—",
                staleness=spec.staleness,
                resolved=resolved,
                total=total,
            )
        )
    return results


def _truncate(text: str, limit: int) -> str:
    """Clip ``text`` to ``limit`` chars, ellipsizing the overflow."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _detail(result: AuditResult) -> str:
    """Render the ``Unresolved`` column for one row."""
    if result.staleness == "opted-out":
        return "(opt-out)"
    if result.staleness == "docs-only":
        return "(N/A)"
    if result.staleness == "unknown":
        return "(no block)" if result.total == 0 else f"0 of {result.total}"
    if result.staleness == "partial":
        return f"{result.total - result.resolved} of {result.total}"
    # suspected-stale / ok — every declared deliverable resolves.
    return "—"


def format_report(results: list[AuditResult]) -> str:
    """Render the full audit matrix as a string."""
    stale = [r for r in results if r.staleness == "suspected-stale"]
    noun = "spec" if len(results) == 1 else "specs"
    title = f"SPEC STATUS AUDIT — {len(results)} {noun} ({len(stale)} suspected-stale)"
    if not results:
        return f"{title}\n\n(no specs found)"

    ordered = sorted(results, key=lambda r: (_STALENESS_ORDER.get(r.staleness, 9), r.slug))
    rows = [
        (
            _truncate(r.slug, 44),
            _truncate(r.layer, 14),
            # Status lines are written informatively and can run to a
            # whole paragraph — truncate so one long status doesn't blow
            # the column out (e.g. integration-coverage's 1k-char line).
            _truncate(r.status, 32),
            _STALENESS_LABEL.get(r.staleness, r.staleness),
            _detail(r),
        )
        for r in ordered
    ]
    widths = [max(len(_HEADERS[i]), *(len(row[i]) for row in rows)) for i in range(len(_HEADERS))]

    def _line(cells: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    out = [title, "", _line(_HEADERS), "─" * len(_line(_HEADERS))]
    out.extend(_line(row) for row in rows)
    out.append("")
    if stale:
        out.append(
            f"⚠ {len(stale)} spec(s) have shipped deliverables but a "
            "non-terminal status — verify & update."
        )
    else:
        out.append("✓ No suspected-stale specs.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """Print the audit matrix; exit per ``--strict``. Never hard-crashes."""
    try:
        args = sys.argv[1:] if argv is None else argv
        strict = "--strict" in args
        results = audit_specs()
        print(format_report(results))
        if strict and any(r.staleness == "suspected-stale" for r in results):
            return 1
        return 0
    except Exception:  # noqa: BLE001 — warn-by-default: report and exit 0
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
