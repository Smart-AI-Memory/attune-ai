"""Measure stash-extraction provenance quality against real transcripts.

The capture-side companion to ``memory_savings.py`` (which measures the
retrieval side). Born from the 2026-07-05 garbled-stash incident
(issue #1263, fixed in #1269): the Stop-hook extractor promoted content
a session merely *read* into "findings". This benchmark replays real
session transcripts through the extractor and machine-scores each
finding's provenance:

  ambient-sourced  — content shingles overlap text that appears ONLY
                     inside tool_result/tool_use blocks (never spoken
                     by the assistant or user): the #1263 failure class
  asserted-sourced — overlaps genuine assistant/user turn text
  unmatched        — paraphrase; needs human labeling (auto-score is a
                     LOWER BOUND on the true ambient rate)

Extraction is deterministic (temperature 0, seed 42, injected by
intercepting the extractor's own Ollama call), so runs are comparable.

Usage::

    # score the current extractor over the 8 most recent transcripts
    python benchmarks/stash_precision.py --recent 8

    # A/B the current extractor against any prior revision
    python benchmarks/stash_precision.py --recent 8 --compare-ref v10.0.0

    # incident replay: truncate a transcript at an anchor phrase so the
    # extractor sees exactly what a specific Stop-hook firing saw
    python benchmarks/stash_precision.py path/to/transcript.jsonl \
        --anchor "Housekeeping run complete"

Requires a local Ollama with the extractor's model (default
``llama3.1:8b``); transcripts stay on this machine. Frozen baseline:
``stash_precision_results_2026-07-06.md`` (old 5% -> new 0% ambient).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "plugin" / "hooks" / "session_stash.py"
SHINGLE = 6  # words per shingle for overlap matching

_REAL_URLOPEN = urllib.request.urlopen


def _deterministic_urlopen(req, timeout=0):
    """Forward the extractor's Ollama call with temp 0 + fixed seed."""
    body = json.loads(req.data.decode("utf-8"))
    body["options"] = {"temperature": 0, "seed": 42}
    req2 = urllib.request.Request(
        req.full_url, data=json.dumps(body).encode("utf-8"), headers=dict(req.headers)
    )
    return _REAL_URLOPEN(req2, timeout=max(timeout, 120))


def _load_extractor(label: str, source_path: Path):
    spec = importlib.util.spec_from_file_location(f"stash_{label}", source_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"stash_{label}"] = mod
    spec.loader.exec_module(mod)
    return mod


def _extractor_from_ref(ref: str, tmpdir: Path) -> Path:
    src = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{ref}:plugin/hooks/session_stash.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    out = tmpdir / f"session_stash_{re.sub(r'[^A-Za-z0-9]', '_', ref)}.py"
    out.write_text(src, encoding="utf-8")
    return out


def _shingles(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(words[i : i + SHINGLE]) for i in range(max(0, len(words) - SHINGLE + 1))}


def _corpus_split(transcript_path: Path) -> tuple[str, str]:
    """Split transcript text into (spoken, tool-only) corpora."""
    spoken: list[str] = []
    tool: list[str] = []

    def walk(content, in_tool: bool):
        if isinstance(content, str):
            (tool if in_tool else spoken).append(content)
        elif isinstance(content, list):
            for p in content:
                walk(p, in_tool)
        elif isinstance(content, dict):
            flag = in_tool or content.get("type") in {"tool_result", "tool_use"}
            t = content.get("text")
            if isinstance(t, str):
                (tool if flag else spoken).append(t)
            if content.get("content") is not None:
                walk(content["content"], flag)
            if content.get("input") is not None:
                walk(json.dumps(content.get("input")), flag)

    with transcript_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            msg = rec.get("message")
            content = msg.get("content") if isinstance(msg, dict) else rec.get("content")
            walk(content, False)
    return " ".join(spoken), " ".join(tool)


