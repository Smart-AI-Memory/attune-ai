#!/usr/bin/env python3
"""Measure whether the local extraction model reliably emits entity refs.

Answers OQ1 of docs/specs/memory-claim-verification: if `llama3.1:8b`
cannot reliably emit `refs` alongside a finding, then heuristic back-fill
from `content` is the permanent mechanism rather than a migration step,
and requirement R3 (structured, verified claims) may not be viable.

This is a MEASUREMENT, not a test. It replays real session transcripts
through the real tail-extraction path and the real Ollama call, then
reports rates. Run it; read the number; rule on OQ1.

    python scripts/measure_stash_refs.py --samples 15

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "plugin" / "hooks" / "session_stash.py"

#: Entities a finding might name. These same patterns are the candidate
#: heuristic back-fill, so the model's refs can be scored against them.
ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("pr", re.compile(r"#(\d{2,6})\b")),
    ("sha", re.compile(r"\b([0-9a-f]{7,40})\b")),
    ("file", re.compile(r"\b((?:src|tests|scripts|docs|plugin)/[\w./-]+\.\w+)")),
    ("spec", re.compile(r"docs/specs/([\w-]+)")),
]

#: The current prompt with a refs clause appended. Deliberately a MINIMAL
#: delta from the shipped prompt — measuring the model, not prompt craft.
REFS_CLAUSE = (
    '- refs is a list of entities the finding is about, each "kind:value".\n'
    "  Kinds: pr (pr:1666), sha (sha:1f6553e), file (file:src/x.py),\n"
    "  spec (spec:memory-recall-eval). Include ONLY entities that appear\n"
    "  in the transcript. Empty list if the finding names none.\n"
)


def load_hook():
    """Load the Stop-hook module so the REAL tail extractor is used."""
    spec = importlib.util.spec_from_file_location("_stash_hook", HOOK)
    if spec is None or spec.loader is None:  # pragma: no cover - env guard
        raise RuntimeError(f"cannot load {HOOK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_stash_hook"] = module
    spec.loader.exec_module(module)
    return module


def build_prompt(text: str) -> str:
    """The shipped prompt plus the refs clause and a refs field."""
    return (
        "You are extracting durable memory from a coding session transcript.\n"
        "Return ONLY JSON of the form "
        '{"findings": [{"type": "...", "content": "...", "refs": ["..."]}]}.\n'
        "Rules:\n"
        "- At most 5 findings; fewer is better. Skip chit-chat and routine steps.\n"
        "- Each finding is a single reusable insight worth recalling next session.\n"
        "- type is one of: decision, pattern, bug, reference, note.\n"
        "- content is one concise sentence, <= 280 chars, no secrets.\n"
        f"{REFS_CLAUSE}"
        "- PROVENANCE: extract only what the ASSISTANT concluded or the USER\n"
        "  decided IN THIS SESSION.\n\n"
        f"TRANSCRIPT TAIL:\n{text}\n"
    )


def call_ollama(prompt: str, model: str, timeout: int) -> tuple[dict | None, float]:
    """Return (parsed JSON, seconds). None when unavailable or unparseable."""
    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return json.loads(body.get("response", "")), time.monotonic() - started
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None, time.monotonic() - started


def entities_in(text: str) -> set[str]:
    """Heuristic back-fill: the refs derivable from text alone."""
    found: set[str] = set()
    for kind, pattern in ENTITY_PATTERNS:
        for match in pattern.findall(text):
            found.add(f"{kind}:{match}")
    return found


@dataclass
class Totals:
    transcripts: int = 0
    parse_ok: int = 0
    parse_fail: int = 0
    findings: int = 0
    with_refs: int = 0
    refs_emitted: int = 0
    refs_wellformed: int = 0
    refs_grounded: int = 0
    findings_backfillable: int = 0
    findings_model_got: int = 0
    durations: list[float] = field(default_factory=list)


def score(findings: list[dict], tail: str, totals: Totals) -> None:
    """Score one transcript's findings against the transcript text."""
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        content = str(finding.get("content", ""))
        if not content:
            continue
        totals.findings += 1

        refs = finding.get("refs")
        refs = [str(r) for r in refs] if isinstance(refs, list) else []
        if refs:
            totals.with_refs += 1
        totals.refs_emitted += len(refs)

        for ref in refs:
            if re.fullmatch(r"(pr|sha|file|spec):.+", ref):
                totals.refs_wellformed += 1
                # Grounded = the ref's value actually appears in the tail.
                if ref.split(":", 1)[1] in tail:
                    totals.refs_grounded += 1

        # Could a pure regex over the CONTENT have produced a ref?
        backfill = entities_in(content)
        if backfill:
            totals.findings_backfillable += 1
            if refs:
                totals.findings_model_got += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=15)
    parser.add_argument(
        "--min-bytes",
        type=int,
        default=20_000,
        help="skip transcripts smaller than this (isolates substantial sessions)",
    )
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--timeout", type=int, default=180)
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

    totals = Totals()
    print(f"model={args.model}  samples={len(transcripts)}\n")

    for index, path in enumerate(transcripts, 1):
        tail = hook._read_transcript_tail(str(path))
        if not tail.strip():
            continue
        totals.transcripts += 1
        parsed, seconds = call_ollama(build_prompt(tail), args.model, args.timeout)
        totals.durations.append(seconds)

        if not isinstance(parsed, dict) or not isinstance(parsed.get("findings"), list):
            totals.parse_fail += 1
            print(f"  [{index:2}] PARSE_FAIL  {seconds:5.1f}s  {path.name[:40]}")
            continue

        totals.parse_ok += 1
        findings = parsed["findings"]
        score(findings, tail, totals)
        refs_here = sum(1 for f in findings if isinstance(f, dict) and f.get("refs"))
        print(
            f"  [{index:2}] ok  {seconds:5.1f}s  findings={len(findings)} "
            f"with_refs={refs_here}  {path.name[:40]}"
        )

    def pct(numerator: int, denominator: int) -> str:
        return f"{100.0 * numerator / denominator:5.1f}%" if denominator else "  n/a"

    print("\n" + "=" * 62)
    print("OQ1 — does the 8B model reliably emit refs?")
    print("=" * 62)
    print(f"transcripts scored      {totals.transcripts}")
    print(
        f"JSON parse ok           {totals.parse_ok}  ({pct(totals.parse_ok, totals.transcripts)})"
    )
    print(f"findings extracted      {totals.findings}")
    print(
        f"findings WITH refs      {totals.with_refs}  "
        f"({pct(totals.with_refs, totals.findings)})   <-- the headline"
    )
    print(f"refs emitted (total)    {totals.refs_emitted}")
    print(
        f"  well-formed           {totals.refs_wellformed}  "
        f"({pct(totals.refs_wellformed, totals.refs_emitted)})"
    )
    print(
        f"  grounded in tail      {totals.refs_grounded}  "
        f"({pct(totals.refs_grounded, totals.refs_emitted)})  "
        "(else: hallucinated)"
    )
    print(
        f"heuristic-backfillable  {totals.findings_backfillable}  "
        f"({pct(totals.findings_backfillable, totals.findings)} of findings)"
    )
    print(
        f"  model also got those  {totals.findings_model_got}  "
        f"({pct(totals.findings_model_got, totals.findings_backfillable)})"
    )
    if totals.durations:
        print(f"mean latency            {sum(totals.durations)/len(totals.durations):.1f}s")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
