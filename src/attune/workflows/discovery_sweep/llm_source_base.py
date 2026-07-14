"""Shared base for LLM-backed FindingSource adapters.

Three exports:

* :data:`STRUCTURED_EMIT_FOOTER` — prompt augmentation appended to a
  wrapped workflow's system prompt at the workflow-INSTANCE level
  so the model emits a parseable ``findings`` JSON block alongside
  its prose.
* :func:`parse_findings_json` — tolerant parser that returns either
  the structured findings or a single text-only-fallback Finding.
* :class:`LLMSource` — optional marker base class setting
  ``is_llm = True`` and ``budget_multiplier = 1.0``.

Phase 2A ships infrastructure only; no per-source adapter exists yet
and nothing is wired into :func:`default_sources`. See
``docs/specs/discovery-sweep/design.md`` § "Structured emit (LLM
adapters)" and § "Prompt augmentation lives at the
workflow-instance level, NEVER class" for the contract this module
implements.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import re

from .workflow import Finding

logger = logging.getLogger(__name__)

# Valid severities mirror the ``Severity`` Literal in workflow.py.
# Kept local rather than imported so an invalid value fails into the
# text-only fallback instead of a TypeError at Finding construction.
_VALID_SEVERITIES = frozenset(
    {"critical", "high", "medium", "low", "info"},
)

# Budget-enforcement spec (D2 floor guard + FR-3). Below this per-call
# USD cap a wrapped workflow truncates before doing useful work, so the
# source skips the run(s) and surfaces one info Finding instead of firing
# N doomed near-zero runs. Best-effort, not a contract — tune from
# telemetry. The common single-path sweep never trips it (share ==
# whole allocation, well above the floor).
MIN_PER_CALL_BUDGET_USD: float = 0.05

# A per-call run whose real cost reaches this fraction of its cap was
# almost certainly budget-bound (truncated with partial findings) rather
# than finishing naturally under budget — surfaced as an info Finding so
# the user knows results for that path may be partial (FR-3). SDK-version
# independent: keyed off the truthful ``cost_report`` (PR #1156), never a
# guessed SDK ``subtype``/``stop_reason`` string.
_CAP_PROXIMITY: float = 0.95

# Non-greedy + DOTALL per design.md so multiple blocks parse cleanly
# and re.findall returns them in source order (we use the last).
_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


STRUCTURED_EMIT_FOOTER = """\
In addition to your normal prose output, emit a JSON block at the END
of your response in the following format. The prose above is for the
human; the JSON is for downstream tooling.

```json
{
  "findings": [
    {
      "severity": "high" | "medium" | "low" | "info",
      "title": "one-line summary",
      "description": "1–3 sentence detail",
      "file": "repo-relative path or null",
      "line": <1-indexed int or null>,
      "evidence": "exact quote from source or null",
      "confidence": <float 0.0–1.0>,
      "tags": ["optional", "freeform"]
    }
  ]
}
```
"""


def _fallback(text: str, source_name: str) -> list[Finding]:
    """Single low-confidence finding for the failed-parse path.

    Routed to ``questions`` by the engine's verification rules so the
    user sees the adapter degraded without aborting the sweep.
    """
    evidence = text[:200] + "..." if len(text) > 200 else text
    return [
        Finding(
            source=source_name,
            severity="info",
            title=f"{source_name} returned no structured findings",
            description=(
                f"Workflow completed but emitted no parseable JSON block. "
                f"Raw output length: {len(text)} chars. Re-run with "
                f"--verbose to inspect."
            ),
            file=None,
            line=None,
            evidence=evidence,
            confidence=0.1,
            tags=("text-only-fallback",),
        )
    ]


def _finding_from_entry(entry: object, source_name: str) -> Finding:
    """Construct a Finding from one JSON entry; raises on any defect.

    The caller wraps this in try/except and converts ANY failure into
    the text-only fallback, so we intentionally don't try to coerce
    invalid fields here — fail loudly into the fallback path instead.
    """
    if not isinstance(entry, dict):
        raise TypeError(
            f"finding entry is {type(entry).__name__}, expected dict",
        )

    severity = entry.get("severity")
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"invalid severity: {severity!r}")

    tags_raw = entry.get("tags") or ()
    if not isinstance(tags_raw, list | tuple):
        raise TypeError(
            f"tags is {type(tags_raw).__name__}, expected list/tuple",
        )

    return Finding(
        source=source_name,
        severity=severity,
        title=str(entry["title"]),
        description=str(entry["description"]),
        file=entry.get("file"),
        line=entry.get("line"),
        evidence=entry.get("evidence"),
        confidence=float(entry["confidence"]),
        tags=tuple(str(t) for t in tags_raw),
    )


def parse_findings_json(text: str, source_name: str) -> list[Finding]:
    """Extract structured findings from an LLM response.

    Tolerant parser per ``design.md`` § Structured emit. Behavior:

    * Finds the LAST ```json fenced block in ``text`` (multiple blocks
      → use last per spec P2A.2).
    * Decodes JSON; expects ``{"findings": [{...}, ...]}``.
    * Constructs a :class:`Finding` per entry with the adapter's
      ``source_name``. Missing optional fields default sensibly
      (``file=None``, ``line=None``, ``evidence=None``, ``tags=()``).
    * On ANY failure (no block, malformed JSON, missing ``findings``
      key, or any entry that fails construction) returns the single
      text-only-fallback Finding and never raises.

    Args:
        text: Raw output from the wrapped workflow.
        source_name: Name of the calling adapter — populates both the
            constructed Finding's ``source`` field and the fallback's.

    Returns:
        List of Finding objects. Never empty: at minimum one fallback
        finding so the engine's verification rules always have input.
    """
    matches = _JSON_BLOCK_RE.findall(text)
    if not matches:
        logger.warning(
            "parse_findings_json: no ```json block in %s output",
            source_name,
        )
        return _fallback(text, source_name)

    raw_block = matches[-1]

    try:
        data = json.loads(raw_block)
    except json.JSONDecodeError as exc:
        logger.warning(
            "parse_findings_json: malformed JSON in %s output: %s",
            source_name,
            exc,
        )
        return _fallback(text, source_name)

    if not isinstance(data, dict) or "findings" not in data:
        logger.warning(
            "parse_findings_json: %s output missing 'findings' key",
            source_name,
        )
        return _fallback(text, source_name)

    entries = data["findings"]
    if not isinstance(entries, list):
        logger.warning(
            "parse_findings_json: %s 'findings' is not a list",
            source_name,
        )
        return _fallback(text, source_name)

    findings: list[Finding] = []
    for entry in entries:
        try:
            findings.append(_finding_from_entry(entry, source_name))
        except (TypeError, ValueError, KeyError) as exc:
            logger.warning(
                "parse_findings_json: %s entry construction failed "
                "(%s); returning text-only fallback for entire response",
                source_name,
                exc,
            )
            return _fallback(text, source_name)

    return findings


