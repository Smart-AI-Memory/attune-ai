#!/usr/bin/env python3
"""Polish-master action — LLM polish on a single-source master, as a diff.

The D10 wiring (docs/specs/attune-author-consolidation/): LLM polish is
preserved but runs at *authoring time on the master*
(``content/features/<slug>.md``), never on projected output. This script
is the reviewable form of that action: it runs the absorbed polish pass
(:mod:`attune.authoring.polish`, LLM calls via
:mod:`attune.models.single_turn` — tier-routed, subscription-first) and
prints a unified diff against the current master. Nothing is written
unless ``--apply`` is passed; the driving session (or the human) reviews
the diff and judges it — the session stays the polish layer of record.

Cost note: one premium-tier LLM call per run (subscription-first; API
fallback when ``ANTHROPIC_API_KEY`` is set). Results are cached in
``~/.attune/polish_cache`` keyed on content+prompt, so re-running on an
unchanged master is free.

Usage::

    PYTHONPATH=src python scripts/polish_master.py <feature-slug>
    PYTHONPATH=src python scripts/polish_master.py <feature-slug> --apply
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def polish_master(slug: str, *, apply: bool = False) -> int:
    """Polish one master and print the reviewable diff.

    Args:
        slug: Feature slug — the master is
            ``content/features/<slug>.md``.
        apply: Write the polished master back in place. Default is
            diff-only.

    Returns:
        Process exit code: 0 on success (including a no-change
        polish), 1 on a missing master or polish failure.
    """
    import yaml

    from attune.authoring.generator import _extract_source_info, _maybe_polish
    from attune.authoring.manifest import Feature
    from attune.authoring.staleness import compute_source_hash

    master = REPO_ROOT / "content" / "features" / f"{slug}.md"
    if not master.is_file():
        print(f"error: no master at {master}", file=sys.stderr)
        return 1

    text = master.read_text(encoding="utf-8")
    if not text.startswith("---"):
        print("error: master has no YAML frontmatter", file=sys.stderr)
        return 1
    _, frontmatter, _body = text.split("---", 2)
    meta = yaml.safe_load(frontmatter) or {}

    feature = Feature(
        name=slug,
        description=str(meta.get("summary", "")),
        files=list(meta.get("source_globs", [])),
        tags=list(meta.get("tags", [])),
    )
    _, matched_files = compute_source_hash(feature, REPO_ROOT)
    source_info = _extract_source_info(matched_files, REPO_ROOT)

    from attune.authoring.polish import PolishError

    try:
        polished = _maybe_polish(
            text,
            feature,
            source_info,
            template_type="generic",
            matched_files=matched_files,
            project_root=REPO_ROOT,
        )
    except PolishError as exc:
        print(f"error: polish failed: {exc}", file=sys.stderr)
        return 1

    if polished == text:
        print(f"{slug}: polish produced no changes")
        return 0

    diff = difflib.unified_diff(
        text.splitlines(keepends=True),
        polished.splitlines(keepends=True),
        fromfile=f"content/features/{slug}.md",
        tofile=f"content/features/{slug}.md (polished)",
    )
    sys.stdout.writelines(diff)

    if apply:
        master.write_text(polished, encoding="utf-8")
        print(f"\napplied to {master.relative_to(REPO_ROOT)}")
        print("review the diff above, then re-run the projection gates")
    else:
        print("\n(diff only — re-run with --apply to write the master)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("slug", help="feature slug (content/features/<slug>.md)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the polished master in place (default: diff only)",
    )
    args = parser.parse_args(argv)
    return polish_master(args.slug, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
