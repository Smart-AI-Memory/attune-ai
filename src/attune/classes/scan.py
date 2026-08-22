"""``attune classes scan`` — run the rule pack over paths (R1).

Emits JSON: repo identity, per-rule calibration state, and every hit.
An uncalibrated-here rule's hits are labeled advisory — they never
block and never clear a class (R1). A file the pack cannot parse
yields a ``PARSE-ERROR`` hit; a rule that CRASHES yields a
``SCAN-ERROR`` entry and a non-zero exit — a failed gatekeeper fails
the gate (contract §7, Agy#7).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from attune.classes.rules import RULES, Hit, Rule, calibrated_here, canonical_repo_id, scan_source

__all__ = ["scan_paths", "main"]

_EXCLUDE_PARTS = {"__pycache__", ".venv", "node_modules", ".git"}


def _iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in paths:
        candidates = [root] if root.is_file() else sorted(root.rglob("*.py"))
        files.extend(f for f in candidates if not (_EXCLUDE_PARTS & set(f.parts)))
    return files


def scan_paths(
    paths: list[Path],
    *,
    repo_root: Path | None = None,
    rules: tuple[Rule, ...] = RULES,
) -> dict:
    """Scan files/directories with the rule pack.

    Args:
        paths: Files or directories to scan (repo-relative or absolute).
        repo_root: Repo whose identity binds calibration; default cwd.
        rules: The rules to run.

    Returns:
        A JSON-ready dict: ``repo``, ``rules`` (id -> calibration
        state), ``hits``, ``scan_errors``, ``files_scanned``.
    """
    repo_id = canonical_repo_id(repo_root)
    rule_meta = {
        r.id: {
            "invariant": r.invariant,
            "class_ids": list(r.class_ids),
            "calibrated_here": calibrated_here(r, repo_id),
            "calibration": asdict(r.calibration) if r.calibration else None,
        }
        for r in rules
    }
    hits: list[Hit] = []
    scan_errors: list[dict] = []
    files = _iter_files(paths)
    for f in files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            scan_errors.append({"path": str(f), "error": str(exc)})
            continue
        try:
            hits.extend(scan_source(source, str(f), rules))
        except Exception as exc:  # a crashing rule fails the gate, not silently
            scan_errors.append({"path": str(f), "error": f"{type(exc).__name__}: {exc}"})
    return {
        "repo": repo_id,
        "files_scanned": len(files),
        "rules": rule_meta,
        "hits": [
            {
                **asdict(h),
                "advisory": not rule_meta.get(h.rule_id, {}).get("calibrated_here", False),
            }
            for h in hits
        ],
        "scan_errors": scan_errors,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.classes.scan --paths src/ [--repo-root .]``."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", nargs="+", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    result = scan_paths(args.paths, repo_root=args.repo_root)
    print(json.dumps(result, indent=2))
    return 1 if result["scan_errors"] else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
