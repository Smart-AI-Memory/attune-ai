#!/usr/bin/env python3
"""Project single-source help into the served bundle (Design B).

The single-source projector writes `.help/templates/<feature>/<kind>.md`
(feature-organized). The in-conversation help surface (MCP `help_lookup`
-> `attune.help.templates.populate`) reads `plugin/help/generated/
<type>/<name>.md` (type-organized) — the bundle that SHIPS in the Claude
Code plugin. A dev-checkout fallback (help-serving-bridge D1) makes
`populate` find the feature-organized files, but a clean `uvx`/plugin
install ships only the bundle, not `.help/templates/<feature>/`. This
script copies each single-sourced feature's kinds INTO the bundle so the
grounded content resolves directly from the shipped artifact (D5).

It then rebuilds `cross_links.json` and `source_manifest.json` for the
whole bundle. It does NOT run the lessons/skills per-type generators, so
existing bundle templates (system concepts, `tool-<skill>`) are left
untouched.

Usage:
    python scripts/sync_help_bundle.py            # emit + rebuild indexes
    python scripts/sync_help_bundle.py --dry-run  # show what would change
    python scripts/sync_help_bundle.py --check     # exit 1 if out of sync
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import frontmatter
import yaml

# kind (single-source filename stem) -> bundle type directory (plural)
_KIND_TO_TYPE_DIR = {
    "concept": "concepts",
    "task": "tasks",
    "reference": "references",
    "quickstart": "quickstarts",
    "comparison": "comparisons",
    "error": "errors",
    "troubleshooting": "troubleshooting",
    "warning": "warnings",
    "note": "notes",
    "tip": "tips",
    "faq": "faqs",
}


def _repo_root() -> Path:
    """Repository root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _single_sourced_features(features_yaml: Path) -> dict[str, dict]:
    """Return {feature: entry} for features marked status: manual."""
    data = yaml.safe_load(features_yaml.read_text(encoding="utf-8"))
    features = data.get("features", {})
    return {
        name: entry
        for name, entry in features.items()
        if isinstance(entry, dict) and entry.get("status") == "manual"
    }


def _planned_outputs(
    root: Path,
    features: dict[str, dict],
) -> list[tuple[Path, Path, str, list[str]]]:
    """Plan (src, dest, feature, tags) for every kind of every feature."""
    templates_dir = root / ".help" / "templates"
    bundle_dir = root / "plugin" / "help" / "generated"
    plan: list[tuple[Path, Path, str, list[str]]] = []

    bundle_root = bundle_dir.resolve()
    for feature, entry in sorted(features.items()):
        feat_dir = templates_dir / feature
        if not feat_dir.is_dir():
            continue
        tags = entry.get("tags", []) or []
        for kind_file in sorted(feat_dir.glob("*.md")):
            type_dir = _KIND_TO_TYPE_DIR.get(kind_file.stem)
            if type_dir is None:
                continue  # unknown kind — skip
            dest = bundle_dir / type_dir / f"{feature}.md"
            # Containment check (CWE-22): `feature` is a features.yaml key;
            # a `..`/separator in it must not write outside the bundle.
            # Mirrors the read-side guards in attune.help.templates.
            try:
                dest.resolve().relative_to(bundle_root)
            except ValueError:
                print(
                    f"  SKIP unsafe feature key: {feature!r}",
                    file=sys.stderr,
                )
                continue
            plan.append((kind_file, dest, feature, list(tags)))
    return plan


def _render_bundle_file(
    src: Path,
    feature: str,
    tags: list[str],
) -> str:
    """Build the bundle file content from a single-source template.

    Keeps the body verbatim; normalizes frontmatter to the bundle shape
    (type, name, tags, source) so cross-link + source-manifest builders
    pick it up. `source` points at the single-source master.
    """
    try:
        post = frontmatter.load(str(src))
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: name the offending file — a malformed template
        # otherwise aborts the whole sync with an opaque traceback.
        raise RuntimeError(f"failed to parse {src}: {exc}") from exc
    kind = src.stem
    out = frontmatter.Post(post.content)
    out["type"] = post.get("type", kind)
    out["name"] = feature
    out["tags"] = tags
    out["source"] = f"content/features/{feature}.md"
    return frontmatter.dumps(out) + "\n"


def _rebuild_indexes(bundle_dir: Path) -> None:
    """Rebuild cross_links.json and source_manifest.json in place."""
    # Sibling scripts live in this dir; insert once (idempotent) so repeat
    # calls don't stack entries. These modules are not importable packages.
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from build_cross_links import build_cross_links
    from generate_all import _build_source_manifest

    links = build_cross_links(bundle_dir)
    (bundle_dir / "cross_links.json").write_text(
        json.dumps(links, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = _build_source_manifest(bundle_dir)
    (bundle_dir / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    """Emit single-source content into the bundle and rebuild indexes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Plan only.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any bundle file is missing or stale.",
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    features = _single_sourced_features(root / ".help" / "features.yaml")
    plan = _planned_outputs(root, features)

    if not plan:
        print("No single-sourced templates found to emit.")
        return 0

    stale = 0
    written = 0
    for src, dest, feature, tags in plan:
        rendered = _render_bundle_file(src, feature, tags)
        current = dest.read_text(encoding="utf-8") if dest.exists() else None
        # NOTE: byte-exact compare. This (and the drift-guard test) couples
        # to frontmatter.dumps()/PyYAML output formatting — a library bump
        # that changes serialization would flag every file stale until a
        # re-sync. Intentional (cheap, catches real drift); re-sync if so.
        if current == rendered:
            continue
        stale += 1
        rel = dest.relative_to(root)
        if args.check:
            print(f"  STALE {rel}")
            continue
        if args.dry_run:
            print(f"  would write {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        written += 1
        print(f"  wrote {rel}")

    if args.check:
        if stale:
            print(f"{stale} bundle file(s) out of sync — run sync_help_bundle.py")
            return 1
        print(f"bundle in sync ({len(plan)} single-source templates)")
        return 0

    if args.dry_run:
        print(f"would write {stale} of {len(plan)} (others already current)")
        return 0

    if written:
        print("rebuilding cross_links.json + source_manifest.json ...")
        _rebuild_indexes(root / "plugin" / "help" / "generated")
    print(f"synced {written} file(s) from {len(features)} single-sourced features")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
