"""Panel tests (advanced-debugging-plugin T4) — panel LOGIC under
mocked seats; LLM output quality is not under test here.
"""

from attune.diagnosis.config import DiagnosisConfig
from attune.diagnosis.panel import (
    build_brief,
    convene_panel,
    parse_seat_reply,
)
from attune.diagnosis.priors import PriorsResult
from attune.models.telemetry.data_models import DiagnosisEvidence

_EVIDENCE = [DiagnosisEvidence(kind="observed", source="run-record", content='{"x":1}')]

_REPLY_HIGH = (
    "HYPOTHESIS: stale editable-install MAPPING points at main\n"
    "CONFIDENCE: high\n"
    "SUPPORTING: run-record\n"
    "CONTRADICTING: none\n"
)
_REPLY_LOW = (
    "HYPOTHESIS: transient network failure during SDK call\n"
    "CONFIDENCE: low\n"
    "SUPPORTING: log-tail\n"
    "CONTRADICTING: run-record\n"
)


def _seats(replies):
    """Build a fake roster + invoker: seat name -> (code, reply)."""
    roster = tuple((name, (name, "-")) for name in replies)
    calls = []

    def invoke(recipe, brief):
        calls.append(recipe[0])
        return replies[recipe[0]]

    return roster, invoke, calls


class TestParsing:
    def test_parses_structured_blocks(self):
        cfg = DiagnosisConfig()
        parsed = parse_seat_reply(_REPLY_HIGH + "\n" + _REPLY_LOW, "codex", cfg)
        assert len(parsed) == 2
        assert parsed[0].statement.startswith("[codex] stale editable-install")
        assert parsed[0].confidence == "high"
        assert parsed[0].supporting == ["run-record"]
        assert parsed[1].contradicting == ["run-record"]

    def test_unknown_confidence_clamps_to_weakest(self):
        cfg = DiagnosisConfig()
        reply = "HYPOTHESIS: something\nCONFIDENCE: absolutely-certain\n"
        assert parse_seat_reply(reply, "s", cfg)[0].confidence == "low"

    def test_freeform_reply_yields_no_hypotheses(self):
        assert parse_seat_reply("I think it broke somehow.", "s", DiagnosisConfig()) == []


class TestConvene:
    def test_two_seats_ranked_by_confidence(self):
        roster, invoke, calls = _seats({"alpha": (0, _REPLY_LOW), "beta": (0, _REPLY_HIGH)})
        result = convene_panel(
            _EVIDENCE, PriorsResult(), DiagnosisConfig(), seats=roster, invoke_seat=invoke
        )
        assert result.meta["seats_invoked"] == ["alpha", "beta"]
        assert result.hypotheses[0].confidence == "high"  # beta's outranks alpha's
        assert result.hypotheses[0].rank == 1
        assert calls == ["alpha", "beta"]

    def test_absent_seat_degrades_never_blocks(self):
        roster, invoke, calls = _seats({"alpha": (1, "401 revoked"), "beta": (0, _REPLY_HIGH)})
        result = convene_panel(
            _EVIDENCE, PriorsResult(), DiagnosisConfig(), seats=roster, invoke_seat=invoke
        )
        assert result.meta["seats_invoked"] == ["beta"]
        assert result.meta["absences"][0]["seat"] == "alpha"
        assert "401 revoked" in result.meta["absences"][0]["reason"]
        assert "SEAT_ABSENT" in result.meta["failure_codes"]
        assert calls == ["alpha", "alpha", "beta"]  # one retry then move on
        assert result.hypotheses  # the panel still produced output

    def test_invocation_cap_enforced(self):
        roster, invoke, _calls = _seats({"alpha": (0, _REPLY_HIGH), "beta": (0, _REPLY_LOW)})
        result = convene_panel(
            _EVIDENCE,
            PriorsResult(),
            DiagnosisConfig(),
            seats=roster,
            invoke_seat=invoke,
            max_invocations=1,
        )
        assert result.meta["invocations"] == 1
        assert "BUDGET_EXHAUSTED" in result.meta["failure_codes"]
        assert result.meta["seats_invoked"] == ["alpha"]

    def test_dissent_retained_when_tops_diverge(self):
        roster, invoke, _calls = _seats({"alpha": (0, _REPLY_HIGH), "beta": (0, _REPLY_LOW)})
        result = convene_panel(
            _EVIDENCE, PriorsResult(), DiagnosisConfig(), seats=roster, invoke_seat=invoke
        )
        assert result.dissent, "diverging top hypotheses must register dissent"
        assert any("DISSENT" in line for line in (result.synthesis or "").splitlines())

    def test_all_seats_absent_yields_empty_but_receipted_panel(self):
        roster, invoke, _calls = _seats({"alpha": (1, ""), "beta": (1, "")})
        result = convene_panel(
            _EVIDENCE, PriorsResult(), DiagnosisConfig(), seats=roster, invoke_seat=invoke
        )
        assert result.hypotheses == []
        assert len(result.meta["absences"]) == 2
        assert result.synthesis is not None  # absences are still receipted


class TestBrief:
    def test_brief_separates_priors_from_observed(self):
        brief = build_brief(
            _EVIDENCE,
            PriorsResult(lessons=["mapping-trap — main shadows worktree"]),
            DiagnosisConfig(),
        )
        assert "Recalled lesson priors" in brief
        assert "NOT observed evidence" in brief
        assert "mapping-trap" in brief
        assert "### run-record" in brief

    def test_degraded_priors_shown_explicitly(self):
        brief = build_brief(_EVIDENCE, PriorsResult(degraded="redis-down"), DiagnosisConfig())
        assert "redis-down" in brief
