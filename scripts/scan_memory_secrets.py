#!/usr/bin/env python3
"""Advisory secret sweep over the memory corpora — R2 of memory-security-hardening.

Secret detection now gates the write paths (raw ``session_stash._sanitize``,
curated ``personal._secret_gate``), but memories written *before* those gates
existed were never scanned. This is the one-time — and repeatable —
corpus-wide sweep the spec calls for: it reads every curated markdown file and
the raw findings JSONL and reports any secret the shared detector finds.

**Advisory and read-only.** It never edits, redacts, or deletes. Rotation is a
human action the spec is explicit about ("deletion is insufficient — rotate"),
and a script cannot rotate a credential. Exit code is 1 when secrets are found
so CI/pre-push can gate on it, 0 when clean.

Usage:
    python scripts/scan_memory_secrets.py
    python scripts/scan_memory_secrets.py --root ~/.claude/memory --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def default_targets() -> tuple[list[Path], list[Path]]:
    """Return (curated_markdown_roots, raw_jsonl_files) present on this machine."""
    home = Path.home()
    md_roots = [home / ".claude" / "memory", home / ".attune" / "memory"]
    projects = home / ".claude" / "projects"
    if projects.is_dir():
        md_roots.extend(sorted(projects.glob("*/memory")))
    jsonl = [
        home / ".attune" / "session_stash" / "findings.jsonl",
        home / ".attune" / "telemetry" / "memory_events.jsonl",
    ]
    return (
        [p for p in md_roots if p.is_dir()],
        [p for p in jsonl if p.is_file()],
    )


def _iter_markdown(roots: list[Path]):
    seen: set[Path] = set()
    for root in roots:
        for path in sorted(root.rglob("*.md")):
            if path not in seen:
                seen.add(path)
                yield path


def _scan_text(detect, path: Path, text: str) -> list[dict]:
    findings = []
    for d in detect(text):
        findings.append(
            {
                "path": str(path),
                "type": d.secret_type.value,
                "severity": d.severity.value,
                "line": d.line_number,
            }
        )
    return findings


def sweep(md_roots: list[Path], jsonl_files: list[Path]) -> dict:
    """Scan every curated file + raw JSONL line. Pure read; returns a report."""
    from attune.memory.security.secrets_detector import detect_secrets

    findings: list[dict] = []
    files_scanned = 0

    for path in _iter_markdown(md_roots):
        files_scanned += 1
        try:
            findings.extend(_scan_text(detect_secrets, path, path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue

    for jf in jsonl_files:
        files_scanned += 1
        try:
            for i, line in enumerate(jf.read_text(encoding="utf-8").splitlines(), 1):
                for hit in _scan_text(detect_secrets, jf, line):
                    hit["line"] = i
                    findings.append(hit)
        except (OSError, UnicodeDecodeError):
            continue

    return {"files_scanned": files_scanned, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, dest="roots")
    parser.add_argument("--jsonl", action="append", type=Path, dest="jsonl")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    src = repo / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    if args.roots or args.jsonl:
        md_roots = [p for p in (args.roots or []) if p.is_dir()]
        jsonl_files = [p for p in (args.jsonl or []) if p.is_file()]
    else:
        md_roots, jsonl_files = default_targets()

    report = sweep(md_roots, jsonl_files)
    findings = report["findings"]

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Scanned {report['files_scanned']} file(s) across the memory corpora.")
        if not findings:
            print("No secrets found. (Advisory scan — not a guarantee.)")
        else:
            print(f"\n[!] {len(findings)} secret(s) found — ROTATE, do not just delete:\n")
            for f in findings:
                print(f"  {f['severity']:8} {f['type']:20} {f['path']}:{f['line']}")

    # Non-zero when secrets found so a pre-push/CI hook can gate on it.
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
