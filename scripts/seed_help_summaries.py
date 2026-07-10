#!/usr/bin/env python3
"""Seed .help/summaries.json from template bodies (no LLM, no spend).

Walks ``.help/templates/**/*.md``, extracts each template's first prose
sentence, and writes a path-keyed sidecar per ADR-004 (attune workspace
tech.md)::

    { "cli/concept.md": "One-line summary.", ... }

Keys are template paths relative to ``.help/templates/`` — the shape
attune-rag's ``DirectoryCorpus`` consumes (the retriever applies a 1.5x
boost on summary matches) and the attune-gui Summaries page edits.

NOT covered: attune-help's ``HelpEngine`` reads a *slug-keyed*
``summaries.json`` from its own generated dir — a different file and
schema; seed that separately if needed.

Existing entries are preserved by default (hand edits from the GUI
Summaries page win over mechanical extraction); pass ``--force`` to
regenerate everything.

Usage:
    python scripts/seed_help_summaries.py [--help-dir .help] [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Cap a summary at roughly one display line; hard stop well before the
# GUI's card layout truncates.
_MAX_CHARS = 200

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_ORDERED_ITEM = re.compile(r"^\s*\d{1,3}[.)]\s*")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_INLINE_CODE = re.compile(r"`([^`]*)`")
# Deliberately NOT stripping single underscores: they're emphasis only at
# word boundaries in markdown, but intra-word in identifiers
# (route_user_input) — stripping them mangles code names.
_EMPHASIS = re.compile(r"(\*\*|\*|__)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block if present."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :]


def _first_prose_paragraph(body: str) -> str | None:
    """Return the first paragraph that is plain prose.

    Skips headings, code fences (and their contents), tables, list
    markers, and blank lines — the goal is the template's lead
    sentence, which the generated templates consistently open with
    right after the H1.
    """
    body = _HTML_COMMENT.sub("", body)
    lines = body.splitlines()
    in_fence = False
    in_block = False  # consuming a list/table/quote incl. wrapped lines
    para: list[str] = []
    first_item: list[str] = []  # fallback: first list item's own text
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped:
            if para:
                break
            in_block = False
            continue
        is_item = _ORDERED_ITEM.match(line) or stripped.startswith(("- ", "* ", "+ "))
        if _HEADING.match(line) or is_item or stripped.startswith(("|", ">")):
            if para:
                break
            if is_item and not first_item:
                first_item.append(_ORDERED_ITEM.sub("", stripped).lstrip("-*+ "))
            in_block = True
            continue
        if in_block:
            # Wrapped continuation of a skipped list item / table row.
            if first_item and len(first_item) < 3:
                first_item.append(stripped)  # finish the fallback item
            continue
        para.append(stripped)
    # Prefer real prose; fall back to the first list item (error/warning/
    # troubleshooting templates open with a numbered symptom list).
    chosen = para or first_item
    if not chosen:
        return None
    return " ".join(chosen)


def _to_summary(paragraph: str) -> str:
    """Collapse markdown syntax and cut at the first sentence boundary."""
    text = _MD_LINK.sub(r"\1", paragraph)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _EMPHASIS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = _SENTENCE_END.split(text, maxsplit=1)
    summary = parts[0].strip()
    if len(summary) > _MAX_CHARS:
        summary = summary[: _MAX_CHARS - 1].rstrip() + "…"
    return summary


def seed(help_dir: Path, *, force: bool = False) -> tuple[dict[str, str], int, int]:
    """Build the summaries mapping for ``help_dir``.

    Returns ``(mapping, n_new, n_kept)``. Existing entries are kept
    unless ``force`` — the GUI Summaries page lets humans refine
    entries, and a reseed must not clobber that work.
    """
    templates_root = help_dir / "templates"
    if not templates_root.is_dir():
        raise SystemExit(f"no templates directory at {templates_root}")

    sidecar = help_dir / "summaries.json"
    existing: dict[str, str] = {}
    if sidecar.is_file() and not force:
        try:
            loaded = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = {str(k): str(v) for k, v in loaded.items() if v}
        except (json.JSONDecodeError, OSError):
            pass  # unreadable sidecar: rebuild from scratch

    mapping: dict[str, str] = {}
    n_new = n_kept = 0
    for md in sorted(templates_root.rglob("*.md")):
        key = md.relative_to(templates_root).as_posix()
        if key in existing:
            mapping[key] = existing[key]
            n_kept += 1
            continue
        body = _strip_frontmatter(md.read_text(encoding="utf-8"))
        paragraph = _first_prose_paragraph(body)
        if paragraph is not None:
            mapping[key] = _to_summary(paragraph)
        else:
            # Pure table/code templates (typically reference.md): synthesize
            # from the path so the retriever still gets a summary token hit.
            feature = md.parent.name
            kind = md.stem
            mapping[key] = f"{feature} {kind} — tables and signatures for the {feature} feature."
        n_new += 1
    return mapping, n_new, n_kept


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--help-dir",
        type=Path,
        default=Path(".help"),
        help="Workspace help directory (default: .help)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate every entry, discarding hand edits",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the would-be JSON to stdout without writing",
    )
    args = parser.parse_args(argv)

    mapping, n_new, n_kept = seed(args.help_dir, force=args.force)
    payload = json.dumps(mapping, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.dry_run:
        sys.stdout.write(payload)
    else:
        (args.help_dir / "summaries.json").write_text(payload, encoding="utf-8")
    print(
        f"{len(mapping)} entries ({n_new} generated, {n_kept} kept) "
        f"-> {args.help_dir / 'summaries.json'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
