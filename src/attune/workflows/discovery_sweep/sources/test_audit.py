"""``TestAuditSource`` — LLM adapter wrapping ``TestAuditWorkflow``.

The final Phase 2B adapter. Mirrors the
:class:`BugPredictSource` / :class:`SecurityAuditSource` /
:class:`DependencyCheckSource` / :class:`PerfAuditSource` /
:class:`DocAuditSource` pattern: constructs a fresh
:class:`TestAuditWorkflow` per call with
:data:`STRUCTURED_EMIT_FOOTER` passed via ``system_prompt_suffix``
(workflow-INSTANCE level augmentation per Phase 1.5
``design.md``), invokes ``execute()`` once per path, and parses
each result via :func:`findings_from_workflow_result`.

``budget_multiplier = 1.0`` — test-audit sits at the default slot
in Phase 1.5's ratio table (security=4 / deps=0.5 / default=1).
Inherits the marker default from :class:`LLMSource`, no override
needed.

The ``claude_agent_sdk`` import lives inside :meth:`discover` so
this module is mock-friendly and doesn't drag the SDK into the
import graph of every test that touches the engine.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..llm_source_base import (
    MIN_PER_CALL_BUDGET_USD,
    STRUCTURED_EMIT_FOOTER,
    LLMSource,
    budget_too_small_finding,
    cap_hit_finding_if_bound,
    findings_from_workflow_result,
    workflow_unsuccessful_finding,
)
from ..workflow import Finding

logger = logging.getLogger(__name__)


@dataclass
class TestAuditSource(LLMSource):
    """Discovery-sweep adapter for :class:`TestAuditWorkflow`.

    Three structural attributes (``name``, ``is_llm``,
    ``budget_multiplier``) satisfy the :class:`FindingSource`
    Protocol; ``LLMSource`` is inherited for the ``--no-llm``
    filter marker. ``budget_multiplier`` keeps the LLMSource
    default of 1.0.

    ``depth`` is configurable per-instance and defaults to
    ``"standard"`` — same default as standalone
    ``attune workflow run test-audit``. Sweep callers that want a
    cheaper pass can construct with ``depth="quick"``.
    """

    name: str = "test-audit"
    depth: str = "standard"

    async def discover(self, paths: list[str], budget_usd: float) -> list[Finding]:
        """Run TestAuditWorkflow on each path and parse findings.

        ``budget_usd`` is this source's allocation from the sweep
        engine. Per the budget-enforcement spec (FR-2 / D2) it is split
        evenly across ``paths`` and passed down as each wrapped
        ``execute()``'s ``max_budget_usd``, so the source self-limits to
        its allocation. Below the per-call floor the source skips its
        runs and surfaces one info Finding (FR-3) instead of firing N
        runs that truncate before doing useful work.
        """
        if not paths:
            logger.warning("test-audit: no paths to scan")
            return [_empty_paths_finding(self.name)]

        # Budget-enforcement spec FR-2 / D2: even-split the allocation
        # across paths. Single-path sweeps (the common case) get the
        # whole allocation. Below the floor, skip rather than truncate.
        share = budget_usd / len(paths)
        if share < MIN_PER_CALL_BUDGET_USD:
            return [budget_too_small_finding(self.name, len(paths), share, budget_usd)]

        # Late import keeps ``claude_agent_sdk`` out of this
        # module's import graph and lets unit tests patch the
        # workflow class at its source module per the existing
        # CLAUDE.md deferred-import lesson.
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        findings: list[Finding] = []
        for path in paths:
            workflow = TestAuditWorkflow(
                system_prompt_suffix=STRUCTURED_EMIT_FOOTER,
            )
            try:
                result = await workflow.execute(path=path, depth=self.depth, max_budget_usd=share)
            except Exception as exc:  # noqa: BLE001
                # INTENTIONAL: per spec NFR-1 a single path failure
                # must not abort the whole source — log and
                # continue, surfacing an info-finding so the
                # engine can route it to ``questions``.
                logger.exception("test-audit execute() failed for %s", path)
                findings.append(_path_failed_finding(self.name, path, exc))
                continue

            self._record_cost(result)

            if not getattr(result, "success", False):
                findings.append(workflow_unsuccessful_finding(self.name, path, result))
                continue

            findings.extend(findings_from_workflow_result(result, self.name))

            # FR-3: note when this path's run sat at its budget ceiling.
            cap_note = cap_hit_finding_if_bound(self.name, path, result, share)
            if cap_note is not None:
                findings.append(cap_note)

        return findings


def _empty_paths_finding(source_name: str) -> Finding:
    """Surfacing finding when the engine handed in an empty paths list."""
    return Finding(
        source=source_name,
        severity="info",
        title=f"{source_name} received no paths to scan",
        description=(
            "The engine passed an empty paths list to this source; "
            "the wrapped workflow was not invoked."
        ),
        file=None,
        line=None,
        evidence=None,
        confidence=1.0,
        tags=("source-failure",),
    )


def _path_failed_finding(source_name: str, path: str, exc: BaseException) -> Finding:
    """Per-path failure marker so one bad input doesn't abort the source."""
    return Finding(
        source=source_name,
        severity="info",
        title=f"{source_name} failed on path {path}",
        description=(
            f"Wrapped workflow raised {type(exc).__name__}: {exc}. "
            f"Other paths (if any) were still attempted."
        ),
        file=path,
        line=None,
        evidence=None,
        confidence=1.0,
        tags=("source-failure",),
    )