def _classify(finding: str, spoken_sh: set, tool_sh: set) -> str:
    f_sh = _shingles(finding)
    if not f_sh:
        return "unmatched"
    hits_spoken = len(f_sh & spoken_sh)
    hits_tool_only = len(f_sh & (tool_sh - spoken_sh))
    if hits_tool_only > 0 and hits_tool_only >= hits_spoken:
        return "ambient-sourced"
    if hits_spoken > 0:
        return "asserted-sourced"
    return "unmatched"


def _window(transcript: Path, anchor: str, tmpdir: Path) -> Path:
    """Truncate a transcript at the first record containing ``anchor``."""
    kept: list[str] = []
    with transcript.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            kept.append(line)
            if anchor in line:
                break
        else:
            raise SystemExit(f"anchor {anchor!r} not found in {transcript}")
    out = tmpdir / f"window_{transcript.stem}.jsonl"
    out.write_text("".join(kept), encoding="utf-8")
    return out


def _recent_transcripts(n: int) -> list[Path]:
    base = Path.home() / ".claude" / "projects"
    cands = sorted(
        (p for p in base.rglob("*.jsonl") if p.stat().st_size > 100_000),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return cands[:n]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcripts", nargs="*", type=Path)
    ap.add_argument("--recent", type=int, help="auto-pick the N most recent transcripts")
    ap.add_argument("--compare-ref", help="git ref of a prior extractor to A/B against")
    ap.add_argument("--anchor", help="truncate transcript(s) at this phrase (incident replay)")
    ap.add_argument("--out", type=Path, default=Path("stash_precision_review.md"))
    args = ap.parse_args()

    urllib.request.urlopen = _deterministic_urlopen

    transcripts = list(args.transcripts) or _recent_transcripts(args.recent or 8)
    if not transcripts:
        raise SystemExit("no transcripts found")

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        variants = [("current", _load_extractor("current", HOOK_PATH))]
        if args.compare_ref:
            ref_path = _extractor_from_ref(args.compare_ref, tmpdir)
            variants.insert(0, (args.compare_ref, _load_extractor("ref", ref_path)))

        totals = {name: {"n": 0, "ambient": 0} for name, _ in variants}
        lines = ["# Stash-precision run", ""]
        for tp in transcripts:
            src = _window(tp, args.anchor, tmpdir) if args.anchor else tp
            spoken, tool = _corpus_split(src)
            spoken_sh, tool_sh = _shingles(spoken), _shingles(tool)
            lines.append(f"## {tp.parent.name[-24:]}/{tp.stem[:8]}")
            for name, mod in variants:
                tail = mod._read_transcript_tail(str(src))
                findings = mod._extract_via_ollama(tail)
                mode = "ollama" if findings is not None else "heuristic"
                if findings is None:
                    findings = mod._extract_heuristic(tail)
                findings = mod._normalize(findings)
                lines.append(f"\n**{name}** ({mode}):")
                for f in findings:
                    auto = _classify(f["content"], spoken_sh, tool_sh)
                    totals[name]["n"] += 1
                    totals[name]["ambient"] += auto == "ambient-sourced"
                    flag = " !AMBIENT" if auto == "ambient-sourced" else ""
                    lines.append(f"- [{f['type']}] {f['content']}{flag}  `auto:{auto}`")
                print(f"[{tp.stem[:8]}] {name}: {len(findings)} findings ({mode})", flush=True)
            lines.append("")

        lines.append("## Totals (auto-score = lower bound; label `unmatched` by hand)")
        for name, t in totals.items():
            pct = (100 * t["ambient"] / t["n"]) if t["n"] else 0.0
            lines.append(f"- {name}: {t['n']} findings, {t['ambient']} ambient ({pct:.0f}%)")
        args.out.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nwrote {args.out}")
        for name, t in totals.items():
            pct = (100 * t["ambient"] / t["n"]) if t["n"] else 0.0
            print(f"{name}: ambient {t['ambient']}/{t['n']} ({pct:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
