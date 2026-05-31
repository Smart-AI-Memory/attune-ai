#!/usr/bin/env python3
"""Documentation wiring audit — v1 (skeleton + anchor check).

Implements Tasks 1 + 2 of
``docs/specs/docs-wiring-audit/tasks.md`` per the spec's
[design.md](../docs/specs/docs-wiring-audit/design.md).

v1 ships:

- CLI + dispatch (Task 1).
- Allowlist loader with reason-comment enforcement (Task 1).
- Markdown + JSON formatters (Task 1).
- Anchor integrity check (Task 2) — verifies every internal
  ``[text](file.md#anchor)`` and ``[text](#anchor)`` link
  resolves to a real heading anchor.

v1.1 will add nav-vs-filesystem + features.yaml checks +
mkdocstrings symbol resolution. v1.2 adds reciprocal See-Also
advisory. Each adds a new ``run_<name>_check`` function and
dispatch entry.

**Layout deviation from design.md:** the design proposed a
``scripts/audit_docs_wiring/`` package layout. v1 ships
single-file because (a) it's well under the 800-LOC threshold
the package-vs-file decision was meant to manage, and (b) the
existing ``scripts/check_help_coverage.py`` convention matches
single-file. Refactor to package when v1.1 adds the second
check and the file approaches that size.

Run:

    python scripts/audit_docs_wiring.py                # all checks
    python scripts/audit_docs_wiring.py --check anchor # one check
    python scripts/audit_docs_wiring.py --format json  # CI-shaped

Exit codes:
    0  — All requested checks passed (zero findings after allowlist).
    1  — One or more findings remain after allowlist (CI fails).
    2  — Bad invocation (unknown check name, malformed allowlist).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

__version__ = "0.1.0"

# ---------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single wiring-audit finding.

    Frozen so callers can put findings in sets / use as dict keys
    without surprise mutation.
    """

    check: str
    severity: str
    file: str
    line: int | None
    message: str
    fix: str | None = None


# ---------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Allowlist:
    """Subtree-level allowlist for orphan checks.

    Per ``docs-wiring-audit/decisions.md`` Q2: entries are
    subtree paths (trailing slash for directories, glob for
    top-level file patterns). Loaded from ``.audit/orphans.yml``;
    each entry MUST have a ``# reason:`` comment on the preceding
    line — enforced at load time.
    """

    orphan_subtrees: tuple[str, ...] = field(default_factory=tuple)

    def is_orphan_exempt(self, path: str) -> bool:
        """True if ``path`` is under any allowlisted subtree."""
        for entry in self.orphan_subtrees:
            if entry.endswith("/") and path.startswith(entry):
                return True
            if "*" in entry:
                # Glob-style match for patterns like docs/BLOG_*.md
                import fnmatch

                if fnmatch.fnmatch(path, entry):
                    return True
            if path == entry:
                return True
        return False


def load_allowlist(path: Path | None = None) -> Allowlist:
    """Load ``.audit/orphans.yml`` with reason-comment enforcement.

    The file format is intentionally a tiny YAML subset (a single
    ``orphan_subtrees:`` list) so we can parse it with stdlib
    line-walking and enforce the reason-comment rule without
    needing a YAML parser dep. Empty / missing file returns an
    empty allowlist.

    Raises:
        ValueError: when any entry lacks a ``# reason:`` comment
            on the immediately preceding non-blank line.
    """
    if path is None:
        path = Path(".audit/orphans.yml")
    if not path.exists():
        return Allowlist()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    entries: list[str] = []
    last_comment: str | None = None
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # blank line — preserve last_comment so a list entry
            # right after blanks still sees its reason
            continue
        if stripped.startswith("#"):
            last_comment = stripped
            continue
        if stripped.startswith("orphan_subtrees:"):
            in_list = True
            continue
        if in_list and stripped.startswith("- "):
            entry = stripped[2:].strip().strip("\"'")
            if last_comment is None or "reason:" not in last_comment.lower():
                raise ValueError(
                    f"Allowlist entry {entry!r} in {path} lacks a "
                    f"'# reason:' comment on the preceding line. "
                    "Every entry requires a reason."
                )
            entries.append(entry)
            last_comment = None  # consumed — next entry needs a fresh one
            continue
        # Anything else (top-level key, malformed line) ends the list block.
        in_list = False

    return Allowlist(orphan_subtrees=tuple(entries))


# ---------------------------------------------------------------------
# Slugify (mirrors Python-Markdown's toc extension default)
# ---------------------------------------------------------------------


