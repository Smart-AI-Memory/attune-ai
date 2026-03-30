#!/usr/bin/env python3
"""Run all documentation template generators.

Executes Error, Warning, Tip, and Reference generators in
sequence. Supports --check flag to verify sync state.

Usage:
    python scripts/generate_all.py           # Generate all
    python scripts/generate_all.py --check   # Verify all
"""

from __future__ import annotations

import sys

from generate_error_templates import main as generate_errors
from generate_reference_templates import main as generate_references
from generate_tip_templates import main as generate_tips
from generate_warning_templates import main as generate_warnings


def main() -> int:
    """Run all generators and report combined results.

    Returns:
        Exit code: 0 if all pass, 1 if any fail.
    """
    argv = sys.argv[1:]
    check = "--check" in argv
    mode = "Verifying" if check else "Generating"

    generators = [
        ("Error", generate_errors),
        ("Warning", generate_warnings),
        ("Tip", generate_tips),
        ("Reference", generate_references),
    ]

    print(f"{'=' * 50}")
    print(f"  {mode} ALL documentation templates")
    print(f"{'=' * 50}\n")

    results: dict[str, int] = {}

    for name, gen_fn in generators:
        print(f"--- {name} templates ---\n")
        exit_code = gen_fn(argv)
        results[name] = exit_code
        print()

    # Summary
    print(f"{'=' * 50}")
    print("  Summary")
    print(f"{'=' * 50}\n")

    total_ok = 0
    total_fail = 0
    for name, code in results.items():
        icon = "  OK" if code == 0 else "FAIL"
        print(f"  [{icon}] {name}")
        if code == 0:
            total_ok += 1
        else:
            total_fail += 1

    print(f"\n  Total: {total_ok} passed, {total_fail} failed")

    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
