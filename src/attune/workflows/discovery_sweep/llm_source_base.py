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
