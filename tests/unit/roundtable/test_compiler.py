"""Artifact-compiler tests (round-table V2-P2).

The fixtures under ``fixtures/mem_signal_001/`` are the REAL
artifacts from the table's first spec-authoring loop (thread
``mem-signal-001`` → ``docs/specs/memory-feedback-signal/``) — the
compiler is validated against what the loop actually produced, not
synthetic examples.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path

from attune.roundtable.compiler import (
    ROLE_REPLY_CHARS,
    compile_requirements,
    critique_verdict,
    link_critiques,
    lint_critique,
    lint_draft,
    lint_final,
    parse_draft,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "mem_signal_001"


def _fx(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


class TestGoldenParse:
    def test_round1_draft_parses_six_items(self) -> None:
        draft = parse_draft(_fx("round1-draft.md"))
        assert [i.item_id for i in draft.items] == [f"MI-{n}" for n in range(1, 7)]
        assert draft.open_questions  # five open questions section present
        assert not draft.dissent_register  # round 1 has none

    def test_round3_final_parses_seven_tagged_items(self) -> None:
        draft = parse_draft(_fx("round3-final.md"))
        assert [i.item_id for i in draft.items] == [f"MI-{n}" for n in range(1, 8)]
        tags = {i.item_id: i.tag for i in draft.items}
        assert tags["MI-5"].startswith("2-1")
        assert all(t.startswith("agreed") for k, t in tags.items() if k != "MI-5")
        assert "antigravity" in draft.dissent_register

    def test_item_lookup(self) -> None:
        draft = parse_draft(_fx("round3-final.md"))
        assert draft.item("MI-7") is not None
        assert draft.item("MI-99") is None


class TestGoldenLints:
    def test_real_artifacts_lint_clean(self) -> None:
        assert lint_draft(_fx("round1-draft.md")) == []
        assert lint_final(_fx("round3-final.md")) == []
        assert lint_critique(_fx("round2-critique-antigravity.md")) == []
        assert lint_critique(_fx("round2-critique-codex.md")) == []

    def test_verdicts_extracted(self) -> None:
        assert critique_verdict(_fx("round2-critique-antigravity.md")) == "ready-with-edits"
        assert critique_verdict(_fx("round2-critique-codex.md")) == "needs-revision"

    def test_untagged_final_item_rejected(self) -> None:
        text = "## Requirements\n\n**MI-1 — thing**\n- a probe\n\n## Dissent register\n\nempty — attested\n"
        assert any("missing convergence tag" in p for p in lint_final(text))

    def test_unattested_empty_dissent_rejected(self) -> None:
        text = (
            "## Requirements\n\n**MI-1 — thing**\n- a probe\n[tag: agreed]\n\n"
            "## Dissent register\n\nempty\n"
        )
        assert any("without attestation" in p for p in lint_final(text))

    def test_uncited_critique_item_rejected(self) -> None:
        text = "1. **MI-1:** this is just an opinion with no reference.\n\nVERDICT: needs-revision"
        assert any("uncited" in p for p in lint_critique(text))

    def test_critique_without_verdict_rejected(self) -> None:
        text = "1. **MI-1:** wrong per pack item 2."
        assert any("VERDICT" in p for p in lint_critique(text))

    def test_draft_without_bullets_rejected(self) -> None:
        assert any(
            "acceptance-criteria" in p
            for p in lint_draft("## Requirements\n\n**MI-1 — bare**\nprose only\n\n## Non-goals\nx")
        )


class TestLedger:
    def test_objections_link_to_their_items(self) -> None:
        draft = parse_draft(_fx("round3-final.md"))
        link_critiques(
            draft,
            {
                "antigravity": _fx("round2-critique-antigravity.md"),
                "codex": _fx("round2-critique-codex.md"),
            },
        )
        mi1 = draft.item("MI-1")
        mi5 = draft.item("MI-5")
        assert mi1 is not None and mi5 is not None
        # codex filed four MI-1 objections; antigravity one; MISSING items skip.
        assert sum(o.startswith("codex:") for o in mi1.objections) >= 3
        assert any(o.startswith("antigravity:") for o in mi5.objections)
        assert all(":" in o for o in mi5.objections)


class TestCompile:
    def test_deterministic_assembly_honors_rulings(self) -> None:
        draft = parse_draft(_fx("round3-final.md"))
        rulings = {f"MI-{n}": "approved" for n in range(1, 8)}
        rulings["MI-6"] = "declined"
        out1 = compile_requirements(
            draft,
            spec_title="Demo Spec",
            thread="mem-signal-001",
            rulings=rulings,
            ruling_note="Chair ruling: wrong_rate is the headline.",
        )
        out2 = compile_requirements(
            parse_draft(_fx("round3-final.md")),
            spec_title="Demo Spec",
            thread="mem-signal-001",
            rulings=rulings,
            ruling_note="Chair ruling: wrong_rate is the headline.",
        )
        assert out1 == out2  # deterministic
        assert "**MI-1 — " in out1 and "**MI-6 — " not in out1  # declined excluded
        assert "declined: MI-6" in out1  # ...but recorded honestly
        assert "mem-signal-001" in out1  # provenance (R10)
        assert "## Dissent register" in out1
        assert "chair: approved" in out1

    def test_unruled_items_stay_out_and_are_named(self) -> None:
        draft = parse_draft(_fx("round3-final.md"))
        out = compile_requirements(
            draft,
            spec_title="Demo",
            thread="t",
            rulings={"MI-1": "approved"},
        )
        assert "unruled: MI-2, MI-3" in out
        assert "**MI-2 — " not in out


class TestBudgets:
    def test_role_budgets_are_role_aware(self) -> None:
        """V2-P1 field note: drafter documents need more room than
        positions — the flat cap truncated a real revision."""
        assert ROLE_REPLY_CHARS["drafter"] > ROLE_REPLY_CHARS["critic"] > 0
        assert ROLE_REPLY_CHARS["critic"] > ROLE_REPLY_CHARS["position"] // 2
