#!/usr/bin/env python3
"""Audit website package-version claims against PyPI (advisory).

``website/lib/features.ts`` PRODUCTS hardcode the published version of
THREE separate PyPI packages (attune-ai, attune-help, attune-author).
Nothing syncs them, so they drift — caught 2026-06-28: attune-ai shown
as 8.7.0 while PyPI was 9.1.0, attune-author 0.21.0 vs 0.22.0. This
script reads each ``(pypiName, version)`` pair and compares to PyPI's
latest.

Network-tolerant: a PyPI hiccup reports ``unverified`` (never a
failure), so CI flakes don't break the build; only a CONFIRMED mismatch
exits 1. The attune-ai self-version additionally has a deterministic,
network-free guard in
``tests/unit/website/test_website_version_accuracy.py`` (it compares
``features.ts`` to this repo's own ``pyproject.toml``).

Usage:
    python scripts/audit_website_versions.py
    python scripts/audit_website_versions.py --format json

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FEATURES = REPO / "website" / "lib" / "features.ts"

#: A PRODUCTS entry lists ``pypiName`` immediately before ``version``;
#: ``\s+`` spans the newline + indent between the two fields.
PAIR_RE = re.compile(r'pypiName:\s*"([^"]+)",\s+version:\s*"([^"]+)"')

HTTP_TIMEOUT = 5


def parse_products(text: str) -> list[tuple[str, str]]:
    """Return ``(pypiName, version)`` pairs from a features.ts source."""
    return PAIR_RE.findall(text)


def _ver_key(version: str) -> tuple[int, ...] | None:
    """Parse ``X.Y.Z`` into a comparable tuple; None when non-numeric."""
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def pypi_latest(pkg: str) -> str | None:
    """Return the latest version of ``pkg`` on PyPI, or None on any error."""
    url = f"https://pypi.org/pypi/{pkg}/json"
    try:
        # noqa: S310 / nosec B310 — hardcoded https PyPI URL, scheme fixed.
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310  # nosec B310
            return json.load(resp)["info"]["version"]
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any PyPI hiccup (offline, 404, parse) is non-fatal —
        # the package is reported "unverified" rather than failing the audit.
        return None


def audit(text: str, fetch=None) -> list[dict]:
    """Compare each product's claimed version to PyPI.

    ``fetch`` is injectable so tests can run hermetically (``None``
    resolves to :func:`pypi_latest` at call time, so module-level
    patching works too). One PyPI lookup per distinct package (cached).
    Each row is ``{package, site, pypi, status}`` where status is
    ok/ahead/drift/unverified.
    """
    if fetch is None:
        fetch = pypi_latest
    rows: list[dict] = []
    cache: dict[str, str | None] = {}
    for name, version in parse_products(text):
        if name not in cache:
            cache[name] = fetch(name)
        latest = cache[name]
        if latest is None:
            status = "unverified"
        elif latest == version:
            status = "ok"
        else:
            # Site AHEAD of PyPI = a release in flight (the prep PR bumps
            # website/lib/features.ts in lockstep BEFORE publish; PyPI
            # catches up minutes later). Only site BEHIND PyPI is the
            # staleness bug this gate exists for. Unparseable versions
            # stay "drift" — fail loud rather than guess.
            site_key, pypi_key = _ver_key(version), _ver_key(latest)
            if site_key is not None and pypi_key is not None and site_key > pypi_key:
                status = "ahead"
            else:
                status = "drift"
        rows.append({"package": name, "site": version, "pypi": latest, "status": status})
    return rows


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exit 1 iff any version CONFIRMED-drifted from PyPI."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--features", type=Path, default=FEATURES)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        text = args.features.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.features}: {exc}", file=sys.stderr)
        return 1

    rows = audit(text)
    if args.format == "json":
        print(json.dumps(rows, indent=2))
    else:
        marks = {"ok": "✓", "drift": "✗", "unverified": "?", "ahead": "↑"}
        for r in rows:
            print(f"  {marks[r['status']]} {r['package']:16} site={r['site']:8} pypi={r['pypi']}")

    ahead = [r for r in rows if r["status"] == "ahead"]
    if ahead:
        names = ", ".join(f"{r['package']} ({r['site']} > {r['pypi']})" for r in ahead)
        print(
            f"\n{len(ahead)} version(s) ahead of PyPI (release in flight, "
            f"self-heals on publish): {names}"
        )

    drift = [r for r in rows if r["status"] == "drift"]
    if drift:
        names = ", ".join(f"{r['package']} ({r['site']}->{r['pypi']})" for r in drift)
        print(
            f"\n{len(drift)} version(s) drifted from PyPI: {names}\n"
            "Update website/lib/features.ts to match.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
