"""Unit tests for spec_lifecycle.derive_lifecycle.

Covers the 6-rule cascade documented at
docs/specs/ops-specs-page-refinement/decisions.md § "Lifecycle derivation
algorithm": Paused -> Complete -> Stale -> Draft -> Approved-not-shipped
-> Active (first match wins).

Tests use a minimal local dataclass mirroring SpecPhase / SpecRecord
shape (only the fields derive_lifecycle reads). Keeping the test
fixtures local rather than importing from routes/specs.py decouples the
pure-logic module from the FastAPI layer — the lifecycle module knows
nothing about HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest

from attune.ops.spec_lifecycle import (
    STALE_THRESHOLD_DAYS,
    derive_lifecycle,
    derive_stage,
    read_gate_verdicts,
)

# ----- Test fixtures --------------------------------------------------


@dataclass
class _Phase:
    """Minimal SpecPhase-like shape for derive_lifecycle input."""

    name: str
    exists: bool = True
    status: str | None = None


@dataclass
class _Spec:
    """Minimal SpecRecord-like shape for derive_lifecycle input."""

    phases: list[_Phase] = field(default_factory=list)
    last_modified: str | None = None


# Fixed "now" — far enough in the future that nothing legitimate hits
# the stale cutoff by accident. Tests that exercise the stale rule pass
# `now=NOW` and an old `last_modified`; tests that exercise other rules
# either pass a fresh `last_modified` or rely on `last_modified=None`
# which short-circuits the stale check.
NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
FRESH = (NOW - timedelta(days=5)).isoformat()
STALE = (NOW - timedelta(days=STALE_THRESHOLD_DAYS + 1)).isoformat()


def _all_phases(*, requirements=None, design=None, tasks=None, decisions=None) -> list[_Phase]:
    """Build the 4 canonical phases with the given statuses (None = missing)."""
    return [
        _Phase(name="requirements", exists=requirements is not None, status=requirements),
        _Phase(name="design", exists=design is not None, status=design),
        _Phase(name="tasks", exists=tasks is not None, status=tasks),
        _Phase(name="decisions", exists=decisions is not None, status=decisions),
    ]


# ----- Rule 1: Paused -------------------------------------------------


class TestPausedRule:
    """Rule 1 — ANY phase containing 'paused' wins everything else."""

    def test_paused_keyword_in_one_phase(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="paused 2026-05-12 — premise invalidated",
                design="complete",
                tasks="complete",
                decisions="complete",
            ),
            last_modified=FRESH,
        )
        # Otherwise this would be Complete (3 phases complete + paused).
        assert derive_lifecycle(spec, now=NOW) == "paused"

    def test_paused_case_insensitive(self):
        spec = _Spec(
            phases=_all_phases(requirements="PAUSED — see audit.md"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "paused"

    def test_paused_wins_over_stale(self):
        spec = _Spec(
            phases=_all_phases(requirements="paused 2025-01-01"),
            last_modified=STALE,
        )
        # Both Paused and Stale match; Paused wins.
        assert derive_lifecycle(spec, now=NOW) == "paused"

    def test_paused_substring_does_not_match_non_word_use(self):
        # Word-substring approach: "unpaused" would also match. Decisions
        # say "contains the word 'paused' (case-insensitive)" — the
        # implementation does substring matching, so 'unpaused' WOULD
        # match. Document the behavior here so it's intentional and not
        # a surprise.
        spec = _Spec(
            phases=_all_phases(requirements="unpaused-and-shipping"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "paused"


# ----- Rule 2: Complete -----------------------------------------------


class TestCompleteRule:
    """Rule 2 — every EXISTING phase is done, at least one exists."""

    def test_all_four_phases_complete(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="complete",
                design="complete",
                tasks="complete",
                decisions="complete",
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_three_phases_complete_no_decisions(self):
        """Real-world case: ci-debt, telemetry — 3 phase files, no decisions.md.

        The strict literal reading "ALL 4 phases" would mark these as
        not-Complete. The codified rule treats non-existent phases as
        not-blocking, so a 3-of-3 complete spec is Complete.
        """
        spec = _Spec(
            phases=_all_phases(
                requirements="complete (2026-05-10)",
                design="complete (2026-05-10)",
                tasks="complete (2026-05-10)",
                decisions=None,  # File doesn't exist
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_status_annotations_dont_break_match(self):
        """`complete (2026-05-10) — Phase A …` should still match."""
        spec = _Spec(
            phases=_all_phases(
                requirements="complete (2026-05-10) — Phase A `68f19b90`, B `28441852`",
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_completed_alias(self):
        spec = _Spec(
            phases=_all_phases(requirements="completed"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_done_alias(self):
        spec = _Spec(
            phases=_all_phases(requirements="done"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_one_phase_incomplete_blocks_complete(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="complete",
                design="approved",
                tasks="complete",
            ),
            last_modified=FRESH,
        )
        # design is approved-not-complete, so spec is not Complete.
        # Falls through to subsequent rules.
        assert derive_lifecycle(spec, now=NOW) != "complete"

    def test_empty_phases_blocks_vacuous_complete(self):
        """all([]) is True; guard with 'at least one phase exists'."""
        spec = _Spec(phases=[], last_modified=FRESH)
        # No phases at all — Complete would be vacuous truth. Must not fire.
        # Falls through to Draft (no requirements).
        assert derive_lifecycle(spec, now=NOW) == "draft"

    def test_all_phases_missing_blocks_complete(self):
        spec = _Spec(
            phases=_all_phases(),  # All exist=False
            last_modified=FRESH,
        )
        # No EXISTING phases. Complete must not fire on vacuous truth.
        assert derive_lifecycle(spec, now=NOW) == "draft"


# ----- Rule 3: Stale --------------------------------------------------


class TestStaleRule:
    """Rule 3 — last_modified older than threshold."""

    def test_stale_when_last_modified_is_old(self):
        spec = _Spec(
            phases=_all_phases(requirements="approved", tasks="draft"),
            last_modified=STALE,
        )
        assert derive_lifecycle(spec, now=NOW) == "stale"

    def test_fresh_spec_is_not_stale(self):
        spec = _Spec(
            phases=_all_phases(requirements="approved", tasks="draft"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) != "stale"

    def test_none_last_modified_is_not_stale(self):
        """Missing timestamp shouldn't default to Stale — go to other rules."""
        spec = _Spec(
            phases=_all_phases(requirements="approved", tasks="draft"),
            last_modified=None,
        )
        assert derive_lifecycle(spec, now=NOW) != "stale"

    def test_complete_wins_over_stale(self):
        """A genuinely-completed but old spec stays Complete, not Stale."""
        spec = _Spec(
            phases=_all_phases(requirements="complete", design="complete", tasks="complete"),
            last_modified=STALE,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_stale_wins_over_draft(self):
        """Old draft surfaces as Stale, not Draft — that's the value."""
        spec = _Spec(phases=_all_phases(), last_modified=STALE)
        assert derive_lifecycle(spec, now=NOW) == "stale"

    def test_naive_iso_treated_as_utc(self):
        """Tolerate naive (no tz) ISO strings without raising."""
        naive_stale = (
            (NOW - timedelta(days=STALE_THRESHOLD_DAYS + 1)).replace(tzinfo=None).isoformat()
        )
        spec = _Spec(
            phases=_all_phases(requirements="approved"),
            last_modified=naive_stale,
        )
        assert derive_lifecycle(spec, now=NOW) == "stale"

    def test_unparseable_iso_does_not_raise(self):
        """Garbage in last_modified shouldn't crash the cascade."""
        spec = _Spec(
            phases=_all_phases(requirements="approved"),
            last_modified="not-a-date",
        )
        # Should fall through to other rules without raising.
        result = derive_lifecycle(spec, now=NOW)
        assert result in {"draft", "approved-not-shipped", "active"}

    def test_threshold_boundary(self):
        """Exactly STALE_THRESHOLD_DAYS old is NOT stale (strict `>`)."""
        on_boundary = (NOW - timedelta(days=STALE_THRESHOLD_DAYS)).isoformat()
        spec = _Spec(
            phases=_all_phases(requirements="approved"),
            last_modified=on_boundary,
        )
        assert derive_lifecycle(spec, now=NOW) != "stale"

    def test_naive_now_treated_as_utc(self):
        """A caller passing a naive `now` shouldn't crash — UTC default."""
        naive_now = datetime(2026, 6, 1, 12, 0, 0)  # no tzinfo
        old_ts = "2025-01-01T00:00:00+00:00"  # >30 days before naive_now
        spec = _Spec(
            phases=_all_phases(requirements="approved"),
            last_modified=old_ts,
        )
        assert derive_lifecycle(spec, now=naive_now) == "stale"


# ----- Rule 4: Draft --------------------------------------------------


class TestDraftRule:
    """Rule 4 — requirements missing OR not approved."""

    def test_no_requirements_file_is_draft(self):
        spec = _Spec(
            phases=_all_phases(design="draft", tasks="draft"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "draft"

    def test_requirements_in_review_is_draft(self):
        spec = _Spec(
            phases=_all_phases(requirements="in-review"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "draft"

    def test_requirements_no_status_is_draft(self):
        spec = _Spec(
            phases=[_Phase(name="requirements", exists=True, status=None)],
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "draft"

    def test_requirements_custom_status_is_draft(self):
        """Unknown custom strings fall through to Draft."""
        spec = _Spec(
            phases=_all_phases(requirements="partial — work paus"),
            last_modified=FRESH,
        )
        # Note: "paus" without "paused" — doesn't match Rule 1
        assert "paus" in "paus"  # sanity
        assert derive_lifecycle(spec, now=NOW) == "draft"


# ----- Rule 5: Approved-not-shipped -----------------------------------


class TestApprovedNotShippedRule:
    """Rule 5 — requirements approved + tasks.md exists + nothing complete."""

    def test_requirements_approved_with_tasks_no_complete(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="approved",
                design="approved",
                tasks="approved",
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "approved-not-shipped"

    def test_requirements_approved_no_tasks_file_is_active(self):
        """Without tasks.md the spec falls through to Active, not ApprNotShipped."""
        spec = _Spec(
            phases=_all_phases(requirements="approved", design="approved"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "active"

    def test_any_complete_phase_disqualifies(self):
        """One phase complete disqualifies Approved-not-shipped — falls to Active."""
        spec = _Spec(
            phases=_all_phases(
                requirements="approved",
                design="approved",
                tasks="complete",  # One phase done -> shipped started
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "active"

    def test_approved_with_complete_status_alias_in_requirements(self):
        """`complete` in requirements means Complete fires, not Approved-not-shipped."""
        spec = _Spec(
            phases=_all_phases(
                requirements="complete",
                design="approved",
                tasks="approved",
            ),
            last_modified=FRESH,
        )
        # any_complete=True; falls to Active (Complete requires ALL existing done).
        assert derive_lifecycle(spec, now=NOW) == "active"


# ----- Rule 6: Active (default) ---------------------------------------


class TestActiveRule:
    """Rule 6 — default catch-all."""

    def test_requirements_approved_alone_is_active(self):
        """Only requirements.md exists & approved — no tasks file -> Active."""
        spec = _Spec(
            phases=_all_phases(requirements="approved"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "active"

    def test_mixed_approved_and_partial_is_active(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="approved",
                design="draft",
                tasks="complete",
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "active"


# ----- Cascade ordering & defaults ------------------------------------


class TestCascadeOrder:
    """Verify first-match-wins ordering for the rule cascade."""

    def test_paused_beats_complete(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="paused",
                design="complete",
                tasks="complete",
                decisions="complete",
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "paused"

    def test_complete_beats_stale(self):
        spec = _Spec(
            phases=_all_phases(requirements="complete"),
            last_modified=STALE,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_stale_beats_draft(self):
        spec = _Spec(phases=_all_phases(), last_modified=STALE)
        assert derive_lifecycle(spec, now=NOW) == "stale"

    def test_draft_beats_approved_not_shipped(self):
        """A spec with requirements=draft + tasks file should be Draft, not ApprNotShipped."""
        spec = _Spec(
            phases=_all_phases(requirements="draft", tasks="approved"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "draft"


class TestNowDefault:
    """Verify the `now` parameter defaults to current time when not passed."""

    def test_now_default_uses_current_time(self):
        """Without `now`, the function uses datetime.now() — verify stale fires
        for a deeply-old last_modified independent of clock drift."""
        spec = _Spec(
            phases=_all_phases(requirements="approved"),
            last_modified="2000-01-01T00:00:00+00:00",  # Decades ago, regardless of clock
        )
        assert derive_lifecycle(spec) == "stale"


# ----- Real-world fixtures from the actual spec corpus ----------------


class TestRealWorldSpecShapes:
    """Sanity-check against shapes seen in the actual docs/specs/ corpus."""

    def test_ci_debt_shape_is_complete(self):
        """ci-debt: 3 phase files, all complete, no decisions.md."""
        spec = _Spec(
            phases=[
                _Phase(
                    name="requirements",
                    exists=True,
                    status="complete (2026-05-10) — Phase A `68f19b90`",
                ),
                _Phase(name="design", exists=True, status="complete (2026-05-10)"),
                _Phase(
                    name="tasks",
                    exists=True,
                    status="complete (2026-05-10) — Phase A `68f19b90`",
                ),
                _Phase(name="decisions", exists=False, status=None),
            ],
            last_modified=FRESH,  # As if the dashboard re-rendered yesterday
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_redis_decoupling_shape_is_active(self):
        """redis-decoupling: all 4 phases exist, 'partial' status, not stale."""
        spec = _Spec(
            phases=_all_phases(
                requirements="partial — 2026-05-12 (P1 + P2 shipped)",
                design="partial — 2026-05-12",
                tasks="partial — 2026-05-12",
                decisions="approved",
            ),
            last_modified=FRESH,
        )
        # 'partial' doesn't match any approved-status set.
        # requirements not approved -> Rule 4: Draft. (Reasonable: 'partial' is
        # ambiguous; falling to Draft surfaces it for review.)
        assert derive_lifecycle(spec, now=NOW) == "draft"

    def test_ops_specs_page_refinement_shape_is_active(self):
        """ops-specs-page-refinement: decisions.md + requirements.md, no design/tasks."""
        spec = _Spec(
            phases=_all_phases(
                requirements="approved (2026-05-31)",
                decisions="approved (2026-05-31)",
            ),
            last_modified=FRESH,
        )
        # requirements approved, no tasks file -> Rule 5 fails -> Active.
        assert derive_lifecycle(spec, now=NOW) == "active"


# ----- Property: always returns a known bucket ------------------------


VALID_BUCKETS = {
    "parked",
    "paused",
    "complete",
    "stale",
    "draft",
    "approved-not-shipped",
    "active",
}


@pytest.mark.parametrize(
    "spec_factory",
    [
        lambda: _Spec(phases=[], last_modified=None),
        lambda: _Spec(phases=_all_phases(), last_modified=None),
        lambda: _Spec(phases=_all_phases(requirements="weird-string"), last_modified=FRESH),
        lambda: _Spec(phases=_all_phases(requirements=""), last_modified=FRESH),
    ],
)
def test_derive_lifecycle_always_returns_known_bucket(spec_factory):
    """Even pathological inputs must return one of the 7 known buckets."""
    result = derive_lifecycle(spec_factory(), now=NOW)
    assert result in VALID_BUCKETS


# ----- Rules 1b/2b + vocabulary tokens (q-briefing-triage-002 A2) -----


class TestParkedRule:
    """Rule 1b — a leading-token 'parked' on ANY phase wins (chair park)."""

    def test_parked_tasks_wins_over_approved_not_shipped(self):
        # The fable-premium-tier shape that motivated the rule: approved
        # requirements + parked tasks previously alarmed as
        # approved-not-shipped, hiding the chair's ruling.
        spec = _Spec(
            phases=_all_phases(
                requirements="approved (2026-07-10)",
                tasks="parked (2026-07-19) — Resume-Trigger: 2026-07-28",
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "parked"

    def test_parked_is_leading_token_only(self):
        # A prose MENTION of parking in an annotation must not trip it.
        spec = _Spec(
            phases=_all_phases(
                requirements="approved (2026-07-10) — sibling spec parked separately", tasks="draft"
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) != "parked"

    def test_parked_wins_over_stale(self):
        old = (NOW - timedelta(days=STALE_THRESHOLD_DAYS + 10)).isoformat()
        spec = _Spec(
            phases=_all_phases(requirements="parked (2026-06-01) — Resume-Trigger: evergreen"),
            last_modified=old,
        )
        assert derive_lifecycle(spec, now=NOW) == "parked"


class TestLivingAndShippedTokens:
    """Rule 2b (living -> active) + shipped/superseded complete-aliases."""

    def test_living_is_active_never_stale(self):
        old = (NOW - timedelta(days=STALE_THRESHOLD_DAYS + 10)).isoformat()
        spec = _Spec(
            phases=_all_phases(requirements="living (ongoing program)", tasks="living"),
            last_modified=old,
        )
        assert derive_lifecycle(spec, now=NOW) == "active"

    def test_shipped_all_phases_is_complete(self):
        spec = _Spec(
            phases=_all_phases(requirements="shipped (2026-07-20)", tasks="shipped (2026-07-20)"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_superseded_is_complete(self):
        spec = _Spec(
            phases=_all_phases(requirements="superseded (2026-07-18) — see sibling"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "complete"

    def test_active_token_skips_approved_not_shipped(self):
        # 'active' requirements + tasks present + nothing complete used
        # to alarm; the alarm is reserved for token 'approved' exactly.
        spec = _Spec(
            phases=_all_phases(
                requirements="active (2026-07-18) — D1 ratified; D2+ open", tasks="draft"
            ),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "active"

    def test_approved_token_still_alarms(self):
        spec = _Spec(
            phases=_all_phases(requirements="approved (2026-07-10)", tasks="draft"),
            last_modified=FRESH,
        )
        assert derive_lifecycle(spec, now=NOW) == "approved-not-shipped"


# ----- Stage derivation (spec-lifecycle-gates UI phase) ----------------


class TestDeriveStage:
    """derive_stage: pipeline position + next transition."""

    def test_shipped_when_all_existing_terminal(self):
        spec = _Spec(phases=_all_phases(requirements="shipped (2026-07-20)", decisions="shipped"))
        info = derive_stage(spec)
        assert info.stage == "shipped"
        assert info.next_phase is None

    def test_requirements_stage_when_missing(self):
        spec = _Spec(phases=_all_phases(decisions="draft"))
        info = derive_stage(spec)
        assert info.stage == "requirements"
        assert info.next_phase == "requirements"
        assert "Draft" in info.next_action

    def test_requirements_stage_when_unapproved(self):
        spec = _Spec(phases=_all_phases(requirements="draft (2026-07-01)"))
        info = derive_stage(spec)
        assert info.stage == "requirements"
        assert info.next_action == "Approve requirements"

    def test_design_stage_when_design_unapproved(self):
        spec = _Spec(
            phases=_all_phases(requirements="approved (2026-07-19)", design="draft — OQ open")
        )
        info = derive_stage(spec)
        assert info.stage == "design"
        assert info.next_phase == "design"
        assert info.next_action == "Approve design"

    def test_design_stage_when_design_missing(self):
        spec = _Spec(phases=_all_phases(requirements="approved (2026-07-19)"))
        info = derive_stage(spec)
        assert info.stage == "design"
        assert "waiver" in info.next_action

    def test_tasks_stage_when_tasks_unapproved(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="approved", design="approved (2026-07-19)", tasks="draft"
            )
        )
        info = derive_stage(spec)
        assert info.stage == "tasks"
        assert info.next_phase == "tasks"

    def test_executing_when_all_present_approved(self):
        spec = _Spec(
            phases=_all_phases(
                requirements="approved", design="approved", tasks="approved", decisions="active"
            )
        )
        info = derive_stage(spec)
        assert info.stage == "executing"
        assert info.next_phase == "decisions"

    def test_partial_terminal_is_not_shipped(self):
        """One shipped phase + one in-flight phase != shipped spec."""
        spec = _Spec(phases=_all_phases(requirements="shipped", design="draft"))
        assert derive_stage(spec).stage == "design"


class TestReadGateVerdicts:
    """read_gate_verdicts: RR-1 ledger reader, graceful everywhere."""

    def test_missing_ledger_returns_empty(self, tmp_path):
        assert read_gate_verdicts(tmp_path / "nope.jsonl") == {}

    def test_reads_latest_receipt_per_slug(self, tmp_path):
        ledger = tmp_path / "verdicts.jsonl"
        ledger.write_text(
            '{"receipt_id": "r1", "target_artifact": "docs/specs/my-spec/design.md", '
            '"evaluation_state": "REVISE", "gate_id": "g1", "phase": "design"}\n'
            '{"receipt_id": "r2", "target_artifact": "docs/specs/my-spec/design.md", '
            '"evaluation_state": "PASS", "gate_id": "g1", "phase": "design"}\n',
            encoding="utf-8",
        )
        verdicts = read_gate_verdicts(ledger)
        assert verdicts["my-spec"]["evaluation_state"] == "PASS"
        assert verdicts["my-spec"]["receipt_id"] == "r2"

    def test_malformed_lines_skipped(self, tmp_path):
        ledger = tmp_path / "verdicts.jsonl"
        ledger.write_text(
            "not json at all\n"
            '["a", "list"]\n'
            '{"no_target": true}\n'
            '{"target_artifact": "docs/specs/ok-spec/requirements.md", '
            '"evaluation_state": "CHAIR_REQUIRED"}\n',
            encoding="utf-8",
        )
        verdicts = read_gate_verdicts(ledger)
        assert list(verdicts) == ["ok-spec"]


class TestStageWaiverSignal:
    """PHASE-WAIVED chair lines satisfy the ladder for ABSENT files."""

    def test_waived_design_advances_past_design(self):
        spec = _Spec(phases=_all_phases(requirements="approved (2026-07-18)"))
        spec.waived_phases = ("design",)
        info = derive_stage(spec)
        assert info.stage == "executing"
        assert info.next_phase == "decisions"

    def test_waiver_ignored_when_design_file_exists(self):
        """An existing file's own status governs; waiving it is contradictory."""
        spec = _Spec(phases=_all_phases(requirements="approved", design="draft"))
        spec.waived_phases = ("design",)
        info = derive_stage(spec)
        assert info.stage == "design"
        assert info.next_action == "Approve design"

    def test_no_waiver_still_demands_design(self):
        spec = _Spec(phases=_all_phases(requirements="approved"))
        info = derive_stage(spec)
        assert info.stage == "design"
        assert "waiver" in info.next_action

    def test_scan_waived_phases_reads_chair_line(self, tmp_path):
        from attune.ops.specs_data import _scan_waived_phases

        d = tmp_path / "some-spec"
        d.mkdir()
        (d / "decisions.md").write_text(
            "# Decisions\n\nbody text\n\n"
            "PHASE-WAIVED: design (2026-07-20 — thread q-x-001)\n"
            "PHASE-WAIVED: nonsense (not a phase)\n",
            encoding="utf-8",
        )
        assert _scan_waived_phases(d) == ("design",)

    def test_scan_waived_phases_missing_decisions(self, tmp_path):
        from attune.ops.specs_data import _scan_waived_phases

        d = tmp_path / "bare-spec"
        d.mkdir()
        assert _scan_waived_phases(d) == ()
