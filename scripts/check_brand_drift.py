#!/usr/bin/env python3
"""G5 — stale-brand lint + empathy ratchet (docs/specs/claim-drift-gates/).

Two tiers, one pass over TRACKED files (``git ls-files``):

1. **Hard fail, no allowlist:** the legacy identifiers
   ``empathy-framework``, ``Deep-Study-AI``, ``empathy-scan`` and the
   retired category framing ``workflow OS`` (case-insensitive;
   ratified 2026-07-29 — say "AI Workflow-harness") may not appear
   anywhere tracked, EXCEPT the documented historical surfaces
   below — they record the rebrand; scrubbing them would falsify
   history.
2. **Ratchet:** the word ``empathy`` in ``src/``,
   ``docs/getting-started/``, ``plugin/`` is frozen to the allowlist
   at ``.claude/gates/empathy-allowlist.txt`` (two tiers:
   ``# user-facing`` and ``# internal``). A file NOT on the allowlist
   gaining a match fails; an allowlisted file that no longer matches
   fails (shrink-on-fix — remove it from the list in the same
   commit). The list only shrinks.

Documented exclusions (both tiers): ``CHANGELOG.md`` (release
history), ``docs/specs/`` (decision records), ``docs/history/``
(archived reports), ``.claude/lessons.md`` (lesson corpus quotes
failures verbatim), ``website/public/`` (generated mirrors), and the
gate's own three files. Redis wire-format key prefixes
(``empathy:...`` constants) are data-format debt (P2B, next-major)
— their files sit on the internal allowlist tier, not scrubbed.

Runs keyless in < 5s; wired as pre-commit gate #9 AND rides CI's
pre-commit job (G5 is the one gate D7 keeps in pre-commit).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ALLOWLIST = REPO / ".claude" / "gates" / "empathy-allowlist.txt"

HARD_TOKENS = ("empathy-framework", "Deep-Study-AI", "empathy-scan")

#: Retired framing, hard tier via regex (ratified 2026-07-29): the
#: category term is "AI Workflow-harness"; "(developer) workflow OS"
#: may not re-enter living surfaces. Case-insensitive, tolerates a
#: hyphen or wrapped whitespace between the words; the trailing
#: boundary keeps "workflows", "OSS", "OSes" out.
HARD_PATTERNS = (("workflow OS", re.compile(r"workflow[\s-]+os\b", re.IGNORECASE)),)
RATCHET_SCOPES = ("src/", "docs/getting-started/", "plugin/")
_RATCHET_RE = re.compile(r"empathy", re.IGNORECASE)

#: Historical / self surfaces exempt from BOTH tiers (see module doc).
EXCLUDED_PREFIXES = (
    "CHANGELOG.md",
    "docs/specs/",
    "docs/history/",
    ".claude/lessons.md",
    "website/public/",
    "scripts/check_brand_drift.py",
    "tests/unit/gates/test_brand_drift.py",
    ".claude/gates/empathy-allowlist.txt",
)


def tracked_files(repo: Path = REPO) -> list[str]:
    proc = subprocess.run(  # noqa: S603 — fixed argv
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True
    )
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _excluded(rel: str) -> bool:
    return any(rel == p or rel.startswith(p) for p in EXCLUDED_PREFIXES)


def _read(repo: Path, rel: str) -> str:
    try:
        return (repo / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""  # binary or unreadable — not a claim surface


def hard_failures(files: list[str], repo: Path = REPO) -> dict[str, list[str]]:
    """rel path -> hard tokens found. Empty dict = clean."""
    hits: dict[str, list[str]] = {}
    for rel in files:
        if _excluded(rel):
            continue
        text = _read(repo, rel)
        found = [tok for tok in HARD_TOKENS if tok in text]
        found += [label for label, pattern in HARD_PATTERNS if pattern.search(text)]
        if found:
            hits[rel] = found
    return hits


def load_allowlist(path: Path = ALLOWLIST) -> dict[str, str]:
    """rel path -> tier ('user-facing' | 'internal')."""
    entries: dict[str, str] = {}
    tier = "internal"
    if not path.is_file():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#"):
            lowered = line.lstrip("# ").lower()
            if lowered in ("user-facing", "internal"):
                tier = lowered
            continue
        if line:
            entries[line] = tier
    return entries


def ratchet_check(
    files: list[str], allowlist: dict[str, str], repo: Path = REPO
) -> tuple[list[str], list[str], dict[str, int]]:
    """Returns (new_debt, stale_allowlist_entries, per-tier counts)."""
    matching = {
        rel
        for rel in files
        if rel.startswith(RATCHET_SCOPES)
        and not _excluded(rel)
        and _RATCHET_RE.search(_read(repo, rel))
    }
    new_debt = sorted(matching - set(allowlist))
    stale = sorted(set(allowlist) - matching)
    counts: dict[str, int] = {"user-facing": 0, "internal": 0}
    for rel in matching & set(allowlist):
        counts[allowlist[rel]] += 1
    return new_debt, stale, counts


def main() -> int:
    files = tracked_files()
    failed = False

    hard = hard_failures(files)
    if hard:
        failed = True
        print("HARD FAIL — legacy identifiers in tracked files (no allowlist):")
        for rel, tokens in sorted(hard.items()):
            print(f"  {rel}: {', '.join(tokens)}")

    new_debt, stale, counts = ratchet_check(files, load_allowlist())
    if new_debt:
        failed = True
        print("RATCHET FAIL — files gained 'empathy' matches (list only shrinks):")
        for rel in new_debt:
            print(f"  {rel}")
    if stale:
        failed = True
        print("RATCHET FAIL — allowlisted files no longer match; remove them:")
        for rel in stale:
            print(f"  {rel}")

    print(
        f"empathy burn-down: {counts['user-facing']} user-facing, "
        f"{counts['internal']} internal file(s) remaining"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
