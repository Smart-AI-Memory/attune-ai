"""Phase 0 measurement harness for agent-surface-rebalance spec.

Instruments a workflow's SDK invocation to capture intermediate
AssistantMessage bytes separately from final ResultMessage bytes,
plus token usage and cost. Writes a JSON record per run.

See docs/specs/agent-surface-rebalance/tasks.md Phase 0 task 1.

Usage::

    python scripts/phase0/measure.py security-audit src/attune/security
    python scripts/phase0/measure.py refactor-plan  src/attune/security

Each invocation writes a timestamped JSON file under
docs/specs/agent-surface-rebalance/runs/.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# --- side-channel byte counters -------------------------------------
# Populated by the wrapped collect_agent_output below.
_STATS: dict[str, Any] = {
    "assistant_calls": 0,
    "assistant_bytes": 0,
    "result_calls": 0,
    "result_bytes": 0,
    "messages_total": 0,
    "tool_use_messages": 0,
    "other_messages": 0,
}


def _install_instrumentation() -> None:
    """Monkey-patch collect_agent_output to count bytes per message.

    The patched version still delegates to the real implementation so
    the workflow runs normally; we just observe byte sizes on the way
    through.
    """
    import claude_agent_sdk

    from attune.workflows import agent_sdk_adapter

    real_collect = agent_sdk_adapter.collect_agent_output

    def instrumented(
        message: Any,
        assistant_parts: list[str],
        result_parts: list[str],
    ):
        _STATS["messages_total"] += 1
        # Snapshot list lengths so we can detect what was appended.
        ap_before = len(assistant_parts)
        rp_before = len(result_parts)

        out = real_collect(message, assistant_parts, result_parts)

        new_ap = assistant_parts[ap_before:]
        new_rp = result_parts[rp_before:]
        if new_ap:
            _STATS["assistant_calls"] += 1
            for s in new_ap:
                _STATS["assistant_bytes"] += len(s.encode("utf-8"))
        if new_rp:
            _STATS["result_calls"] += 1
            for s in new_rp:
                _STATS["result_bytes"] += len(s.encode("utf-8"))

        # Classify other message types for awareness.
        if not isinstance(
            message,
            (
                claude_agent_sdk.AssistantMessage,
                claude_agent_sdk.ResultMessage,
            ),
        ):
            _STATS["other_messages"] += 1
            # Heuristic: many SDK messages carry tool use.
            content = getattr(message, "content", None)
            if content:
                _STATS["tool_use_messages"] += 1

        return out

    agent_sdk_adapter.collect_agent_output = instrumented


def _reset_stats() -> None:
    for k in _STATS:
        _STATS[k] = 0


_WORKFLOWS: dict[str, str] = {
    "security-audit": "attune.workflows.security_audit:SecurityAuditWorkflow",
    "refactor-plan": "attune.workflows.refactor_plan:RefactorPlanWorkflow",
}


def _resolve_workflow(name: str):
    spec = _WORKFLOWS.get(name)
    if not spec:
        raise SystemExit(f"unknown workflow {name!r}; choose from {list(_WORKFLOWS)}")
    module_path, _, class_name = spec.partition(":")
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


async def _run(workflow_name: str, path: str, depth: str) -> dict[str, Any]:
    _install_instrumentation()
    _reset_stats()

    Workflow = _resolve_workflow(workflow_name)
    wf = Workflow()

    t0 = time.perf_counter()
    result = await wf.execute(path=path, depth=depth)
    elapsed_s = time.perf_counter() - t0

    cost_report = getattr(result, "cost_report", None)
    metadata = getattr(result, "metadata", {}) or {}
    final_output = getattr(result, "final_output", "")
    summary = getattr(result, "summary", "")

    final_output_text = (
        final_output if isinstance(final_output, str) else json.dumps(final_output, default=str)
    )

    record = {
        "workflow": workflow_name,
        "path": path,
        "depth": depth,
        "elapsed_seconds": elapsed_s,
        "success": getattr(result, "success", None),
        "stats": dict(_STATS),
        "cost_usd": getattr(cost_report, "total_cost", None) if cost_report else None,
        "num_turns": metadata.get("num_turns"),
        "session_id": metadata.get("session_id"),
        "duration_api_ms": metadata.get("duration_api_ms"),
        "subagent_transcripts_kb": (
            sum(
                len(s.encode("utf-8"))
                for texts in metadata.get("subagent_transcripts", {}).values()
                for s in texts
            )
            / 1024
            if metadata.get("subagent_transcripts")
            else 0
        ),
        "final_output_bytes": len(final_output_text.encode("utf-8")),
        "summary_bytes": len(summary.encode("utf-8")) if isinstance(summary, str) else 0,
    }

    # Ratio: how much intermediate orchestrator text vs final summary
    summary_bytes = record["summary_bytes"] or record["final_output_bytes"]
    if summary_bytes:
        record["intermediate_to_summary_ratio"] = record["stats"]["assistant_bytes"] / summary_bytes
    else:
        record["intermediate_to_summary_ratio"] = None

    return record


def main(argv: list[str]) -> int:
    if len(argv) < 3 or len(argv) > 4:
        print(__doc__, file=sys.stderr)
        print(
            "\nUsage: python scripts/phase0/measure.py <workflow> <path> [depth]",
            file=sys.stderr,
        )
        return 2

    workflow_name = argv[1]
    path = argv[2]
    depth = argv[3] if len(argv) == 4 else "standard"

    out_dir = REPO_ROOT / "docs" / "specs" / "agent-surface-rebalance" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)

    record = asyncio.run(_run(workflow_name, path, depth))

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"{workflow_name}-{depth}-{ts}.json"
    out_file.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps(record, indent=2, default=str))
    print(f"\nSaved: {out_file.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
