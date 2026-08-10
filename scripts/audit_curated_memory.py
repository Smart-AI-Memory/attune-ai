#!/usr/bin/env python3
"""Advisory staleness sweep over curated markdown memory corpora.

Reports which curated memories most need a human verdict, plus corpus
integrity problems (schema violations, broken links, index-pointer drift).

**Advisory only.** This script never writes to a corpus and always exits 0 —
it is not a gate. Turning it into one requires the review loop from P2 and
the recall-frequency term from P3; see
``docs/specs/memory-status-integrity/design.md``.

Usage:
    python scripts/audit_curated_memory.py
    python scripts/audit_curated_memory.py --root ~/.attune/memory --top 10
    python scripts/audit_curated_memory.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def default_roots() -> list[Path]:
    """Return the curated corpora present on this machine.

    The library hardcodes no paths (design D3); this CLI is a caller and may
    offer conveniences. Missing roots are simply absent from the result.
    """
    home = Path.home()
    candidates = [home / ".attune" / "memory", home / ".claude" / "memory"]
    projects = home / ".claude" / "projects"
    if projects.is_dir():
        candidates.extend(sorted(projects.glob("*/memory")))
    return [path for path in candidates if path.is_dir()]


def _format_report(report, top: int) -> str:
    """Render the advisory report as plain text."""
    lines: list[str] = []
    lines.append(f"Scanned {report.scanned} curated memories in {len(report.roots)} root(s)")
    lines.append(f"Age basis: {report.age_basis}")
    lines.append(f"Rank basis: {report.rank_basis}")
    if report.age_basis == "mtime":
        lines.append(
            "  note: mtime records the last EDIT, not the last verification — "
            "bulk reformats read as fresh. Resolved when `verified:` ships (P2)."
        )
    lines.append("")

    from attune.memory.curated_audit import epistemic_tier

    serves_by_stem = dict(report.serves_by_stem)
    lines.append(f"── Review priority ({report.rank_basis}), top {top} ──")
    for (mem, score), (_, basis, days) in zip(
        report.ranked[:top], report.age_bases[:top], strict=False
    ):
        mem_type = mem.mem_type or "?"
        tier = epistemic_tier(mem.mem_type, basis, days)
        serve_note = ""
        if report.rank_basis != "age-only":
            serve_note = f", serves={serves_by_stem.get(mem.stem, 0)}"
        lines.append(f"  {score:8.1f}  [{mem_type:9}] {mem.stem}  ({basis}, {tier}{serve_note})")
    if not report.ranked:
        lines.append("  (none)")
    if any(basis in {"invalidated", "tombstoned"} for _, basis, _ in report.age_bases):
        lines.append(
            "  note: invalidated = edited substantively since verification "
            "(verified: is void); tombstoned = latest verdict was 'wrong'."
        )
    lines.append("")

    def section(title: str, rows: list[str]) -> None:
        lines.append(f"── {title} ({len(rows)}) ──")
        if rows:
            lines.extend(f"  {row}" for row in rows)
        else:
            lines.append("  (none)")
        lines.append("")

    section(
        "Schema violations",
        [f"{path.name}: {', '.join(keys)}" for path, keys in report.schema_violations],
    )
    section(
        "Invalid metadata.type",
        [f"{path.name}: type '{value}'" for path, value in report.invalid_types],
    )
    section("name: does not match filename", [p.name for p in report.name_mismatches])
    section("Broken [[links]]", [f"{path.name} -> {link}" for path, link in report.broken_links])
    section("Memories with no MEMORY.md pointer", [p.name for p in report.orphans])
    section(
        "Pointers with no memory file",
        [f"{index.parent.name}/MEMORY.md -> {stem}" for index, stem in report.dangling_pointers],
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the sweep. Always returns 0 — advisory, never a gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        dest="roots",
        help="Corpus root to scan (repeatable). Defaults to the corpora found on this machine.",
    )
    parser.add_argument("--top", type=int, default=15, help="How many ranked rows to show.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    src = repo / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from attune.memory.curated_audit import sweep
    from attune.memory.serve_telemetry import serve_counts

    roots = args.roots or default_roots()
    if not roots:
        print("No curated memory corpora found.")
        return 0

    # P3 task 5: the CLI opts into the live telemetry sink explicitly —
    # the library never auto-reads it. None (vs {}) keeps the report
    # honest when no frequency evidence exists at all.
    served = serve_counts() or None
    report = sweep(roots, serves=served)

    if args.json:
        serves_by_stem = dict(report.serves_by_stem)
        print(
            json.dumps(
                {
                    "scanned": report.scanned,
                    "age_basis": report.age_basis,
                    "rank_basis": report.rank_basis,
                    "roots": [str(r) for r in report.roots],
                    "ranked": [
                        {
                            "stem": mem.stem,
                            "type": mem.mem_type,
                            "unverified_days": days,
                            "risk": round(score, 2),
                            "basis": basis,
                            "serves": serves_by_stem.get(mem.stem),
                            "path": str(mem.path),
                        }
                        for (mem, score), (_, basis, days) in zip(
                            report.ranked[: args.top], report.age_bases[: args.top], strict=False
                        )
                    ],
                    "schema_violations": [
                        {"path": str(p), "keys": list(k)} for p, k in report.schema_violations
                    ],
                    "invalid_types": [{"path": str(p), "type": t} for p, t in report.invalid_types],
                    "name_mismatches": [str(p) for p in report.name_mismatches],
                    "broken_links": [
                        {"path": str(p), "link": link} for p, link in report.broken_links
                    ],
                    "orphans": [str(p) for p in report.orphans],
                    "dangling_pointers": [
                        {"index": str(i), "stem": s} for i, s in report.dangling_pointers
                    ],
                },
                indent=2,
            )
        )
    else:
        print(_format_report(report, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