def slugify(text: str, separator: str = "-") -> str:
    """Slugify a heading to its anchor form.

    Matches Python-Markdown's ``markdown.extensions.toc.slugify``
    so anchor links in docs resolve the same way mkdocs would
    resolve them at build time. We mirror the algorithm inline
    instead of importing ``markdown`` to keep this script
    stdlib-only.

    Args:
        text: The heading text (without the leading ``#`` markers).
        separator: Separator character used between words.

    Returns:
        Slugified anchor string suitable for ``#anchor`` links.
    """
    # Normalize to NFKD and drop non-ASCII (matches Python-Markdown).
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Strip everything that isn't word-char, whitespace, or dash.
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    # Collapse runs of whitespace OR the separator into a single separator.
    return re.sub(rf"[{re.escape(separator)}\s]+", separator, value)


# ---------------------------------------------------------------------
# Anchor integrity check
# ---------------------------------------------------------------------

# Markdown heading patterns. ATX-style: # / ## / ### headers.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# Inline link: [text](url "optional title"). url captured greedily up
# to the closing paren or whitespace.
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _extract_headings(text: str) -> set[str]:
    """Return the set of slugified anchors for a markdown document."""
    anchors: set[str] = set()
    for match in _HEADING_RE.finditer(text):
        heading_text = match.group(2)
        # Strip trailing # marks (e.g. "## Section ##")
        heading_text = re.sub(r"\s+#+\s*$", "", heading_text)
        anchors.add(slugify(heading_text))
    return anchors


def _compute_line_starts(text: str) -> list[int]:
    """Return byte offsets where each line begins (0-indexed positions).

    Index 0 is always 0; subsequent entries are offsets immediately
    after each ``\\n``. Used by ``_offset_to_line`` for O(log n)
    line-number lookup.
    """
    line_starts = [0]
    for i, char in enumerate(text):
        if char == "\n":
            line_starts.append(i + 1)
    return line_starts


def _offset_to_line(line_starts: list[int], offset: int) -> int:
    """1-indexed line number containing ``offset``.

    Uses binary search over the pre-computed ``line_starts`` list
    (built by ``_compute_line_starts``). Lifted to module scope
    instead of a per-loop closure so ruff's B023 (loop-variable
    capture) doesn't false-positive on the safe inner-loop use.
    """
    return bisect.bisect_right(line_starts, offset)


def _is_external_link(url: str) -> bool:
    """True if the link should be skipped (external, mailto, cross-repo)."""
    if url.startswith(("http://", "https://", "mailto:", "ftp://")):
        return True
    return False


def _resolve_target_file(
    link_url: str,
    source_file: Path,
    docs_root: Path,
) -> Path | None:
    """Resolve ``[text](file.md#anchor)`` to an absolute file path.

    Returns ``None`` for intra-page links (no file part) — caller
    handles those by checking the source file's own headings.
    """
    # Strip the anchor portion to get just the file path.
    file_part = link_url.split("#", 1)[0]
    if not file_part:
        # Intra-page link: [text](#anchor)
        return None
    # Relative to the source file's directory.
    candidate = (source_file.parent / file_part).resolve()
    # Refuse to follow links outside docs/ (e.g. ../../src/foo.py).
    try:
        candidate.relative_to(docs_root.resolve())
    except ValueError:
        return None
    return candidate


