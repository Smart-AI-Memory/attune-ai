"""The receipted diagnosis panel (advanced-debugging-plugin RR-5).

Independent seats inspect the SAME bounded evidence pack (R1: text in,
text out — seats never run tools) and return structured hypotheses;
the moderator synthesis is DETERMINISTIC — parsed hypotheses ranked by
confidence and seat agreement, with unresolved dissent retained, never
a further LLM call. Failures map onto the shipped producing taxonomy
(``SEAT_ABSENT``, ``BUDGET_EXHAUSTED``); an absent seat degrades the
panel, it never blocks it.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from attune.models.telemetry.data_models import DiagnosisEvidence, DiagnosisHypothesis
from attune.roundtable.routine import SEAT_RECIPES, default_invoke_seat

from .config import DiagnosisConfig
from .priors import PriorsResult

logger = logging.getLogger(__name__)

#: Hard invocation ceiling, mirroring the producing run's R5 cap.
MAX_INVOCATIONS = 10

_BRIEF_TEMPLATE = """\
You are one seat on a diagnosis panel for a failed attune workflow
run. Other seats see the same evidence; you cannot see their answers.
Analyze the evidence and reply in EXACTLY this format (1-3 hypotheses,
most likely first; text only — do not run tools or take actions):

HYPOTHESIS: <one-sentence root-cause statement>
CONFIDENCE: <{scale}>
SUPPORTING: <evidence source names that support it>
CONTRADICTING: <evidence source names that cut against it, or "none">

## Recalled lesson priors (historical, NOT observed evidence)
{priors}

