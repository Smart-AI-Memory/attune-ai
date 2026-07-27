"""Benchmark Fable 5 spec-packet generation — FABLE_SPEC_WORKFLOW_TODO item 1.

Measures the evidence the routing matrix needs BEFORE a default
whole-spec vs per-document strategy is picked (see
docs/process/FABLE_SPEC_WORKFLOW_TODO.md, "Measure before setting the
generation budget"): time to first stream event, time to first text
delta, total duration, input/output token counts, stop reason, file
markers found, and the failure mode when a bound trips.

Three representative packets, all authoring the same feature brief:

- ``one``  — requirements.md only (1 file marker expected)
- ``four`` — requirements + design + tasks + decisions (4 markers)
- ``five`` — the four spec docs + the .claude/plans XML plan (5 markers)

Each run streams through the beta namespace with the fable fallbacks
opt-in (attune.model_tiers.fable_extras) and is bounded twice: a
first/inter-event read timeout (httpx read timeout) and a total-run
wall clock enforced in the event loop. A tripped bound is recorded as
a failure mode, never retried silently — the same strategy is never
attempted twice in one invocation.

Results land as JSON under --out (default
docs/process/fable-spec-benchmark/) plus a markdown summary table on
stdout for the decision matrix.

Usage::

    set -a && source ~/.attune/anthropic.env && set +a
    PYTHONPATH=src python scripts/benchmark_fable_spec.py --packet all

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from anthropic import Anthropic

from attune.model_tiers import fable_extras

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "docs" / "process" / "fable-spec-benchmark"
DEFAULT_MODEL = "claude-fable-5"

# Registry premium-tier pricing (src/attune/models/registry.py) — per
# million tokens; used only for the report, not billing.
INPUT_USD_PER_M = 10.00
OUTPUT_USD_PER_M = 50.00

FILE_MARKER = re.compile(r"^=== FILE: (\S+) ===$", re.MULTILINE)

FEATURE_BRIEF = """\
Feature: bounded Fable drafting runner for spec authoring.

Context: attune-ai orchestrates spec authoring across providers. The
current whole-spec Fable call can sit silent for minutes with no
progress signal, then gets interrupted and retried blind. We need a
drafting runner that streams progress, enforces a time-to-first-event
limit and a total-run limit, switches to a preselected per-document
strategy after one first-event timeout (never repeating the same
silent whole-spec call), captures the exact provider/model/auth
failure without exposing secrets, and validates required file markers
and output-size limits before materializing any file.

