"""Resolution-complexity classifier for the discovery-sweep workflow.

Runs ONLY on findings that already have ``verification_status ==
ACCEPT``. Decides between ``routine`` (the queue-default) and
``needs_patrick`` (anything Patrick wants eyes on before
resolution).

Routine is the default. Any trigger flips the finding to
``needs_patrick``. Erring toward ``needs_patrick`` on ambiguous
cases is intentional — Patrick can downgrade in triage.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Protocol, runtime_checkable

from .schema import Finding, ResolutionComplexity, VerificationStatus


@runtime_checkable
class ComplexityTrigger(Protocol):
    """Returns True when the finding should flip to needs_patrick."""

    name: str

    def applies(self, finding: Finding) -> bool:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------


class CrossCuttingTrigger:
    """Fires when the finding looks cross-cutting.

    Heuristic: message or raw_finding references three or more
    distinct file paths, OR mentions ``public API`` / ``base
    class`` / ``shared`` in a way that suggests broad impact.
    """

    name = "cross_cutting"
    _BROAD_IMPACT_RE = re.compile(
        r"\b(public api|base class|shared (?:mixin|module|interface)|" r"breaking change)\b",
        re.IGNORECASE,
    )
    _PATH_RE = re.compile(r"(?:\.\./)*(?:[\w\-]+/){1,}[\w\-]+\.(?:py|js|ts|tsx|md)")

    def applies(self, finding: Finding) -> bool:
        haystack = self._collect_text(finding)
        if self._BROAD_IMPACT_RE.search(haystack):
            return True
        paths = set(self._PATH_RE.findall(haystack))
        paths.discard(finding.file_path)
        return len(paths) >= 3

    @staticmethod
    def _collect_text(finding: Finding) -> str:
        chunks: list[str] = [finding.message]
        for value in finding.raw_finding.values():
            if isinstance(value, str):
                chunks.append(value)
            elif isinstance(value, list):
                chunks.extend(str(v) for v in value if isinstance(v, str | int))
        return "\n".join(chunks)


class SecurityAdjacentTrigger:
    """Fires when the finding touches the security surface."""

    name = "security_adjacent"
    _SECURITY_PATH_TOKENS = (
        "src/attune/security/",
        "/security/",
        "auth",
        "credential",
    )
    _SECURITY_KEYWORDS_RE = re.compile(
        r"\b(eval\(|exec\(|path traversal|path validation|webhook|"
        r"ssrf|injection|secret|credential|cwe-)",
        re.IGNORECASE,
    )

    def applies(self, finding: Finding) -> bool:
        path_lower = finding.file_path.lower()
        if any(token in path_lower for token in self._SECURITY_PATH_TOKENS):
            return True
        return bool(self._SECURITY_KEYWORDS_RE.search(finding.message))


class ContradictsLessonTrigger:
    """Fires when the finding lands in territory documented as a
    known false-positive antipattern.

    Phase 1 heuristic: the finding's message overlaps with
    keywords from any REJECT rule's matcher (e.g. dirs[:],
    create_subprocess_exec, structlog kwargs). Survives REJECT
    only when the rule didn't fire — meaning Patrick should
    look before we assume the fix is safe.
    """

    name = "contradicts_lesson"
    _LESSON_KEYWORDS_RE = re.compile(
        r"(dirs\[:\]|create_subprocess_exec|regex\.exec|"
        r"\.write_text\(|noqa: ble001|structlog|pragma: allowlist secret)",
        re.IGNORECASE,
    )

    def applies(self, finding: Finding) -> bool:
        return bool(self._LESSON_KEYWORDS_RE.search(finding.message))


class TierOrBudgetTrigger:
    """Fires on findings that would change tier mapping, cost
    model, or budget thresholds."""

    name = "tier_or_budget_change"
    _RE = re.compile(
        r"\b(modeltier|tier_map|tier mapping|cost model|cost_tracker|"
        r"budget(?:_| )(?:cap|ceiling|usd)|max_budget_usd|"
        r"premium|capable tier|cheap tier)\b",
        re.IGNORECASE,
    )

    def applies(self, finding: Finding) -> bool:
        return bool(self._RE.search(finding.message))


class MocksProductionTrigger:
    """Fires when a test file's finding suggests rewriting tests
    in a way that loses real coverage.

    Heuristic: the finding is in a test path AND the message
    mentions mocking, patching, or replacing a non-test path.
    """

    name = "mocks_production_smell"
    _TEST_PATH_TOKENS = ("tests/", "test_", "/tests_", "/test/")
    _MOCK_RE = re.compile(
        r"\b(mock|patch|monkeypatch|stub|fake|replace[\w_]*)\b",
        re.IGNORECASE,
    )
    _PRODUCTION_HINT_RE = re.compile(
        r"\b(src/|attune\.[\w\.]+|production code|real (?:db|database|api|client))\b",
        re.IGNORECASE,
    )

    def applies(self, finding: Finding) -> bool:
        path_lower = finding.file_path.lower()
        if not any(token in path_lower for token in self._TEST_PATH_TOKENS):
            return False
        return bool(
            self._MOCK_RE.search(finding.message)
            and self._PRODUCTION_HINT_RE.search(finding.message)
        )


class LowConfidenceTrigger:
    """Fires when the verification reasoning shows the engine
    wasn't fully confident in the ACCEPT verdict."""

    name = "low_confidence"
    _RE = re.compile(
        r"(could not determine|ambiguous|unsure|might be|possibly|"
        r"unable to verify|no specific input)",
        re.IGNORECASE,
    )

    def applies(self, finding: Finding) -> bool:
        return bool(self._RE.search(finding.verification_reasoning))


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def default_triggers() -> list[ComplexityTrigger]:
    """Return the default trigger set."""
    return [
        CrossCuttingTrigger(),
        SecurityAdjacentTrigger(),
        ContradictsLessonTrigger(),
        TierOrBudgetTrigger(),
        MocksProductionTrigger(),
        LowConfidenceTrigger(),
    ]


class ComplexityClassifier:
    """Tags ACCEPTed findings with ``routine`` or ``needs_patrick``.

    Returns a new Finding (the input is not mutated). Non-ACCEPT
    findings are returned unchanged with ``resolution_complexity``
    left None.
    """

    def __init__(self, triggers: list[ComplexityTrigger] | None = None) -> None:
        self._triggers = triggers if triggers is not None else default_triggers()

    def classify(self, finding: Finding) -> Finding:
        if finding.verification_status != VerificationStatus.ACCEPT:
            return finding

        fired = [t.name for t in self._triggers if t.applies(finding)]

        if not fired:
            return replace(finding, resolution_complexity=ResolutionComplexity.ROUTINE)

        # Append firing-trigger names to verification reasoning so
        # the queue file carries triage hints.
        annotation = "needs_patrick triggers: " + ", ".join(fired)
        new_reasoning = (
            f"{finding.verification_reasoning} | {annotation}"
            if finding.verification_reasoning
            else annotation
        )
        return replace(
            finding,
            resolution_complexity=ResolutionComplexity.NEEDS_PATRICK,
            verification_reasoning=new_reasoning,
        )

    def classify_many(self, findings: list[Finding]) -> list[Finding]:
        return [self.classify(f) for f in findings]


__all__ = [
    "ComplexityClassifier",
    "ComplexityTrigger",
    "ContradictsLessonTrigger",
    "CrossCuttingTrigger",
    "LowConfidenceTrigger",
    "MocksProductionTrigger",
    "SecurityAdjacentTrigger",
    "TierOrBudgetTrigger",
    "default_triggers",
]
