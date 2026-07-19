"""Spec-lifecycle gates tests (T1–T4 of spec-lifecycle-gates).

Covers the protocol's closed enum, the G1 ledger under ATTUNE_HOME
isolation, the activation policy against the chair-ruled surface
map, the baseline gates (including the slot-3 confabulation
regression), and the runner's never-advance + G5 exit semantics.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from attune.gates.lifecycle import (
    GateReceipt,
    Waiver,
    active_gates,
    append,
    blast_radius,
    exit_code,
    falsifiability_gate,
    latest_for,
    ledger_path,
    parse_waivers,
    run_boundary,
    symbol_reality_gate,
    unresolved_chair_required,
    waived,
)

NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)

#: The seven paths the slot-3 drafter confabulated — the live episode
#: this gate exists to catch (spec decisions.md, 2026-07-19).
CONFABULATED = """
- Boundary gates must invoke `attune/compiler/lint.py` and
  `attune/corpus/readiness.py` plus `attune/doc_import/gate.py`.
- Also `attune/runner/caps.py`, `attune/receipts/rerun.py`,
  `attune/curator/triage.py`, `attune/reconciler/starter_reconciler.py`.
"""


class TestProtocol:
    def test_unknown_state_raises(self):
        with pytest.raises(ValueError, match="unknown gate state"):
            GateReceipt(gate_id="x", phase="design", target="t", state="MAYBE")

    def test_unknown_phase_raises(self):
        with pytest.raises(ValueError, match="unknown phase"):
            GateReceipt(gate_id="x", phase="thinking", target="t", state="PASS")

    def test_receipt_round_trips(self):
        r = GateReceipt(
            gate_id="symbol-reality",
            phase="requirements",
            target="some-spec",
            state="BLOCKED",
            findings=["cited but unresolvable: x.py"],
        )
        loaded = GateReceipt.from_dict(r.to_dict())
        assert loaded.receipt_id == r.receipt_id
        assert loaded.state == "BLOCKED"
        assert loaded.findings == r.findings


class TestLedger:
    def test_append_and_latest_for(self, tmp_path):
        f = tmp_path / "verdicts.jsonl"
        old = GateReceipt(gate_id="g", phase="design", target="s", state="REVISE")
        new = GateReceipt(gate_id="g", phase="design", target="s", state="PASS")
        append(old, path=f)
        append(new, path=f)
        (latest,) = latest_for("s", path=f)
        assert latest.state == "PASS"  # later rows supersede

    def test_unresolved_chair_required(self, tmp_path):
        f = tmp_path / "verdicts.jsonl"
        open_r = GateReceipt(gate_id="a", phase="design", target="s", state="CHAIR_REQUIRED")
        cited = GateReceipt(
            gate_id="b",
            phase="design",
            target="s",
            state="CHAIR_REQUIRED",
            decisions_ref="G9",
        )
        append(open_r, path=f)
        append(cited, path=f)
        assert [r.gate_id for r in unresolved_chair_required(path=f)] == ["a"]

    def test_default_path_is_isolated_from_real_home(self):
        """Drift guard: the suite must never touch the real ledger."""
        assert str(ledger_path()).startswith(os.environ["ATTUNE_HOME"])
        assert ledger_path() != Path.home() / ".attune" / "ops" / "gates" / "verdicts.jsonl"


class TestActivation:
    @pytest.mark.parametrize(
        "paths",
        [
            ["src/attune/security/path_validation.py"],
            ["plugin/skills/spec/SKILL.md"],
            [".github/workflows/tests.yml"],
            ["src/attune/models/telemetry/data_models.py"],
            ["pyproject.toml"],
            ["src/attune/__init__.py"],
            ["db/migrations/0001_add.sql"],
            [],  # unclassifiable → conservative default
        ],
    )
    def test_chair_radius_cases(self, paths):
        assert blast_radius(paths) == "chair"

    def test_isolated_radius(self):
        assert blast_radius(["src/attune/gates/lifecycle/protocol.py", "tests/unit/x.py"]) == (
            "isolated"
        )

    def test_sub_spec_tier_gets_baseline_only(self):
        assert active_gates("sub-spec", "chair") == ["symbol-reality", "falsifiability"]

    def test_spec_tier_chair_radius_appends_chair_review(self):
        assert active_gates("spec", "chair")[-1] == "chair-review"

    def test_waiver_parse_and_expiry(self):
        text = "WAIVER: symbol-reality my-spec until 2026-07-20 — flaky env, G2\n"
        (w,) = parse_waivers(text)
        assert w == Waiver("symbol-reality", "my-spec", "2026-07-20", "flaky env, G2")
        assert not w.expired(today=NOW)
        assert w.expired(today=datetime(2026, 7, 21, tzinfo=timezone.utc))
        assert waived("symbol-reality", "my-spec", [w], today=NOW)
        assert not waived("symbol-reality", "other", [w], today=NOW)

    def test_malformed_waiver_is_ignored(self):
        assert parse_waivers("WAIVER: badline\n") == []


class TestBaselineGates:
    def test_confabulated_paths_block(self, tmp_path):
        """The slot-3 live episode, as a permanent regression."""
        r = symbol_reality_gate(CONFABULATED, tmp_path, phase="requirements", target="s")
        assert r.state == "BLOCKED"
        assert len(r.findings) == 7
        assert any("attune/compiler/lint.py" in f for f in r.findings)

    def test_real_paths_pass(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "ok.py").write_text("x = 1\n")
        doc = "- uses `src/ok.py` and the `attune.gates.lifecycle` module."
        r = symbol_reality_gate(doc, tmp_path, phase="design", target="s")
        assert r.state == "PASS"

    def test_not_yet_built_hatch_exempts_line(self, tmp_path):
        doc = "- will add `src/future/thing.py` [[?future-thing]] later."
        r = symbol_reality_gate(doc, tmp_path, phase="design", target="s")
        assert r.state == "PASS"

    def test_falsifiability_flags_banned_phrasing(self):
        doc = "- the hook is registered and exits 0.\n- covered by a suite test that fails on regression.\n"
        r = falsifiability_gate(doc, phase="requirements", target="s")
        assert r.state == "REVISE"
        assert len(r.findings) == 1
        assert "registered" in r.findings[0]

    def test_falsifiability_passes_receipted_bullets(self):
        doc = "- verified by a live-fire probe that exits non-zero on failure.\n"
        r = falsifiability_gate(doc, phase="requirements", target="s")
        assert r.state == "PASS"


class TestRunner:
    def _spec_dir(self, tmp_path: Path, requirements: str, decisions: str = "") -> Path:
        d = tmp_path / "docs" / "specs" / "my-spec"
        d.mkdir(parents=True)
        (d / "requirements.md").write_text(requirements, encoding="utf-8")
        if decisions:
            (d / "decisions.md").write_text(decisions, encoding="utf-8")
        return tmp_path

    def test_receipts_appended_and_tree_untouched(self, tmp_path):
        root = self._spec_dir(tmp_path, CONFABULATED)
        ledger_file = tmp_path / "ledger.jsonl"
        before = sorted(p for p in root.rglob("*") if p.is_file())
        receipts = run_boundary(
            "requirements",
            "my-spec",
            project_root=root,
            tier="sub-spec",
            changed_paths=["docs/x.md"],
            ledger_file=ledger_file,
        )
        after = sorted(p for p in root.rglob("*") if p.is_file() and p != ledger_file)
        assert before == after  # never mutates spec files
        assert {r.gate_id for r in receipts} == {"symbol-reality", "falsifiability"}
        assert len(latest_for("my-spec", path=ledger_file)) == 2

    def test_waiver_downgrades_with_flag(self, tmp_path):
        waiver = "WAIVER: symbol-reality my-spec until 2099-01-01 — pinned example, G2\n"
        root = self._spec_dir(tmp_path, CONFABULATED, decisions=waiver)
        receipts = run_boundary(
            "requirements",
            "my-spec",
            project_root=root,
            tier="sub-spec",
            changed_paths=["docs/x.md"],
            ledger_file=tmp_path / "l.jsonl",
        )
        sym = next(r for r in receipts if r.gate_id == "symbol-reality")
        assert sym.state == "PASS" and sym.waived is True

    def test_exit_codes_follow_g5(self):
        blocked = GateReceipt(gate_id="a", phase="design", target="s", state="BLOCKED")
        chair = GateReceipt(gate_id="b", phase="design", target="s", state="CHAIR_REQUIRED")
        ok = GateReceipt(gate_id="c", phase="design", target="s", state="PASS")
        assert exit_code([ok, chair, blocked]) == 2
        assert exit_code([ok, chair]) == 1
        assert exit_code([ok]) == 0
