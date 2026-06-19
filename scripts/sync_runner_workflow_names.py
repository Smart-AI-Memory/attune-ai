#!/usr/bin/env python3
"""Generate the ops dashboard's ``WORKFLOW_NAMES`` JS array.

Single source of truth: ``attune.ops.data.list_workflows()`` (the same
canonical list the dashboard serves). The derived artifact is the
``WORKFLOW_NAMES`` array in ``src/attune/ops/static/js/runner.js`` —
used to render workflow-name mentions as clickable pills.

This replaces the old hand-edit-and-hope-a-test-catches-it loop
(``test_runner_js_parsing.py::test_workflow_names_match_canonical_list``)
with a generator + an inverted backstop: the test now runs ``--check``
and tells you the command to run when the array is stale. See
docs/specs/drift-guards-to-generators/.

Usage:
    python scripts/sync_runner_workflow_names.py          # Regenerate
    python scripts/sync_runner_workflow_names.py --check   # Verify in sync
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Sentinel markers delimiting the generated block in runner.js. The
# generator only ever rewrites text between these (inclusive), so the
# surrounding hand-written JS is never touched.
BEGIN = "  // >>> AUTO-GENERATED: WORKFLOW_NAMES — do not hand-edit."
END = "  // <<< AUTO-GENERATED: WORKFLOW_NAMES"

# Names per rendered line (cosmetic; keeps the array readable).
_PER_LINE = 4

_BLOCK_RE = re.compile(
    re.escape(BEGIN) + r".*?" + re.escape(END),
    re.DOTALL,
)


def _canonical_names() -> list[str]:
    """Return the sorted canonical workflow names (source of truth)."""
    from attune.ops import data

    return sorted(w.name for w in data.list_workflows())


def render_block(names: list[str]) -> str:
    """Render the full generated block (markers + array) for runner.js."""
    rows: list[str] = []
    for i in range(0, len(names), _PER_LINE):
        chunk = names[i : i + _PER_LINE]
        rows.append("    " + ", ".join(f'"{n}"' for n in chunk) + ",")
    # Drop the trailing comma on the final entry for clean JS.
    if rows:
        rows[-1] = rows[-1].rstrip(",")
    body = "\n".join(rows)
    return (
        f"{BEGIN}\n"
        "  // Source of truth: attune.ops.data.list_workflows().\n"
        "  // Regenerate: python scripts/sync_runner_workflow_names.py\n"
        "  var WORKFLOW_NAMES = [\n"
        f"{body}\n"
        "  ];\n"
        f"{END}"
    )


def apply(runner_js: Path, *, check: bool) -> int:
    """Generate or verify the WORKFLOW_NAMES block. Returns an exit code."""
    text = runner_js.read_text(encoding="utf-8")
    if not _BLOCK_RE.search(text):
        print(
            f"FAIL: generated markers not found in {runner_js.name}.\n"
            f"      Expected a block delimited by:\n"
            f"        {BEGIN}\n"
            f"        {END}"
        )
        return 1

    new_block = render_block(_canonical_names())
    new_text = _BLOCK_RE.sub(lambda _: new_block, text)

    if new_text == text:
        print(f"OK: {runner_js.name} WORKFLOW_NAMES is in sync.")
        return 0

    if check:
        print(
            f"FAIL: {runner_js.name} WORKFLOW_NAMES is out of sync with "
            "attune.ops.data.list_workflows().\n"
            "      Run: python scripts/sync_runner_workflow_names.py"
        )
        return 1

    runner_js.write_text(new_text, encoding="utf-8")
    print(f"Regenerated WORKFLOW_NAMES in {runner_js.name}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]
    check = "--check" in argv
    repo_root = Path(__file__).resolve().parent.parent
    runner_js = repo_root / "src" / "attune" / "ops" / "static" / "js" / "runner.js"
    return apply(runner_js, check=check)


if __name__ == "__main__":
    raise SystemExit(main())
