#!/usr/bin/env python3
"""Project the canonical Fix workspace sandbox into the Next.js site.

The standalone source lives under ``attune-ai-dev/fix-workspace`` and
is served directly by attune-ai.dev.  smartaimemory.com embeds the same
interaction assets from ``website/public/fix-workspace-demo``.  The HTML
projection adapts only the host-specific absolute asset root.

Run ``python scripts/sync_fix_workspace_demo.py --write`` after editing
the source, or ``--check`` in verification and CI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "attune-ai-dev" / "fix-workspace"
DESTINATION = REPO_ROOT / "website" / "public" / "fix-workspace-demo"
FILES = ("index.html", "demo.css", "demo.js")
INDEX_PATH_REPLACEMENTS = (
    (b"/fix-workspace/demo.css", b"/fix-workspace-demo/demo.css"),
    (b"/fix-workspace/demo.js", b"/fix-workspace-demo/demo.js"),
)


def _validated_path(root: Path, candidate: Path) -> Path:
    """Return a resolved candidate only when it stays below ``root``."""
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    resolved.relative_to(resolved_root)
    return resolved


def _projected_bytes(source: Path, name: str) -> bytes:
    """Read an asset and adapt the HTML asset root for smartaimemory.com."""
    content = source.read_bytes()
    if name == "index.html":
        for standalone_path, website_path in INDEX_PATH_REPLACEMENTS:
            content = content.replace(standalone_path, website_path)
    return content


def drifted_files() -> list[str]:
    """List projected files that are absent or differ from their source."""
    drifted: list[str] = []
    for name in FILES:
        source = _validated_path(REPO_ROOT, SOURCE / name)
        destination = _validated_path(REPO_ROOT, DESTINATION / name)
        if not destination.exists() or destination.read_bytes() != _projected_bytes(source, name):
            drifted.append(name)
    return drifted


def write_projection() -> None:
    """Write each canonical asset to the smartaimemory.com public tree."""
    destination = _validated_path(REPO_ROOT, DESTINATION)
    destination.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source = _validated_path(REPO_ROOT, SOURCE / name)
        output = _validated_path(REPO_ROOT, destination / name)
        output.write_bytes(_projected_bytes(source, name))
        print(f"wrote {output.relative_to(REPO_ROOT)}")


def main() -> int:
    """Write the projection or fail when committed copies have drifted."""
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.write:
        write_projection()
        return 0
    drifted = drifted_files()
    if drifted:
        print("Fix workspace projection drift: " + ", ".join(drifted))
        return 1
    print("Fix workspace projection is in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
