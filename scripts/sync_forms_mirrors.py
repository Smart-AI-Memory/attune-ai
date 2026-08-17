"""Sync the attune-forms mirror test files into this repo.

The elicitation mirror suite (``tests/unit/elicitation/``) carries
byte-level copies of three attune-forms test files with ONLY the
import block swapped to the ``attune.elicitation`` aliases. Every
attune-forms release that touches them goes red here until the mirrors
re-sync (#2071 and #2072 both did on 2026-08-16); this script makes
the re-sync the one command the post-release parity step runs.

Usage:
    python scripts/sync_forms_mirrors.py [--source ~/attune-forms] [--check]

``--check`` diffs instead of writing and exits 1 on drift — suitable
for release-prep gates.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIRROR_DIR = REPO_ROOT / "tests/unit/elicitation"

#: The shared files — attune-forms tests/<name> -> mirror of the same name.
MIRRORED_FILES = (
    "test_widget_roundtrip.py",
    "test_needs_widget.py",
    "test_widget_css_families.py",
)

#: The import-block swap, applied line-wise in order (first match wins
#: per line). Everything else is byte-identical by design.
IMPORT_SWAPS = (
    ("from attune_forms.reference_form import", "from attune.elicitation.reference_form import"),
    ("from attune_forms.bridge import", "from attune.elicitation.bridge import"),
    ("from attune_forms.widget import", "from attune.elicitation.widget import"),
    (
        "from attune_forms.models import QuestionType",
        "from attune.meta_workflows.models import QuestionType",
    ),
    ("from attune_forms import", "from attune.elicitation import"),
)


def transform(source_text: str, filename: str = "mirror.py") -> str:
    """Apply the import-block swap to one attune-forms test file.

    The swapped names sort differently under isort than the originals,
    so the result is normalized through ruff's import sorter (the same
    hook that runs on commit) — otherwise ``--check`` would flag a
    purely cosmetic ordering diff on every sync (hit on first dogfood,
    2026-08-16).
    """
    out_lines = []
    for line in source_text.splitlines(keepends=True):
        for old, new in IMPORT_SWAPS:
            if line.startswith(old):
                line = line.replace(old, new, 1)
                break
        out_lines.append(line)
    swapped = "".join(out_lines)
    return _isort_normalize(swapped, filename)


def _isort_normalize(text: str, filename: str) -> str:
    """Sort imports the way the repo's ruff hook would; raw on failure."""
    import subprocess

    try:
        proc = subprocess.run(
            ["ruff", "check", "--select", "I", "--fix", "--stdin-filename", filename, "-"],
            input=text,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return text
    return proc.stdout if proc.stdout else text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(Path.home() / "attune-forms"),
        help="Path to an attune-forms checkout (default: ~/attune-forms)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Diff only; exit 1 if any mirror drifts from the transformed source",
    )
    args = parser.parse_args(argv)

    source_tests = Path(args.source).expanduser() / "tests"
    if not source_tests.is_dir():
        print(f"source tests dir not found: {source_tests}", file=sys.stderr)
        return 2

    drifted: list[str] = []
    for name in MIRRORED_FILES:
        src = source_tests / name
        dst = MIRROR_DIR / name
        if not src.is_file():
            print(f"missing in source checkout: {src}", file=sys.stderr)
            return 2
        want = transform(src.read_text(encoding="utf-8"))
        have = dst.read_text(encoding="utf-8") if dst.is_file() else ""
        if want == have:
            print(f"in sync: {name}")
            continue
        if args.check:
            drifted.append(name)
            print(f"DRIFTED: {name}")
        else:
            dst.write_text(want, encoding="utf-8")
            print(f"synced:  {name}")

    if drifted:
        print(
            f"\n{len(drifted)} mirror(s) drifted — run "
            "`python scripts/sync_forms_mirrors.py` to re-sync.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