Constraints: Python 3.10+, anthropic SDK, no new runtime dependencies,
must degrade cleanly when the API key is absent, and scratch artifacts
must never appear in the repository working tree.
"""

DOC_INSTRUCTIONS = {
    "requirements": (
        "docs/specs/bounded-fable-runner/requirements.md — user stories, "
        "acceptance criteria, out-of-scope list"
    ),
    "design": (
        "docs/specs/bounded-fable-runner/design.md — architecture, the two "
        "timeout bounds, strategy-switch state machine, error taxonomy"
    ),
    "tasks": (
        "docs/specs/bounded-fable-runner/tasks.md — ordered implementation "
        "tasks T1..Tn with dependencies and per-task acceptance"
    ),
    "decisions": (
        "docs/specs/bounded-fable-runner/decisions.md — decision log with "
        "one entry per open question, status, and rationale"
    ),
    "plan": (
        ".claude/plans/bounded-fable-runner.md — XML execution plan "
        "(<plan><task id=..>) mirroring tasks.md"
    ),
}

PACKETS: dict[str, list[str]] = {
    "one": ["requirements"],
    "four": ["requirements", "design", "tasks", "decisions"],
    "five": ["requirements", "design", "tasks", "decisions", "plan"],
}

PACKET_MAX_TOKENS = {"one": 32_000, "four": 64_000, "five": 64_000}


def build_prompt(packet: str) -> str:
    """Assemble the spec-authoring prompt for one packet."""
    docs = PACKETS[packet]
    doc_lines = "\n".join(f"- {DOC_INSTRUCTIONS[d]}" for d in docs)
    return (
        f"{FEATURE_BRIEF}\n"
        f"Write the following {len(docs)} document(s) in full:\n{doc_lines}\n\n"
        "Output format (mandatory): precede EVERY document with a line of "
        "exactly `=== FILE: <path> ===` on its own line, then the complete "
        "markdown content. No prose outside the documents."
    )


def run_packet(
    client: Anthropic,
    packet: str,
    model: str,
    total_timeout: float,
) -> dict[str, Any]:
    """Stream one packet generation, recording timings and failure mode."""
    expected = len(PACKETS[packet])
    result: dict[str, Any] = {
        "packet": packet,
        "model": model,
        "expected_files": expected,
        "ttfe_s": None,
        "ttft_s": None,
        "total_s": None,
        "input_tokens": None,
        "output_tokens": None,
        "output_chars": 0,
        "stop_reason": None,
        "markers_found": 0,
        "markers_ok": False,
        "failure_mode": None,
        "cost_usd": None,
    }
    text_parts: list[str] = []
    start = time.monotonic()
    try:
        stream = client.beta.messages.create(
            model=model,
            max_tokens=PACKET_MAX_TOKENS[packet],
            messages=[{"role": "user", "content": build_prompt(packet)}],
            stream=True,
            **fable_extras(model),
        )
        for event in stream:
            now = time.monotonic()
            if result["ttfe_s"] is None:
                result["ttfe_s"] = round(now - start, 2)
            if now - start > total_timeout:
                result["failure_mode"] = "total_timeout"
                break
            etype = getattr(event, "type", "")
            if etype == "message_start":
                usage = event.message.usage
                result["input_tokens"] = usage.input_tokens
            elif etype == "content_block_delta":
                delta_text = getattr(event.delta, "text", None)
                if delta_text:
                    if result["ttft_s"] is None:
                        result["ttft_s"] = round(now - start, 2)
                    text_parts.append(delta_text)
            elif etype == "message_delta":
                result["stop_reason"] = getattr(event.delta, "stop_reason", None)
                usage = getattr(event, "usage", None)
                if usage is not None:
                    result["output_tokens"] = usage.output_tokens
    except httpx.ReadTimeout:
        result["failure_mode"] = (
            "first_event_timeout" if result["ttfe_s"] is None else "inter_event_timeout"
        )
    except KeyboardInterrupt:
        result["failure_mode"] = "interrupted"
        raise
    except Exception as exc:  # noqa: BLE001 — failure MODE is the datum here
        result["failure_mode"] = f"exception:{type(exc).__name__}: {exc}"

    result["total_s"] = round(time.monotonic() - start, 2)
    text = "".join(text_parts)
    result["output_chars"] = len(text)
    result["markers_found"] = len(FILE_MARKER.findall(text))
    result["markers_ok"] = result["markers_found"] == expected and result["failure_mode"] is None
    if result["input_tokens"] is not None and result["output_tokens"] is not None:
        result["cost_usd"] = round(
            result["input_tokens"] * INPUT_USD_PER_M / 1e6
            + result["output_tokens"] * OUTPUT_USD_PER_M / 1e6,
            4,
        )
    return result


def summary_table(results: list[dict[str, Any]]) -> str:
    """Render the decision-matrix rows as a markdown table."""
    header = (
        "| packet | files | TTFE (s) | TTFT (s) | total (s) | in tok | "
        "out tok | markers | stop | failure | cost ($) |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|"
    )
    rows = []
    for r in results:
        rows.append(
            f"| {r['packet']} | {r['markers_found']}/{r['expected_files']} "
            f"| {r['ttfe_s']} | {r['ttft_s']} | {r['total_s']} "
            f"| {r['input_tokens']} | {r['output_tokens']} "
            f"| {'ok' if r['markers_ok'] else 'BAD'} | {r['stop_reason']} "
            f"| {r['failure_mode'] or '-'} | {r['cost_usd']} |"
        )
    return "\n".join([header, *rows])


def validate_out_dir(raw: str) -> Path:
    """Resolve --out and require it to stay inside the repository."""
    out = Path(raw).resolve()
    if not out.is_relative_to(REPO_ROOT):
        raise SystemExit(f"--out must be inside the repo ({REPO_ROOT}); got {out}")
    return out


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--packet", choices=[*PACKETS, "all"], default="all")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--first-event-timeout",
        type=float,
        default=90.0,
        help="httpx read timeout — bounds first event AND inter-event gaps (s)",
    )
    parser.add_argument("--total-timeout", type=float, default=600.0)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_dir = validate_out_dir(args.out)
    client = Anthropic(
        timeout=httpx.Timeout(connect=10.0, read=args.first_event_timeout, write=30.0, pool=10.0),
        max_retries=0,  # a retry would double-spend; failure mode is the datum
    )

    packets = list(PACKETS) if args.packet == "all" else [args.packet]
    results = []
    for packet in packets:
        print(f"--- running packet '{packet}' ({len(PACKETS[packet])} file(s)) ...", flush=True)
        result = run_packet(client, packet, args.model, args.total_timeout)
        results.append(result)
        print(json.dumps(result, indent=2), flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"results-{stamp}.json"
    out_file.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {out_file}\n\n{summary_table(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
