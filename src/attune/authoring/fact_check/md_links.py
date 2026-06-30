"""Check relative markdown link targets exist.

For each ``[label](target)`` reference in the polished file:
- If ``target`` looks like an external URL or mailto, skip.
- Otherwise resolve relative to the polished file's directory
  and assert the target file exists.

Anchor existence is out of scope for Phase 1 per spec §1.5.
"""

from __future__ import annotations

import re
from pathlib import Path

from .report import CHECK_MD_LINKS, Finding

#: Match inline markdown links ``[label](target)``. Captures
#: the target. Greedy-safe (no nested parens supported, which
#: is fine for our doc style).
_LINK = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)\)")

#: Skip anything that looks like a URL or a non-file scheme.
_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|mailto:|#)", re.IGNORECASE)


def check(polished_path: Path) -> list[Finding]:
    """Run the md-links check on ``polished_path``."""
    text = polished_path.read_text(encoding="utf-8")
    base = polished_path.parent
    findings: list[Finding] = []
    seen: set[str] = set()

    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _LINK.finditer(line):
            target = match.group("target")
            if _EXTERNAL.match(target):
                continue
            # Strip in-document anchors — out of scope for existence.
            target_path_str = target.split("#", 1)[0]
            if not target_path_str:
                # Pure ``#anchor`` link — same file, skip.
                continue
            if target_path_str in seen:
                continue
            seen.add(target_path_str)

            resolved = (base / target_path_str).resolve()
            if not resolved.exists():
                findings.append(
                    Finding(
                        check=CHECK_MD_LINKS,
                        severity="error",
                        location=f"Line {lineno}",
                        message=f"`[{match.group('label')}]({target})` — target does not exist",
                    )
                )

    return findings


__all__ = ["check"]
