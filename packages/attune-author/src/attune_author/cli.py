"""CLI entry point for attune-author.

Provides commands for help system initialization, staleness
checking, template generation, and document generation.

Usage:
    attune-author init              # Bootstrap .help/
    attune-author status            # Show staleness report
    attune-author generate <feat>   # Generate templates
    attune-author regenerate        # Regenerate stale
    attune-author docs <path>       # Generate docs (AI)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        prog="attune-author",
        description="Documentation authoring and maintenance for the attune ecosystem.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = sub.add_parser("init", help="Initialize .help/ in the current project")
    p_init.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory).",
    )

    # status
    p_status = sub.add_parser("status", help="Show staleness report")
    p_status.add_argument(
        "--help-dir",
        default=".help",
        help="Path to .help/ directory.",
    )
    p_status.add_argument(
        "--project-root",
        default=".",
        help="Project root directory.",
    )

    # generate
    p_gen = sub.add_parser("generate", help="Generate templates for a feature")
    p_gen.add_argument("feature", help="Feature name to generate.")
    p_gen.add_argument(
        "--help-dir",
        default=".help",
        help="Path to .help/ directory.",
    )
    p_gen.add_argument(
        "--project-root",
        default=".",
        help="Project root directory.",
    )
    p_gen.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite manual templates.",
    )

    # regenerate
    p_regen = sub.add_parser("regenerate", help="Regenerate all stale templates")
    p_regen.add_argument(
        "--help-dir",
        default=".help",
        help="Path to .help/ directory.",
    )
    p_regen.add_argument(
        "--project-root",
        default=".",
        help="Project root directory.",
    )
    p_regen.add_argument(
        "--dry-run",
        action="store_true",
        help="Report stale features without regenerating.",
    )

    # docs
    p_docs = sub.add_parser("docs", help="Generate docs from source (requires [ai])")
    p_docs.add_argument("target", help="Source file or module to document.")
    p_docs.add_argument(
        "--output",
        "-o",
        help="Output file path.",
    )
    p_docs.add_argument(
        "--doc-type",
        default="api-reference",
        help="Documentation type (default: api-reference).",
    )
    p_docs.add_argument(
        "--audience",
        default="developers",
        help="Target audience (default: developers).",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "init":
            return _cmd_init(args)
        elif args.command == "status":
            return _cmd_status(args)
        elif args.command == "generate":
            return _cmd_generate(args)
        elif args.command == "regenerate":
            return _cmd_regenerate(args)
        elif args.command == "docs":
            return _cmd_docs(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    """Handle the init command."""
    from attune_author.bootstrap import proposals_to_manifest, scan_project
    from attune_author.manifest import save_manifest

    root = Path(args.project_root).resolve()
    help_dir = root / ".help"

    if (help_dir / "features.yaml").exists():
        print(f"Already initialized: {help_dir / 'features.yaml'}")
        return 0

    print(f"Scanning {root}...")
    proposals = scan_project(root)

    if not proposals:
        print("No features discovered. Create .help/features.yaml manually.")
        return 0

    print(f"\nDiscovered {len(proposals)} features:\n")
    for p in proposals:
        conf = {"high": "+", "medium": "~", "low": "?"}
        marker = conf.get(p.confidence, "?")
        print(f"  [{marker}] {p.name} — {p.description}")
        print(f"      files: {', '.join(p.files)}")

    # Convert all proposals to manifest
    manifest = proposals_to_manifest(proposals)
    path = save_manifest(manifest, help_dir)
    print(f"\nSaved {len(proposals)} features to {path}")
    print("Edit .help/features.yaml to refine, then run: attune-author generate <feature>")

    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Handle the status command."""
    from attune_author.maintenance import format_status_report
    from attune_author.manifest import load_manifest
    from attune_author.staleness import check_staleness

    help_dir = Path(args.help_dir)
    root = Path(args.project_root).resolve()

    manifest = load_manifest(help_dir)
    report = check_staleness(manifest, help_dir, root)
    print(format_status_report(report, help_dir))

    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    """Handle the generate command."""
    from attune_author.generator import generate_feature_templates
    from attune_author.manifest import load_manifest

    help_dir = Path(args.help_dir)
    root = Path(args.project_root).resolve()

    manifest = load_manifest(help_dir)
    feature = manifest.features.get(args.feature)

    if not feature:
        print(f"Feature '{args.feature}' not found in manifest.")
        print(f"Available: {', '.join(sorted(manifest.features))}")
        return 1

    result = generate_feature_templates(
        feature=feature,
        help_dir=help_dir,
        project_root=root,
        overwrite=args.overwrite,
    )

    if result.templates:
        print(f"Generated {len(result.templates)} templates for '{args.feature}':")
        for t in result.templates:
            print(f"  {t.path}")
    else:
        print("No templates generated (all may be manual).")

    return 0


def _cmd_regenerate(args: argparse.Namespace) -> int:
    """Handle the regenerate command."""
    from attune_author.maintenance import run_maintenance

    help_dir = Path(args.help_dir)
    root = Path(args.project_root).resolve()

    result = run_maintenance(
        help_dir=help_dir,
        project_root=root,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"Stale features: {result.stale_count}")
        for name in result.staleness.stale_features:
            print(f"  - {name}")
    else:
        print(f"Regenerated: {result.regenerated_count}")
        if result.failed:
            print(f"Failed: {', '.join(result.failed)}")

    return 0


def _cmd_docs(args: argparse.Namespace) -> int:
    """Handle the docs command."""
    try:
        from attune_author.doc_gen import DocGenConfig, generate_docs
    except ImportError:
        print(
            "Doc generation requires the [ai] extra:\n" "  pip install 'attune-author[ai]'",
            file=sys.stderr,
        )
        return 1

    config = DocGenConfig(
        doc_type=args.doc_type,
        audience=args.audience,
    )

    result = generate_docs(
        target=args.target,
        config=config,
        output_path=args.output,
    )

    if args.output:
        print(f"Documentation written to {args.output}")
    else:
        print(result.content)

    return 0


def _get_version() -> str:
    """Get package version."""
    try:
        from attune_author import __version__

        return __version__
    except ImportError:
        return "dev"


if __name__ == "__main__":
    sys.exit(main())