def findings_from_workflow_result(result: object, source_name: str) -> list[Finding]:
    """Parse structured findings from a WorkflowResult.

    Prefers ``metadata["raw_result_text"]`` — the UNMODIFIED agent
    text — over ``final_output``. ``AgentSDKResultAdapter`` rewrites
    ``final_output`` as formatted markdown whenever its category
    parser extracts findings, which silently drops the ```json block
    that :data:`STRUCTURED_EMIT_FOOTER` requests (caught by the
    nightly auth run 27249886475 — every adapter fell back to the
    text-only path). The raw channel carries the block intact;
    ``final_output`` remains the fallback for results produced
    before the channel existed.

    Args:
        result: A WorkflowResult (or duck-typed equivalent) from a
            wrapped workflow.
        source_name: Name of the calling adapter — threaded through
            to :func:`parse_findings_json`.

    Returns:
        List of Finding objects (never empty — see
        :func:`parse_findings_json`).
    """
    metadata = getattr(result, "metadata", None)
    raw_text = ""
    if isinstance(metadata, dict):
        raw = metadata.get("raw_result_text")
        if isinstance(raw, str):
            raw_text = raw

    final_output = getattr(result, "final_output", "") or ""
    if not isinstance(final_output, str):
        final_output = str(final_output)

    return parse_findings_json(raw_text or final_output, source_name)


def budget_too_small_finding(
    source_name: str,
    n_paths: int,
    share: float,
    allocation: float,
) -> Finding:
    """Floor-guard Finding: the per-call share is below the useful minimum.

    Emitted (per FR-3 / D2) when a source's budget allocation divided
    across its ``paths`` falls below :data:`MIN_PER_CALL_BUDGET_USD`, so
    the source skips its runs entirely rather than firing N runs that
    truncate before doing useful work. ``file=None`` + no ``file-level``
    tag routes this to the sweep's ``questions`` bucket (verification
    rule 1 — an ``info`` finding WITH a file would fail rule 2's
    severity threshold and land in ``rejected``), where the user sees
    the sweep was under-funded.

    Args:
        source_name: The calling adapter's ``name``.
        n_paths: Number of paths the allocation was split across.
        share: The computed per-call share (``allocation / n_paths``).
        allocation: This source's total budget allocation.

    Returns:
        A single ``info``-severity Finding.
    """
    return Finding(
        source=source_name,
        severity="info",
        title=f"{source_name}: budget too small to scan {n_paths} path(s)",
        description=(
            f"This source's ${allocation:.4f} allocation split across "
            f"{n_paths} path(s) is ${share:.4f} each — below the "
            f"${MIN_PER_CALL_BUDGET_USD:.2f} minimum for a useful run. "
            f"Skipped to avoid spending on runs that truncate immediately. "
            f"Raise --budget or narrow the path glob."
        ),
        file=None,
        line=None,
        evidence=None,
        confidence=1.0,
        tags=("budget-cap",),
    )