def check_anchors(docs_root: Path) -> list[Finding]:
    """Walk docs/**/*.md and verify every internal anchor link resolves.

    Implements design.md §3a. Skips external links and refuses to
    follow links pointing outside ``docs_root``.

    Args:
        docs_root: Path to the docs root (typically ``Path("docs")``).

    Returns:
        List of ``Finding`` records — one per broken anchor.
    """
    findings: list[Finding] = []
    if not docs_root.is_dir():
        return findings

    # Pre-compute heading sets for every .md so we don't re-read.
    heading_cache: dict[Path, set[str]] = {}
    for md in docs_root.rglob("*.md"):
        try:
            heading_cache[md.resolve()] = _extract_headings(md.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            # Skip unreadable files; not a wiring issue.
            continue

    for md in sorted(docs_root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        line_starts = _compute_line_starts(text)

        for match in _LINK_RE.finditer(text):
            url = match.group(2)
            if _is_external_link(url):
                continue
            if "#" not in url:
                # Not an anchor link; nav/filesystem check (future
                # v1.1 task) handles file-existence verification.
                continue

            anchor = url.split("#", 1)[1]
            if not anchor:
                # [text](file.md#) — empty anchor; skip
                continue

            # Distinguish intra-page (#anchor) from outside-docs
            # (../../src/foo.py#L42). Both are caught by the resolver
            # returning None, but only the former should be checked
            # against the source file's headings.
            file_part = url.split("#", 1)[0]
            target_file = _resolve_target_file(url, md, docs_root)
            if target_file is None and file_part:
                # Resolved file landed outside docs/ — skip; not our scope.
                continue
            if target_file is None:
                # Intra-page anchor — check against this file's headings
                target_anchors = heading_cache.get(md.resolve(), set())
                target_label = str(md.relative_to(docs_root.parent))
            else:
                target_anchors = heading_cache.get(target_file)
                if target_anchors is None:
                    # Link points at a file we couldn't read or that
                    # doesn't exist. Nav-vs-filesystem check (v1.1)
                    # owns file-existence; skip here to avoid double-
                    # reporting.
                    continue
                target_label = str(target_file.relative_to(docs_root.parent.resolve()))

            if anchor in target_anchors:
                continue

            # Build a "did-you-mean" hint listing up to 3 nearby headings.
            sample = sorted(target_anchors)[:5] if target_anchors else []
            hint = (
                f"available anchors in {target_label}: {', '.join(sample)}"
                if sample
                else f"target file has no headings ({target_label})"
            )
            findings.append(
                Finding(
                    check="anchor",
                    severity="error",
                    file=str(md.relative_to(docs_root.parent)),
                    line=_offset_to_line(line_starts, match.start()),
                    message=(f"Link target '#{anchor}' not found in {target_label} " f"({hint})"),
                    fix=(
                        "Update link to match an existing heading, or rename "
                        "the heading and update inbound links (see "
                        "docs-wiring-audit/decisions.md Q1 — update inbound "
                        "links, no redirect)."
                    ),
                )
            )

    return findings


# ---------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------


def format_markdown(findings: list[Finding]) -> str:
    """Render findings as a human-readable markdown report."""
    if not findings:
        return "No findings."

    parts: list[str] = ["# Docs wiring audit\n"]
    parts.append(f"Total findings: **{len(findings)}**\n")

    # Group by check.
    by_check: dict[str, list[Finding]] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)

    for check, items in sorted(by_check.items()):
        parts.append(f"\n## {check} ({len(items)})\n")
        parts.append("| File | Line | Severity | Message | Fix |")
        parts.append("|---|---|---|---|---|")
        for f in items:
            line_str = str(f.line) if f.line else "—"
            fix_str = f.fix or "—"
            # Escape pipes inside table cells.
            msg = f.message.replace("|", "\\|")
            fix_str = fix_str.replace("|", "\\|")
            parts.append(f"| `{f.file}` | {line_str} | {f.severity} | {msg} | {fix_str} |")

    return "\n".join(parts) + "\n"


def format_json(findings: list[Finding]) -> str:
    """Render findings as JSON for CI consumption."""
    return json.dumps(
        {"findings": [asdict(f) for f in findings]},
        indent=2,
        sort_keys=True,
    )


# ---------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------

CHECKS = {
    "anchor": check_anchors,
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="audit_docs_wiring",
        description=(
            "Audit docs/ wiring (anchors, nav, features.yaml, "
            "mkdocstrings). v1 ships anchor check; nav + features.yaml "
            "+ mkdocstrings land in v1.1; reciprocal See-Also in v1.2."
        ),
    )
    parser.add_argument(
        "--check",
        choices=sorted(CHECKS.keys()) + ["all"],
        default="all",
        help="Which check to run. Default: all available.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path("docs"),
        help="Path to the docs root. Default: docs",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path(".audit/orphans.yml"),
        help="Path to the orphan allowlist. Default: .audit/orphans.yml",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    """Top-level entry point. Returns the exit code."""
    args = _parse_args(argv)

    # Allowlist load — fails early on missing reason comments.
    try:
        load_allowlist(args.allowlist)
    except ValueError as exc:
        print(f"Allowlist error: {exc}", file=sys.stderr)
        return 2

    # Dispatch.
    requested = sorted(CHECKS.keys()) if args.check == "all" else [args.check]
    all_findings: list[Finding] = []
    for name in requested:
        check_fn = CHECKS[name]
        all_findings.extend(check_fn(args.docs_root))

    # Emit.
    if args.format == "json":
        print(format_json(all_findings))
    else:
        print(format_markdown(all_findings))

    return 1 if all_findings else 0


if __name__ == "__main__":
    sys.exit(run())
