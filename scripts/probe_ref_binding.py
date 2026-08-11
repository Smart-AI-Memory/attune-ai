#!/usr/bin/env python3
"""mcv D-5 re-probe: shipped prompt vs v2 prompt+binder, dual-arm.

memory-claim-verification design.md D-5 (gates P1): run BOTH extraction
arms on the SAME transcripts — arm v1 (shipped prompt, extraction-quality
baseline) and arm v2 (refs prompt delta + deterministic binder, behind
ATTUNE_MEMORY_REFS_V2) — plus a salted adversarial subset, reported
separately, never blended.

This is a MEASUREMENT, not a test. It replays real session transcripts
through the REAL shipped extraction path (session_stash._extract_via_ollama)
and the REAL binder (session_stash._bind_findings) — the probe is the
binder's test harness (design D-3); nothing is reimplemented here. The
fuzzy prose matcher this script carried for the D7 rider-(c) probe is
retired (D8/D9); its result (22.9%) is recorded in the spec's decisions.md.

    python scripts/probe_ref_binding.py --transcript-list d8.txt --arm both
    python scripts/probe_ref_binding.py --salt-dir ~/.attune/tmp/salted \
        --salt-manifest ~/.attune/tmp/salted/manifest.json

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "plugin" / "hooks" / "session_stash.py"


def load_hook():
    """Load the Stop-hook module so the REAL extraction+binding path is used."""
    spec = importlib.util.spec_from_file_location("_stash_hook", HOOK)
    if spec is None or spec.loader is None:  # pragma: no cover - env guard
        raise RuntimeError(f"cannot load {HOOK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_stash_hook"] = module
    spec.loader.exec_module(module)
    return module


def session_cwd(transcript: Path) -> str:
    """First recorded cwd in the transcript (binder path normalization)."""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"cwd"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                cwd = record.get("cwd")
                if isinstance(cwd, str) and cwd:
                    return cwd
    except OSError:
        pass
    return str(Path.home())


def run_arm(
    hook,
    arm: str,
    transcripts: list[Path],
    out_rows: list[dict],
) -> dict:
    """Extract (and for v2, bind) every transcript under the given arm."""
    if arm == "v2":
        os.environ["ATTUNE_MEMORY_REFS_V2"] = "1"
    else:
        os.environ.pop("ATTUNE_MEMORY_REFS_V2", None)

    stats: dict = {
        "arm": arm,
        "scored": 0,
        "misses": 0,
        "findings": 0,
        "content_lengths": [],
        "contents": [],
        "per_transcript_findings": [],
        "status_counts": Counter(),
        "refs_per_finding": Counter(),
        "ref_items_proposed": 0,
        "ref_items_bound": 0,
        "ref_items_rejected_membership": 0,
        "ref_items_rejected_bad_kind": 0,
        "ref_items_unchecked": 0,
        "bound_kind_hits": Counter(),
    }
    for index, path in enumerate(transcripts, 1):
        tail = hook._read_transcript_tail(str(path))
        if not tail.strip():
            stats["misses"] += 1
            print(f"  [{arm} {index:2}] empty-tail  {path.name[:44]}")
            continue
        findings = hook._extract_via_ollama(tail)
        if not findings:
            stats["misses"] += 1
            print(f"  [{arm} {index:2}] no-findings/ollama-miss  {path.name[:44]}")
            continue
        stats["scored"] += 1
        stats["per_transcript_findings"].append(len(findings))
        cwd = session_cwd(path)
        if arm == "v2":
            hook._bind_findings(findings, str(path), cwd)
        bound_here = 0
        for f in findings:
            content = str(f.get("content", ""))
            if not content:
                continue
            stats["findings"] += 1
            stats["content_lengths"].append(len(content))
            stats["contents"].append(content.strip().lower())
            row = {
                "arm": arm,
                "transcript": path.name,
                "cwd": cwd,
                "type": f.get("type"),
                "content": content,
                "confidence": f.get("confidence"),
            }
            if arm == "v2":
                refs = f.get("refs") or []
                status = f.get("ref_status", "?")
                tags = f.get("_ref_tags", [])
                bound = [t[len("ref_bound:") :] for t in tags if t.startswith("ref_bound:")]
                rejected = [
                    t[len("ref_rejected:") :] for t in tags if t.startswith("ref_rejected:")
                ]
                unchecked = [
                    t[len("ref_proposed:") :] for t in tags if t.startswith("ref_proposed:")
                ]
                stats["status_counts"][status] += 1
                stats["refs_per_finding"][min(len(refs), 3)] += 1
                stats["ref_items_proposed"] += len(refs)
                stats["ref_items_bound"] += len(bound)
                stats["ref_items_unchecked"] += len(unchecked)
                for item in rejected:
                    reason = item.split(":", 1)[0]
                    if reason == "bad_kind":
                        stats["ref_items_rejected_bad_kind"] += 1
                    else:
                        stats["ref_items_rejected_membership"] += 1
                for b in bound:
                    stats["bound_kind_hits"][b.split(":", 1)[0]] += 1
                if status == "bound":
                    bound_here += 1
                row.update(
                    {
                        "refs": refs,
                        "ref_status": status,
                        "bound": bound,
                        "rejected": rejected,
                        "unchecked": unchecked,
                    }
                )
            out_rows.append(row)
        universe = hook._derive_session_refs(str(path)) or {}
        sizes = " ".join(f"{k}={len(v)}" for k, v in universe.items())
        print(
            f"  [{arm} {index:2}] ok  findings={len(findings)}"
            + (f" bound={bound_here}" if arm == "v2" else "")
            + f"  universe({sizes})  {path.name[:36]}"
        )
    return stats


def pct(numerator: int, denominator: int) -> str:
    return f"{100.0 * numerator / denominator:5.1f}%" if denominator else "  n/a"


def dedup_rate(contents: list[str]) -> float:
    if not contents:
        return 0.0
    return 1.0 - len(set(contents)) / len(contents)


def quality_block(stats: dict) -> str:
    lengths = stats["content_lengths"]
    per_t = stats["per_transcript_findings"]
    lines = [
        f"  transcripts scored      {stats['scored']}  (misses {stats['misses']})",
        f"  findings extracted      {stats['findings']}",
    ]
    if per_t:
        lines.append(f"  findings/transcript     {statistics.mean(per_t):.2f}")
    if lengths:
        lines.append(f"  mean content length     {statistics.mean(lengths):.1f}")
        lines.append(f"  dedup rate              {100 * dedup_rate(stats['contents']):.1f}%")
    return "\n".join(lines) + "\n"


def v2_block(stats: dict) -> str:
    sc = stats["status_counts"]
    n_findings = stats["findings"]
    bound = sc.get("bound", 0)
    no_universe = sc.get("no_ref_universe", 0)
    in_universe = n_findings - no_universe
    proposed = stats["ref_items_proposed"]
    checked = proposed - stats["ref_items_unchecked"]
    rej_m = stats["ref_items_rejected_membership"]
    dist = stats["refs_per_finding"]
    kinds = stats["bound_kind_hits"]
    return (
        "  -- statuses --\n"
        + "".join(f"    {status:22} {count}\n" for status, count in sorted(sc.items()))
        + "  -- bind rate (finding-level) --\n"
        f"    primary  (excl. no_ref_universe)  {bound}/{in_universe}  "
        f"({pct(bound, in_universe)})\n"
        f"    secondary (all-in, D8-comparable) {bound}/{n_findings}  "
        f"({pct(bound, n_findings)})\n"
        "  -- ref items --\n"
        f"    proposed {proposed}  (checked {checked}, unchecked {stats['ref_items_unchecked']})\n"
        f"    bound    {stats['ref_items_bound']}  "
        f"by kind: {dict(kinds) or {}}\n"
        f"    rejected not_in_session {rej_m}  "
        f"(membership-rejection rate {pct(rej_m, checked)})\n"
        f"    rejected bad_kind       {stats['ref_items_rejected_bad_kind']}\n"
        "  -- refs per finding --\n"
        + "".join(f"    {k} refs: {dist.get(k, 0)}\n" for k in range(4))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript-list", help="file of absolute transcript paths")
    parser.add_argument("--samples", type=int, default=40, help="fallback: newest-N selection")
    parser.add_argument("--min-bytes", type=int, default=20_000)
    parser.add_argument(
        "--projects",
        default=str(Path.home() / ".claude" / "projects"),
        help="Claude Code projects dir holding transcript JSONL",
    )
    parser.add_argument("--arm", choices=("v1", "v2", "both"), default="both")
    parser.add_argument("--salt-dir", help="directory of salted transcript copies (v2 arm only)")
    parser.add_argument("--salt-manifest", help="JSON manifest of salted refs per transcript")
    parser.add_argument("--out-jsonl", help="raw per-finding dump (for the aboutness audit)")
    args = parser.parse_args()

    hook = load_hook()
    if args.transcript_list:
        transcripts = [
            Path(line.strip())
            for line in Path(args.transcript_list).read_text().splitlines()
            if line.strip()
        ]
        missing = [p for p in transcripts if not p.is_file()]
        if missing:
            print(f"missing transcripts: {missing}", file=sys.stderr)
            return 1
    else:
        root = Path(args.projects)
        transcripts = sorted(
            (p for p in root.rglob("*.jsonl") if p.stat().st_size > args.min_bytes),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[: args.samples]
    if not transcripts and not args.salt_dir:
        print("no transcripts selected", file=sys.stderr)
        return 1

    out_rows: list[dict] = []
    print(f"transcripts={len(transcripts)}  (real extractor + real binder)\n")

    arm_stats: list[dict] = []
    if transcripts:
        if args.arm in ("v1", "both"):
            arm_stats.append(run_arm(hook, "v1", transcripts, out_rows))
        if args.arm in ("v2", "both"):
            arm_stats.append(run_arm(hook, "v2", transcripts, out_rows))

    salt_stats = None
    salt_refs: dict[str, list[str]] = {}
    if args.salt_dir:
        salted = sorted(Path(args.salt_dir).glob("*.jsonl"))
        if args.salt_manifest:
            salt_refs = json.loads(Path(args.salt_manifest).read_text())
        print(f"\nsalted subset: {len(salted)} transcripts (v2 arm, reported separately)\n")
        salt_rows: list[dict] = []
        salt_stats = run_arm(hook, "v2", salted, salt_rows)
        for row in salt_rows:
            row["arm"] = "v2-salted"
            # Manifest maps transcript name -> distinctive salt VALUES
            # (path tails, pr numbers, spec slugs); substring match keeps
            # this robust to the binder's normalization (absolutized POSIX
            # paths, stripped "#", lowered slugs).
            salts = salt_refs.get(row["transcript"], [])
            row["salt_proposed"] = [r for r in row.get("refs", []) if any(v in r for v in salts)]
            row["salt_bound"] = [b for b in row.get("bound", []) if any(v in b for v in salts)]
        out_rows.extend(salt_rows)

    print("\n" + "=" * 62)
    print("mcv D-5 re-probe report")
    print("=" * 62)
    for stats in arm_stats:
        print(f"\narm {stats['arm']}:")
        print(quality_block(stats), end="")
        if stats["arm"] == "v2":
            print(v2_block(stats), end="")
    if salt_stats is not None:
        print("\narm v2 SALTED (separate — never blended):")
        print(quality_block(salt_stats), end="")
        print(v2_block(salt_stats), end="")
        salted_rows = [r for r in out_rows if r["arm"] == "v2-salted"]
        n_prop = sum(1 for r in salted_rows if r.get("salt_proposed"))
        n_bound = sum(1 for r in salted_rows if r.get("salt_bound"))
        print("  -- salt uptake (aboutness failures by construction) --")
        print(f"    findings proposing a salt ref  {n_prop}/{len(salted_rows)}")
        print(f"    findings BINDING a salt ref    {n_bound}/{len(salted_rows)}")
    print("=" * 62)

    if args.out_jsonl:
        out_path = Path(args.out_jsonl)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            for row in out_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"raw rows -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
