#!/usr/bin/env python3
"""Measure the D7 rider-(c) gate: can findings bind to derived refs?

memory-claim-verification D7 adopted per-finding matching (candidate
2) with rider (c): BEFORE the P1 matcher is built, measure what
fraction of real raw-tier findings deterministically match at least
one ref derivable from their session's tool_use records. A low hit
rate (<50%) reopens the design conversation (2-with-fallback vs 3).

This is a MEASUREMENT, not a test (same discipline as OQ1's
measure_stash_refs.py). It replays real session transcripts through
the REAL shipped extraction path (session_stash._extract_via_ollama),
derives each session's ref-set from its tool_use records, and matches
finding text against the derived set with deterministic rules only —
no LLM anywhere in the binding path.

    python scripts/probe_ref_binding.py --samples 40

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "plugin" / "hooks" / "session_stash.py"

#: Ref kinds derivable from tool_use records (mirrors the OQ1 probe's
#: third-mechanism analysis; symbol-kind is deliberately NOT probed —
#: honest limit, P1 may add it).
COMMAND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("pr", re.compile(r"(?:#|pull/)(\d{2,6})\b")),
    ("sha", re.compile(r"\b([0-9a-f]{8,40})\b")),
    ("file", re.compile(r"\b((?:src|tests|scripts|docs|plugin|content)/[\w./-]+\.\w+)")),
    ("spec", re.compile(r"docs/specs/([\w-]+)")),
]

#: Basenames too generic to bind on — the claude-seat over-match guard.
STOPLIST = {
    "main",
    "test",
    "tests",
    "src",
    "docs",
    "init",
    "setup",
    "index",
    "utils",
    "readme",
    "claude",
    "config",
    "requirements",
    "design",
    "tasks",
    "decisions",
}
MIN_BASENAME = 5


def load_hook():
    """Load the Stop-hook module so the REAL extraction path is used."""
    spec = importlib.util.spec_from_file_location("_stash_hook", HOOK)
    if spec is None or spec.loader is None:  # pragma: no cover - env guard
        raise RuntimeError(f"cannot load {HOOK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_stash_hook"] = module
    spec.loader.exec_module(module)
    return module


def derive_refs(transcript: Path) -> dict[str, set[str]]:
    """Derive the session ref-set from tool_use records (deterministic).

    Walks every JSONL line, collects tool_use inputs: file-path keys
    directly, and pr/sha/file/spec patterns from command strings.
    """
    refs: dict[str, set[str]] = {"pr": set(), "sha": set(), "file": set(), "spec": set()}
    with open(transcript, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"tool_use"' not in line:
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            content = record.get("message", {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                inputs = block.get("input")
                if not isinstance(inputs, dict):
                    continue
                for key, value in inputs.items():
                    if not isinstance(value, str):
                        continue
                    if key in ("file_path", "path", "notebook_path"):
                        refs["file"].add(value)
                        continue
                    for kind, pattern in COMMAND_PATTERNS:
                        for match in pattern.findall(value):
                            refs[kind].add(match)
    return refs


def match_finding(content: str, refs: dict[str, set[str]]) -> list[str]:
    """Deterministic per-finding matching (the D7 matcher family).

    Exact path / basename / pr-number / sha-prefix / spec-slug only.
    Returns the matched refs as "kind:value" strings.
    """
    matched: list[str] = []
    lower = content.lower()
    words = set(re.findall(r"[\w.-]+", lower))

    for number in refs["pr"]:
        if re.search(rf"(?:#|\bpr[ #]?){number}\b", lower):
            matched.append(f"pr:{number}")

    hex_tokens = re.findall(r"\b[0-9a-f]{7,40}\b", lower)
    for sha in refs["sha"]:
        if any(sha.startswith(token) or token.startswith(sha) for token in hex_tokens):
            matched.append(f"sha:{sha[:12]}")

    for path in refs["file"]:
        base = Path(path).name.lower()
        stem = Path(path).stem.lower()
        if path.lower() in lower:
            matched.append(f"file:{path}")
        elif (
            len(stem) >= MIN_BASENAME and stem not in STOPLIST and (base in words or stem in words)
        ):
            matched.append(f"file:{path}")

    for slug in refs["spec"]:
        if slug.lower() in lower:
            matched.append(f"spec:{slug}")
    return matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--min-bytes", type=int, default=20_000)
    parser.add_argument(
        "--projects",
        default=str(Path.home() / ".claude" / "projects"),
        help="Claude Code projects dir holding transcript JSONL",
    )
    args = parser.parse_args()

    hook = load_hook()
    root = Path(args.projects)
    transcripts = sorted(
        (p for p in root.rglob("*.jsonl") if p.stat().st_size > args.min_bytes),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[: args.samples]
    if not transcripts:
        print(f"no transcripts found under {root}", file=sys.stderr)
        return 1

    n_scored = 0
    n_findings = 0
    n_bound = 0
    kind_hits = {"pr": 0, "sha": 0, "file": 0, "spec": 0}
    bound_samples: list[tuple[str, list[str]]] = []
    unbound_samples: list[str] = []

    print(f"samples={len(transcripts)}  (real extractor + deterministic matcher)\n")
    for index, path in enumerate(transcripts, 1):
        tail = hook._read_transcript_tail(str(path))
        if not tail.strip():
            continue
        findings = hook._extract_via_ollama(tail)
        if not findings:
            print(f"  [{index:2}] no-findings/ollama-miss  {path.name[:44]}")
            continue
        n_scored += 1
        refs = derive_refs(path)
        bound_here = 0
        for finding in findings:
            content = str(finding.get("content", ""))
            if not content:
                continue
            n_findings += 1
            matches = match_finding(content, refs)
            if matches:
                n_bound += 1
                bound_here += 1
                for m in matches:
                    kind_hits[m.split(":", 1)[0]] += 1
                bound_samples.append((content, matches))
            else:
                unbound_samples.append(content)
        print(
            f"  [{index:2}] ok  findings={len(findings)} bound={bound_here}  "
            f"refs(pr={len(refs['pr'])} sha={len(refs['sha'])} "
            f"file={len(refs['file'])} spec={len(refs['spec'])})  {path.name[:36]}"
        )

    def pct(numerator: int, denominator: int) -> str:
        return f"{100.0 * numerator / denominator:5.1f}%" if denominator else "  n/a"

    print("\n" + "=" * 62)
    print("D7 rider-(c) — per-finding deterministic bind rate")
    print("=" * 62)
    print(f"transcripts scored      {n_scored}")
    print(f"findings extracted      {n_findings}")
    print(f"findings BOUND (>=1)    {n_bound}  ({pct(n_bound, n_findings)})   <-- the gate number")
    print(
        f"  by kind: pr={kind_hits['pr']} sha={kind_hits['sha']} file={kind_hits['file']} spec={kind_hits['spec']}"
    )
    print(
        f"gate verdict            {'PROCEED to P1' if n_findings and n_bound / n_findings >= 0.5 else 'REOPEN design (<50%)'}"
    )

    rng = random.Random(42)
    print("\n--- over-match spot-check (10 random bound findings) ---")
    for content, matches in rng.sample(bound_samples, min(10, len(bound_samples))):
        print(f"  BOUND {matches}\n        {content[:160]}")
    print("\n--- lossiness sample (5 random unbound findings) ---")
    for content in rng.sample(unbound_samples, min(5, len(unbound_samples))):
        print(f"  UNBOUND {content[:160]}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