def cap_hit_finding_if_bound(
    source_name: str,
    path: str,
    result: object,
    share: float | None,
) -> Finding | None:
    """Return an info Finding when a run spent ~all of its cap, else None.

    Per FR-3: when a wrapped workflow's real cost reaches
    :data:`_CAP_PROXIMITY` of its per-call ``max_budget_usd`` share, the
    source maxed its allocation on ``path`` — the run sat at the budget
    ceiling and its findings may be partial. Worded as "at the ceiling"
    rather than "was truncated" because cost alone cannot distinguish a
    truncated run from one that finished naturally at its allocation;
    either way "this source spent its whole allocation, raise --budget
    for more" is the true, useful message. Keyed off the truthful
    ``cost_report.total_cost`` (PR #1156), never a guessed SDK signal.

    ``file=None`` (path goes in the description) so this routes to the
    ``questions`` bucket via verification rule 1 — an ``info`` finding
    WITH a file would be rejected by the severity threshold (rule 2).

    Args:
        source_name: The calling adapter's ``name``.
        path: The path whose run is being assessed.
        result: The WorkflowResult (or duck-typed equivalent).
        share: The per-call USD cap passed to this run, or ``None`` when
            no cap was applied (returns ``None`` — nothing to note).

    Returns:
        An ``info``-severity Finding, or ``None`` when the run finished
        comfortably under its cap (or no cap was set).
    """
    if share is None or share <= 0.0:
        return None
    cost_report = getattr(result, "cost_report", None)
    cost = float(getattr(cost_report, "total_cost", 0.0) or 0.0)
    if cost < share * _CAP_PROXIMITY:
        return None
    return Finding(
        source=source_name,
        severity="info",
        title=f"{source_name}: budget allocation exhausted on {path}",
        description=(
            f"This run spent ${cost:.4f} of its ${share:.4f} allocation "
            f"(≥{_CAP_PROXIMITY:.0%}) — at the budget ceiling; findings "
            f"for {path} may be partial. Raise --budget for a fuller scan."
        ),
        file=None,
        line=None,
        evidence=None,
        confidence=1.0,
        tags=("budget-cap",),
    )


def workflow_unsuccessful_finding(
    source_name: str,
    path: str,
    result: object,
) -> Finding:
    """Marker for a clean WorkflowResult whose ``success`` came back False.

    Shared by every LLM source adapter (previously mirrored per-file
    with a detail line that only read ``final_output`` — empty on most
    failures, rendering the useless "(no detail returned)"). Prefers
    the structured ``error`` / ``error_type`` fields so the question
    entry names the actual failure.

    Tagged ``source-failure`` so verification rule 0 routes it to the
    ``questions`` bucket and the engine counts the source as failed
    when it produced nothing else.
    """
    error = getattr(result, "error", None)
    error_type = getattr(result, "error_type", None)
    final_output = getattr(result, "final_output", "") or ""
    detail = str(error or final_output or "(no detail returned)")
    if error_type:
        detail = f"[{error_type}] {detail}"
    return Finding(
        source=source_name,
        severity="info",
        title=f"{source_name} returned an unsuccessful result for {path}",
        description=(
            "Wrapped workflow completed without raising but reported "
            f"success=False. Detail: {detail[:300]}"
        ),
        file=path,
        line=None,
        evidence=None,
        confidence=1.0,
        tags=("source-failure",),
    )


class LLMSource:
    """Optional marker base for LLM-backed FindingSource adapters.

    Adapters can inherit this or set the attributes directly — the
    engine checks them structurally via ``getattr``. ``is_llm`` lets
    the ``--no-llm`` flag filter sources; ``budget_multiplier`` lets
    a heavier-class adapter (e.g. an orchestrator-with-subagents)
    request a larger share of the sweep budget.
    """

    is_llm: bool = True
    budget_multiplier: float = 1.0
    spent_usd: float = 0.0

    def _record_cost(self, result: object) -> None:
        """Accumulate one workflow result's API cost onto this source.

        After the fan-out, the sweep engine sums ``spent_usd`` across
        sources to populate ``SweepMetadata.spent_usd`` (the footer's
        ``$X / $Y`` line and the workflow ``CostReport``). Without this
        the wrapped workflows' real spend is silently discarded and the
        sweep always reports ``$0.00``.

        Sources are constructed fresh per sweep by ``default_sources()``,
        so the running total never leaks across runs. A result with no
        ``cost_report`` (or a zero cost) contributes nothing.

        Args:
            result: A WorkflowResult (or duck-typed equivalent) whose
                ``cost_report.total_cost`` is the API spend to record.
        """
        cost_report = getattr(result, "cost_report", None)
        if cost_report is None:
            return
        self.spent_usd += float(getattr(cost_report, "total_cost", 0.0) or 0.0)