## Observed evidence
{evidence}
"""

_HYPOTHESIS_RE = re.compile(
    r"HYPOTHESIS:\s*(?P<statement>.+?)\s*\n"
    r"\s*CONFIDENCE:\s*(?P<confidence>[\w-]+)\s*\n"
    r"(?:\s*SUPPORTING:\s*(?P<supporting>.*?)\s*\n)?"
    r"(?:\s*CONTRADICTING:\s*(?P<contradicting>.*?)(?:\n|$))?",
    re.IGNORECASE,
)


@dataclass
class PanelResult:
    """Everything the panel step contributes to a DiagnosisRecord."""

    hypotheses: list[DiagnosisHypothesis] = field(default_factory=list)
    synthesis: str | None = None
    dissent: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)  # -> DiagnosisRecord.panel


def build_brief(
    evidence: list[DiagnosisEvidence],
    priors: PriorsResult,
    config: DiagnosisConfig,
) -> str:
    """Render the seat brief — identical for every seat."""
    priors_block = (
        "\n".join(f"- {lesson}" for lesson in priors.lessons)
        if priors.lessons
        else f"(none — {priors.degraded or 'no priors'})"
    )
    evidence_block = "\n\n".join(f"### {e.source}\n{e.content}" for e in evidence)
    return _BRIEF_TEMPLATE.format(
        scale=" | ".join(config.confidence_scale),
        priors=priors_block,
        evidence=evidence_block,
    )


def parse_seat_reply(reply: str, seat: str, config: DiagnosisConfig) -> list[DiagnosisHypothesis]:
    """Parse HYPOTHESIS blocks; unknown confidence values clamp to weakest."""
    parsed: list[DiagnosisHypothesis] = []
    for i, match in enumerate(_HYPOTHESIS_RE.finditer(reply or "")):
        confidence = (match.group("confidence") or "").lower()
        if confidence not in config.confidence_scale:
            confidence = config.confidence_scale[0]
        parsed.append(
            DiagnosisHypothesis(
                statement=f"[{seat}] {match.group('statement').strip()}",
                rank=i + 1,
                confidence=confidence,
                supporting=_split_sources(match.group("supporting")),
                contradicting=_split_sources(match.group("contradicting")),
            )
        )
    return parsed


def _split_sources(raw: str | None) -> list[str]:
    if not raw or raw.strip().lower() in ("none", "n/a", "-"):
        return []
    return [s.strip() for s in re.split(r"[,;]", raw) if s.strip()]


def convene_panel(
    evidence: list[DiagnosisEvidence],
    priors: PriorsResult,
    config: DiagnosisConfig | None = None,
    *,
    seats: Sequence[tuple[str, tuple[str, ...]]] = SEAT_RECIPES,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] = default_invoke_seat,
    max_invocations: int = MAX_INVOCATIONS,
) -> PanelResult:
    """Convene up to ``config.panel_seats`` seats; degrade, never block."""
    config = config or DiagnosisConfig()
    brief = build_brief(evidence, priors, config)
    hypotheses: list[DiagnosisHypothesis] = []
    seats_invoked: list[str] = []
    absences: list[dict[str, str]] = []
    failure_codes: list[str] = []
    invocations = 0

    for seat, recipe in seats[: max(1, config.panel_seats)]:
        reply = ""
        ok = False
        for _attempt in range(2):  # one retry, mirroring producing
            if invocations >= max_invocations:
                failure_codes.append("BUDGET_EXHAUSTED")
                break
            invocations += 1
            code, reply = invoke_seat(recipe, brief)
            ok = code == 0 and bool(reply.strip())
            if ok:
                break
        if not ok:
            if "BUDGET_EXHAUSTED" not in failure_codes or invocations < max_invocations:
                failure_codes.append("SEAT_ABSENT")
            absences.append({"seat": seat, "reason": (reply or "no reply")[-300:]})
            continue
        seats_invoked.append(seat)
        hypotheses.extend(parse_seat_reply(reply, seat, config))

    ranked = _rank(hypotheses, config)
    dissent = _detect_dissent(ranked, seats_invoked)
    return PanelResult(
        hypotheses=ranked,
        synthesis=_synthesize(ranked, dissent, seats_invoked, absences),
        dissent=dissent,
        meta={
            "seats_invoked": seats_invoked,
            "absences": absences,
            "failure_codes": failure_codes,
            "invocations": invocations,
        },
    )


def _rank(
    hypotheses: list[DiagnosisHypothesis], config: DiagnosisConfig
) -> list[DiagnosisHypothesis]:
    """Strongest confidence first; stable within a level (seat order)."""
    order = {level: i for i, level in enumerate(config.confidence_scale)}
    ranked = sorted(hypotheses, key=lambda h: -order.get(h.confidence, 0))
    for i, hyp in enumerate(ranked):
        hyp.rank = i + 1
    return ranked


def _detect_dissent(ranked: list[DiagnosisHypothesis], seats_invoked: list[str]) -> list[str]:
    """Record top-hypothesis disagreement between seats — kept, not merged."""
    if len(seats_invoked) < 2 or not ranked:
        return []
    tops: dict[str, str] = {}
    for hyp in ranked:
        seat = hyp.statement.split("]", 1)[0].lstrip("[")
        tops.setdefault(seat, hyp.statement)
    statements = list(tops.values())
    dissent: list[str] = []
    for i, a in enumerate(statements):
        for b in statements[i + 1 :]:
            if not _overlaps(a, b):
                dissent.append(f"top hypotheses diverge: {a!r} vs {b!r}")
    return dissent


def _overlaps(a: str, b: str) -> bool:
    """Cheap material-agreement test: shared significant tokens."""
    tok = lambda s: {w.lower() for w in re.findall(r"[A-Za-z_]{4,}", s)}  # noqa: E731
    shared = tok(a) & tok(b)
    return len(shared) >= 3


def _synthesize(
    ranked: list[DiagnosisHypothesis],
    dissent: list[str],
    seats_invoked: list[str],
    absences: list[dict[str, str]],
) -> str | None:
    """Deterministic moderator summary — assembled, never generated."""
    if not ranked and not absences:
        return None
    lines = [f"panel: {len(seats_invoked)} seat(s) answered, {len(absences)} absent"]
    for hyp in ranked[:5]:
        support = ", ".join(hyp.supporting) or "unstated"
        against = ", ".join(hyp.contradicting) or "none"
        lines.append(
            f"#{hyp.rank} [{hyp.confidence}] {hyp.statement} "
            f"(for: {support}; against: {against})"
        )
    lines.extend(f"DISSENT: {d}" for d in dissent)
    return "\n".join(lines)
