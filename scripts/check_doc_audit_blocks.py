#!/usr/bin/env python3
"""Pre-commit reader: flag unresolved cross-reference links in docs.

attune-author's polish pass appends a ``## Unresolved references``
audit table to generated docs, flagging body links whose targets
don't exist (LLM-hallucinated cross-refs — shape #3 in the
"polish-pass hallucinations" lesson). The signal is already in the
file; nothing in attune-ai read it, so we only found breakage when
``mkdocs --strict`` failed on CI. This reads the audit block at the
attune-author -> attune-ai boundary and surfaces broken links before
they land. See ``docs/specs/docs-link-prevalidation/``.

v1 is **warn mode**: prints findings, exits 0 (DECIDE-1 — promote to
exit-non-zero after a release cycle). A file-level override comment
``<!-- attune-skip-link-check: <reason> -->`` skips a file.

stdlib only. Usage: ``python scripts/check_doc_audit_blocks.py <files...>``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

# The audit block: a "## Unresolved references" heading, extending to
# the next "## " heading or EOF (same extraction shape as
# spec-status-self-truthing's checklist reader).
_AUDIT_HEADING = re.compile(
    r"^##\s+Unresolved\s+references\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_NEXT_H2 = re.compile(r"^##\s+", re.MULTILINE)

# A table row: "| Line 96 | error | <issue> |" — the Location cell may
# carry a suffix like "Line 7 (code fence)", so allow non-pipe text
# after the digits before the next column separator.
_AUDIT_ROW = re.compile(
    r"^\|\s*Line\s+(\d+)[^|]*\|\s*(error|warning|info)\s*\|\s*(.*?)\s*\|\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# File-level override (DECIDE-2): an inline HTML comment with a reason.
_OVERRIDE = re.compile(
    r"<!--\s*attune-skip-link-check\s*:\s*(.+?)\s*-->",
    re.IGNORECASE | re.DOTALL,
)

# Issue text that marks a row as a broken *link* (vs. a broken import
# or other audit finding, which are out of scope for v1).
_BROKEN_LINK_MARKERS = (
    "target does not exist",
    "not found among documentation files",
)


@dataclass(frozen=True)
class BrokenLink:
    """One broken cross-reference flagged by an audit block."""

    line: int
    issue: str


def override_reason(text: str) -> str | None:
    """Return the skip reason if a valid override comment is present."""
    match = _OVERRIDE.search(text)
    if match is None:
        return None
    reason = match.group(1).strip()
    return reason or None


def find_broken_links(text: str) -> list[BrokenLink]:
    """Parse the audit block and return only the broken-link rows.

    Returns ``[]`` when there's no audit block or no broken-link rows.
    Broken *imports* / other error rows are parsed but not returned —
    they're different hallucination shapes, out of scope for v1.
    """
    heading = _AUDIT_HEADING.search(text)
    if heading is None:
        return []
    next_h2 = _NEXT_H2.search(text, heading.end())
    block = text[heading.end() : (next_h2.start() if next_h2 else len(text))]

    results: list[BrokenLink] = []
    for row in _AUDIT_ROW.finditer(block):
        line_no, severity, issue = row.group(1), row.group(2), row.group(3)
        if severity.lower() != "error":
            continue
        lowered = issue.lower()
        if not any(marker in lowered for marker in _BROKEN_LINK_MARKERS):
            continue
        results.append(BrokenLink(line=int(line_no), issue=issue.strip()))
    return results


def _report(path: str, links: list[BrokenLink]) -> None:
    print(f"{path}:")
    for link in links:
        print(f"  Line {link.line}: error — {link.issue}")
    print("  Suggested fixes:")
    print("    - Remove the bullet/sentence containing the bad link")
    print("    - Replace with a working link if one exists")
    print("    - Add `<!-- attune-skip-link-check: <reason> -->` to override")


def main(argv: list[str]) -> int:
    """Check each passed file; warn-mode (always exit 0 in v1)."""
    total_findings = 0
    for path in argv:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            # Never fail the commit over an unreadable file — skip it.
            print(f"{path}: skipped (unreadable: {exc})", file=sys.stderr)
            continue

        reason = override_reason(text)
        if reason is not None:
            print(f"{path}: skipped per override: {reason}")
            continue

        links = find_broken_links(text)
        if links:
            _report(path, links)
            total_findings += len(links)

    if total_findings:
        # v1 warn mode (DECIDE-1): surface, don't block. Promote to
        # `return 1` here after the warn-mode release cycle.
        print(
            f"\n[warn] {total_findings} unresolved doc link(s) flagged. "
            "Not blocking (warn mode); fix or override before they reach "
            "mkdocs --strict.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
