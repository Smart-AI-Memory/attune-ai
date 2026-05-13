"""Verification rule engine for the discovery-sweep workflow.

The engine runs an ordered list of rules against each Finding.
The first rule that fires determines the finding's
``VerificationStatus`` (REJECT or ACCEPT). If no rule fires, the
default is UNSURE — these findings flow to the questions file
for human review.

The asymmetry to respect: a false REJECT is worse than a false
ACCEPT, because REJECTed findings only land in the audit log
(less visible) while ACCEPTed findings land in the queue (visible
and triaged). REJECT rules must be paired with control tests
showing similar-looking real bugs that the rule does NOT fire on.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from .schema import Finding, VerificationStatus

logger = logging.getLogger(__name__)


@runtime_checkable
class VerificationRule(Protocol):
    """Protocol for verification rules.

    Implementations inspect a Finding plus the source file (as a
    list of lines) and return a ``(status, reasoning)`` tuple when
    the rule fires, or ``None`` to defer to subsequent rules.

    Rules MUST be side-effect free.
    """

    name: str

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:  # pragma: no cover - protocol
        ...


class VerificationEngine:
    """Runs an ordered list of rules against findings.

    The engine reads each finding's source file once (cached per
    sweep run) and dispatches to rules in order. The first rule
    that returns a non-None classification wins. If no rule matches,
    the finding is classified as UNSURE.
    """

    def __init__(
        self,
        rules: Iterable[VerificationRule],
        project_root: Path | None = None,
    ) -> None:
        self._rules: list[VerificationRule] = list(rules)
        self._project_root = (project_root or Path.cwd()).resolve()
        self._source_cache: dict[str, list[str]] = {}

    def classify(self, finding: Finding) -> Finding:
        """Return a new Finding with ``verification_status`` populated.

        The input Finding is not mutated.
        """
        source_lines = self._load_source(finding.file_path)

        for rule in self._rules:
            try:
                outcome = rule.classify(finding, source_lines)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: a buggy rule must not abort the sweep.
                # Log and skip — finding falls through to UNSURE.
                logger.exception(
                    "verification rule %s raised on %s:%s",
                    getattr(rule, "name", type(rule).__name__),
                    finding.file_path,
                    finding.line,
                )
                continue

            if outcome is None:
                continue

            status, reasoning = outcome
            return _with_verdict(finding, status, reasoning)

        return _with_verdict(
            finding,
            VerificationStatus.UNSURE,
            "no verification rule fired; deferring to human review",
        )

    def classify_many(self, findings: Iterable[Finding]) -> list[Finding]:
        """Classify a batch of findings."""
        return [self.classify(f) for f in findings]

    def _load_source(self, file_path: str) -> list[str]:
        if file_path in self._source_cache:
            return self._source_cache[file_path]

        resolved = self._resolve(file_path)
        if resolved is None or not resolved.is_file():
            self._source_cache[file_path] = []
            return []

        try:
            text = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.debug("could not read source for %s", file_path)
            self._source_cache[file_path] = []
            return []

        lines = text.splitlines()
        self._source_cache[file_path] = lines
        return lines

    def _resolve(self, file_path: str) -> Path | None:
        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = self._project_root / candidate
        try:
            return candidate.resolve()
        except OSError:
            return None


def _with_verdict(
    finding: Finding,
    status: VerificationStatus,
    reasoning: str,
) -> Finding:
    """Return a copy of finding with the verdict applied."""
    from dataclasses import replace

    return replace(
        finding,
        verification_status=status,
        verification_reasoning=reasoning,
    )


__all__ = ["VerificationEngine", "VerificationRule"]
