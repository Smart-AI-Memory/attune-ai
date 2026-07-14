#!/usr/bin/env python3
"""Project a feature's master file to .help kinds + docs pages.

Deterministic projection driver for the help-docs-single-source pilot
(T2). Reads ``content/features/<feature>.md`` and renders the 11
``.help`` kinds + 4 ``docs/`` pages via
``attune_author.projector`` — no LLM, no AST, no meta-templates.

Usage::

    python scripts/project_features.py <feature> [--dry-run]

Mirrors ``scripts/regenerate_help_templates.py``'s project-root
resolution: the repo root is this file's grandparent; ``help_dir`` is
``.help/``; the master file is ``content/features/<feature>.md``. The
master file is fact-checked first (warn-only — DD4); findings are
printed alongside the projection's own warnings and never block the
projection.

Specs: docs/specs/help-docs-single-source/ (design.md, decisions.md
D6/D7/D8, t2-projector-build.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Project a feature master file to .help kinds + docs pages.",
    )
    parser.add_argument(
        "feature",
        help="Feature name; reads content/features/<feature>.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the outputs and print them without writing any files.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    help_dir = repo_root / ".help"
    master_path = repo_root / "content" / "features" / f"{args.feature}.md"

    if not master_path.is_file():
        print(f"error: master file not found: {master_path}", file=sys.stderr)
        return 1

    try:
        from attune.authoring.projector import project_feature, validate_master_file
    except ImportError:
        print(
            "error: attune-author not installed "
            "(pip install -e ../attune-author or pip install attune-author).",
            file=sys.stderr,
        )
        return 1

    # Fact-check the master file before projecting (warn-only — DD4).
    try:
        findings = validate_master_file(master_path, repo_root)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: validation is advisory for the pilot; never let
        # it block the projection it precedes.
        findings = []
        print(f"warning: validation skipped: {exc}", file=sys.stderr)

    # Example-execution gate on the master file (warn-only — P5). The
    # static fact-check above proves symbols exist; this proves the
    # `python` examples are runnable (compile + no coroutine called
    # without await). See scripts/check_doc_examples.py.
    try:
        from check_doc_examples import check_file

        example_problems = check_file(master_path)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: advisory like the fact-check; never block.
        example_problems = []
        print(f"warning: example check skipped: {exc}", file=sys.stderr)

    # ``faq`` projects from the master's "## FAQ seeds" section (FG1
    # Phase 1 — seeds-only; the dynamic channels stay deferred, see
    # docs/specs/archive/help-docs-single-source/follow-ups.md).
    # ``tutorial`` needs no explicit skip: attune-author >=0.20.0 drops
    # it from DOCS_PAGE_SECTIONS by default (a guided tutorial resists
    # pure section projection — the projected version is just the Tasks
    # list verbatim, duplicating the how-to; tutorials stay
    # hand-authored per decision D10).
    result = project_feature(
        master_path,
        repo_root,
        help_dir,
        dry_run=args.dry_run,
    )

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {len(result.outputs)} output(s) for {args.feature!r}:")
    for out in result.outputs:
        rel = out.path.relative_to(repo_root) if out.path.is_relative_to(repo_root) else out.path
        print(f"  [{out.target}] {out.kind:<16} -> {rel}")

    if result.skipped:
        print(f"skipped {len(result.skipped)}:")
        for entry in result.skipped:
            print(f"  {entry}")

    warnings = (
        list(result.warnings)
        + [f"{f.check} [{f.severity}] {f.location}: {f.message}" for f in findings]
        + [f"example {p}" for p in example_problems]
    )
    if warnings:
        print(f"warnings {len(warnings)}:")
        for warning in warnings:
            print(f"  {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
