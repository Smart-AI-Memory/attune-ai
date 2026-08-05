#!/usr/bin/env python3
"""Enforce the chartkit seal: size ceiling and both import boundaries.

Checks (all must pass):
  A. Outward seal - every import in chartkit JS source starts with './'
     (no attune modules, no npm runtime deps, no '../' escapes).
  B. Inward seal - no tracked .py/.js file outside chartkit references
     chartkit internals, except the sanctioned loader allowlist.
  C. Size ceiling - dist/kernel.min.js <= 20,480 bytes when present
     (--require-dist makes its absence a failure, for CI after build).

Exit 0 clean, exit 1 with one line per violation.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KERNEL_DIR = Path("src/attune/widgets/chartkit")
DIST = KERNEL_DIR / "dist/kernel.min.js"
SIZE_CEILING = 20_480

# The only files allowed to reference chartkit from outside the seal.
# The loader reads dist/kernel.min.js as bytes; it never imports source.
ALLOWED_OUTSIDE = {
    "scripts/check_chartkit_boundary.py",
    "src/attune/widgets/chart_widget_tool.py",
    ".github/workflows/chartkit.yml",
    # Sync test reads spec.schema.json as data (contract check, not an import).
    "tests/unit/widgets/test_chart_spec.py",
    # Package docstring names the sealed dir; it imports nothing from it.
    "src/attune/widgets/__init__.py",
}

IMPORT_RE = re.compile(r"""(?:from\s+|import\s+|require\s*\(\s*)["']([^"']+)["']""")


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def check_outward(violations: list[str]) -> None:
    for js in (REPO / KERNEL_DIR / "src").rglob("*.js"):
        rel = js.relative_to(REPO)
        for mod in IMPORT_RE.findall(js.read_text(encoding="utf-8")):
            if not mod.startswith("./"):
                violations.append(
                    f"{rel}: outward import '{mod}' - kernel imports must start with './'"
                )


def check_inward(violations: list[str]) -> None:
    for rel in tracked_files():
        if rel.startswith(str(KERNEL_DIR)) or rel in ALLOWED_OUTSIDE:
            continue
        if not rel.endswith((".py", ".js", ".mjs", ".ts")):
            continue
        path = REPO / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "chartkit" in text:
            violations.append(f"{rel}: references chartkit but is not in the loader allowlist")


def check_size(violations: list[str], require_dist: bool) -> None:
    dist = REPO / DIST
    if not dist.exists():
        if require_dist:
            violations.append(f"{DIST}: missing (build before the size gate)")
        return
    size = dist.stat().st_size
    if size > SIZE_CEILING:
        violations.append(
            f"{DIST}: {size} bytes exceeds the {SIZE_CEILING}-byte ceiling "
            f"(over by {size - SIZE_CEILING})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-dist",
        action="store_true",
        help="fail if dist/kernel.min.js is absent (CI runs this after build)",
    )
    args = parser.parse_args()

    violations: list[str] = []
    check_outward(violations)
    check_inward(violations)
    check_size(violations, args.require_dist)

    if violations:
        print("chartkit seal BROKEN:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print(f"chartkit seal intact (ceiling {SIZE_CEILING} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
