#!/usr/bin/env python3
"""Enforce every widget kernel's seal: size ceiling and both import
boundaries (widget-kernel-family R3; generalized from the chartkit-only
check_chartkit_boundary.py).

Checks per kernel (all must pass):
  A. Outward seal - every import in kernel JS source starts with './'
     (no attune modules, no npm runtime deps, no '../' escapes).
  B. Inward seal - no tracked .py/.js file outside the kernel references
     its internals, except the kernel's sanctioned allowlist.
  C. Size ceiling - dist/kernel.min.js within the kernel's ruled budget
     when present (--require-dist makes absence a failure, for CI after
     build).

Kernels register in KERNELS below; per-kernel ceiling overrides are
ruled in docs/specs/widget-kernel-family/ (R3/D2) before they land
here. Exit 0 clean, exit 1 with one line per violation.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

DEFAULT_CEILING = 20_480

IMPORT_RE = re.compile(r"""(?:from\s+|import\s+|require\s*\(\s*)["']([^"']+)["']""")


@dataclass(frozen=True)
class KernelPolicy:
    """One sealed kernel's boundary contract."""

    name: str
    kernel_dir: str  # repo-relative, forward slashes
    ceiling: int = DEFAULT_CEILING
    # Files outside the seal allowed to reference kernel internals
    # (loaders read dist bytes / schemas as data - never import source).
    allowed_outside: frozenset[str] = field(default_factory=frozenset)
    # Textual markers that count as coupling to internals. Police paths
    # and imports, not vocabulary: prose may say "chartkit", but
    # "chartkit/" or "widgets.chartkit" is coupling.
    internal_markers: tuple[str, ...] = ()


KERNELS: dict[str, KernelPolicy] = {
    "chartkit": KernelPolicy(
        name="chartkit",
        kernel_dir="src/attune/widgets/chartkit",
        ceiling=DEFAULT_CEILING,
        allowed_outside=frozenset(
            {
                "scripts/check_widget_kernel_boundaries.py",
                "src/attune/widgets/chart_widget_tool.py",
                ".github/workflows/chartkit.yml",
                # Sync test reads spec.schema.json as data (contract
                # check, not an import).
                "tests/unit/widgets/test_chart_spec.py",
                # Package docstring names the sealed dir; imports nothing.
                "src/attune/widgets/__init__.py",
                # Boundary-gate tests reference the policy, not internals.
                "tests/unit/gates/test_widget_kernel_boundary.py",
            }
        ),
        internal_markers=("chartkit/", "widgets.chartkit"),
    ),
    # formkit (R1) slots in here when it lands - ceiling 40_960 per
    # widget-kernel-family D2/F4. infokit (R2) uses the default.
}


def tracked_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def check_outward(repo: Path, policy: KernelPolicy, violations: list[str]) -> None:
    for js in (repo / policy.kernel_dir / "src").rglob("*.js"):
        rel = js.relative_to(repo)
        for mod in IMPORT_RE.findall(js.read_text(encoding="utf-8")):
            if not mod.startswith("./"):
                violations.append(
                    f"[{policy.name}] {rel}: outward import '{mod}' - "
                    "kernel imports must start with './'"
                )


def check_inward(
    repo: Path,
    policy: KernelPolicy,
    files: list[str],
    violations: list[str],
) -> None:
    for rel in files:
        if rel.startswith(policy.kernel_dir) or rel in policy.allowed_outside:
            continue
        if not rel.endswith((".py", ".js", ".mjs", ".ts")):
            continue
        path = repo / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in policy.internal_markers):
            violations.append(
                f"[{policy.name}] {rel}: references kernel internals but "
                "is not in the loader allowlist"
            )


def check_size(repo: Path, policy: KernelPolicy, violations: list[str], require_dist: bool) -> None:
    dist = repo / policy.kernel_dir / "dist/kernel.min.js"
    rel = dist.relative_to(repo)
    if not dist.exists():
        if require_dist:
            violations.append(f"[{policy.name}] {rel}: missing (build before the size gate)")
        return
    size = dist.stat().st_size
    if size > policy.ceiling:
        violations.append(
            f"[{policy.name}] {rel}: {size} bytes exceeds the "
            f"{policy.ceiling}-byte ceiling (over by {size - policy.ceiling})"
        )


def run_checks(
    repo: Path,
    policies: list[KernelPolicy],
    require_dist: bool,
) -> list[str]:
    """Run all three checks for each policy; return violations."""
    violations: list[str] = []
    files = tracked_files(repo)
    for policy in policies:
        check_outward(repo, policy, violations)
        check_inward(repo, policy, files, violations)
        check_size(repo, policy, violations, require_dist)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kernel",
        choices=sorted(KERNELS),
        help="check one kernel only (default: all registered kernels)",
    )
    parser.add_argument(
        "--require-dist",
        action="store_true",
        help="fail if dist/kernel.min.js is absent (CI runs this after build)",
    )
    args = parser.parse_args()

    policies = [KERNELS[args.kernel]] if args.kernel else list(KERNELS.values())
    violations = run_checks(REPO, policies, args.require_dist)

    if violations:
        print("widget-kernel seal BROKEN:")
        for v in violations:
            print(f"  - {v}")
        return 1
    names = ", ".join(f"{p.name} (ceiling {p.ceiling})" for p in policies)
    print(f"widget-kernel seals intact: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
