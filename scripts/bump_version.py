#!/usr/bin/env python3
"""Bump the release version across every release-artifact file.

Source of truth: the version passed on the command line; the current
version is read from ``pyproject.toml`` (the authoritative PyPI
surface). Writes, in one validated pass:

1. ``pyproject.toml`` — ``version = "X"``
2. ``plugin/.claude-plugin/plugin.json`` — ``"version"``
3. ``plugin/.claude-plugin/marketplace.json`` — ``metadata.version``
   AND ``plugins[0].version``
4. ``.claude-plugin/marketplace.json`` (root) — same two fields
5. ``plugin/core/__init__.py`` — ``__version__``
6. ``.claude/CLAUDE.md`` — header (``# Attune AI Framework vX``) and
   footer (``**Version:** X``)
7. ``docs/reference/API_REFERENCE.md`` — header and footer
   (``**Version:** X``)
8. ``website/lib/features.ts`` — the two attune-ai product entries
   (``pypiName: "attune-ai"`` + ``version: "X"``; other products'
   versions are independent and never touched)
9. ``website/app/page.tsx`` — homepage badge (``<span>vX</span>``)

Every replacement is count-checked against the expected number of
occurrences BEFORE any file is written; a mismatch aborts with no
partial state. After writing, all sites are re-read and verified.

Backstop guards: ``tests/unit/plugins/test_plugin_config_validation.py
::TestVersionConsistency::test_all_versions_match`` (asserts all
sites equal — fails with a pointer to this script) and
``tests/unit/test_website_version_accuracy.py::TestFeaturesVersionSync``
(website sites vs pyproject — the guard that turned every CI lane red
on the 9.4.0 release when this script didn't yet cover the website).

Usage:
    python scripts/bump_version.py 8.5.0
    python scripts/bump_version.py 8.5.0 --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass
class Site:
    """One file's version-replacement plan."""

    path: Path
    pattern: str  # template with {v} for the version
    expected: int  # exact count, or minimum when min_count=True
    min_count: bool = False

    def render(self, version: str) -> str:
        """Render the pattern with a version, escaping regex chars."""
        return re.escape(self.pattern).replace(r"\{v\}", re.escape(version))


def _sites(root: Path) -> list[Site]:
    """The full release-artifact site list (R1 source of truth)."""
    return [
        Site(root / "pyproject.toml", 'version = "{v}"', 1),
        Site(
            root / "plugin" / ".claude-plugin" / "plugin.json",
            '"version": "{v}"',
            1,
        ),
        Site(
            root / "plugin" / ".claude-plugin" / "marketplace.json",
            '"version": "{v}"',
            2,
        ),
        Site(
            root / ".claude-plugin" / "marketplace.json",
            '"version": "{v}"',
            2,
        ),
        Site(
            root / "plugin" / "core" / "__init__.py",
            '__version__ = "{v}"',
            1,
        ),
        Site(
            root / ".claude" / "CLAUDE.md",
            "# Attune AI Framework v{v}",
            1,
        ),
        Site(
            root / ".claude" / "CLAUDE.md",
            "**Version:** {v}",
            1,
            min_count=True,
        ),
        Site(
            root / "docs" / "reference" / "API_REFERENCE.md",
            "**Version:** {v}",
            2,
            min_count=True,
        ),
        # Website sites — enforced by tests/unit/
        # test_website_version_accuracy.py in the required CI lanes.
        # The pattern is anchored on pypiName so the other products'
        # independent versions (attune-help, attune-author) are never
        # matched even if one coincides with the attune-ai version.
        Site(
            root / "website" / "lib" / "features.ts",
            'pypiName: "attune-ai",\n    version: "{v}"',
            2,
        ),
        Site(
            root / "website" / "app" / "page.tsx",
            "<span>v{v}</span>",
            1,
        ),
    ]


def read_current_version(root: Path) -> str:
    """Read the authoritative current version from pyproject.toml."""
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "(\d+\.\d+\.\d+)"', text, re.MULTILINE)
    if not match:
        raise ValueError('pyproject.toml: no semver `version = "X.Y.Z"` line found')
    return match.group(1)


def bump(root: Path, new_version: str, dry_run: bool = False) -> str:
    """Bump all sites from the current pyproject version to new_version.

    Returns the old version. Raises ValueError on any validation
    failure BEFORE writing anything (no partial state).
    """
    if not SEMVER.match(new_version):
        raise ValueError(f"not a semver version: {new_version!r}")
    old = read_current_version(root)
    if old == new_version:
        raise ValueError(f"already at {new_version}")

    # Validate every site first; collect planned writes.
    planned: dict[Path, str] = {}
    for site in _sites(root):
        text = planned.get(site.path) or site.path.read_text(encoding="utf-8")
        old_re = site.render(old)
        count = len(re.findall(old_re, text))
        ok = count >= site.expected if site.min_count else count == site.expected
        if not ok:
            want = f">= {site.expected}" if site.min_count else str(site.expected)
            raise ValueError(
                f"{site.path}: expected {want} occurrence(s) of "
                f"{site.pattern.format(v=old)!r}, found {count} — "
                "fix the file (or this script's site list) before bumping"
            )
        planned[site.path] = re.sub(old_re, site.pattern.format(v=new_version), text)

    if not dry_run:
        for path, text in planned.items():
            path.write_text(text, encoding="utf-8")
        # Post-write verification: every site reads back at new_version.
        for site in _sites(root):
            text = site.path.read_text(encoding="utf-8")
            count = len(re.findall(site.render(new_version), text))
            ok = count >= site.expected if site.min_count else count == site.expected
            if not ok:
                raise RuntimeError(f"{site.path}: post-write verification failed")
    return old


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="new semver version, e.g. 8.5.0")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repo root (default: this script's parent repo)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate every site without writing",
    )
    args = parser.parse_args(argv)
    try:
        old = bump(args.root, args.version, dry_run=args.dry_run)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    verb = "would bump" if args.dry_run else "bumped"
    files = sorted({str(s.path.relative_to(args.root)) for s in _sites(args.root)})
    print(f"{verb} {old} -> {args.version} across {len(files)} files:")
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
