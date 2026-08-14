"""Tests for the advisory curated-memory staleness audit.

Every fixture is built under ``tmp_path``. Nothing here reads the real home
directory — a test that did would leak a machine-specific dependency into CI
and violate the home-directory isolation guard.

The ranking tests pin **both directions**. A change that flags everything
must fail as loudly as one that flags nothing; see
``docs/specs/memory-status-integrity/requirements.md`` § Acceptance.
"""

from __future__ import annotations

import hashlib
import os
from datetime import date, datetime, timedelta
from datetime import time as clock_time
from pathlib import Path

import pytest

from attune.memory.curated_audit import (
    DEFAULT_VOLATILITY,
    annotate,
    audit,
    epistemic_tier,
    format_age_annotation,
    format_status_annotation,
    load_memory,
    resolve_age_basis,
    risk_score,
    scan_corpus,
    sweep,
    unverified_age_days,
    volatility,
)
from attune.memory.verdict_log import VERDICTS_FILENAME, VerdictRecord, append_verdict

TODAY = date(2026, 8, 7)


def write_memory(
    root: Path,
    stem: str,
    mem_type: str = "project",
    *,
    description: str = "a memory",
    body: str = "The claim.",
    age_days: int = 0,
    extra_frontmatter: str = "",
    name: str | None = None,
) -> Path:
    """Write one curated memory and backdate its mtime by ``age_days``."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{stem}.md"
    path.write_text(
        "---\n"
        f"name: {name if name is not None else stem}\n"
        f"description: {description}\n"
        "metadata:\n"
        f"  type: {mem_type}\n"
        f"{extra_frontmatter}"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    # Anchor to local NOON of the target date rather than subtracting raw
    # seconds from now. Second-arithmetic lands on an arbitrary wall-clock
    # time, so a run near local midnight — or across a DST transition —
    # backdates to the wrong calendar day and the age assertions drift by one.
    # Anchor to the module's pinned TODAY, not the real clock: the audit
    # assertions compare against TODAY, so a real-clock anchor makes every
    # fixture age one day younger per real day (and timezone-dependent) —
    # broke calendar-wide on 2026-08-14 when the 56-day fixture hit 49.
    target = TODAY - timedelta(days=age_days)
    stamp = datetime.combine(target, clock_time(12, 0)).timestamp()
    os.utime(path, (stamp, stamp))
    return path


def write_index(root: Path, stems: list[str]) -> Path:
    """Write a MEMORY.md index pointing at the given stems."""
    lines = [f"- [{stem}]({stem}.md) — hook" for stem in stems]
    path = root / "MEMORY.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestParsing:
    def test_parses_the_mandated_schema(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "project_thing", "project", description="hi")
        mem = load_memory(path)
        assert mem.name == "project_thing"
        assert mem.description == "hi"
        assert mem.mem_type == "project"
        assert mem.unknown_keys == ()

    def test_provenance_key_is_tolerated_alongside_a_valid_type(self, tmp_path: Path) -> None:
        """``node_type`` is platform provenance, not drift.

        The canonical linter (~/.claude/hooks/memory_lint.py, lines 188-194)
        tolerates it whenever a valid ``metadata.type`` is present. Reporting
        it as a violation would put this sweep in permanent disagreement with
        the enforcement mechanism — and did, until a live ``--check-all`` run
        on 2026-08-07 showed the real corpus at 0 violations.
        """
        path = write_memory(tmp_path, "p_one", extra_frontmatter="  node_type: memory\n")
        assert load_memory(path).unknown_keys == ()

    def test_provenance_key_is_flagged_when_it_substitutes_for_type(self, tmp_path: Path) -> None:
        """The drift the rule was actually written to catch."""
        path = write_memory(
            tmp_path, "p_one_b", mem_type="bogus", extra_frontmatter="  node_type: memory\n"
        )
        assert "metadata.node_type" in load_memory(path).unknown_keys

    def test_lesson_type_does_not_activate_provenance_tolerance(self, tmp_path: Path) -> None:
        """Linter parity: ``lesson`` is NOT in memory_lint's ALLOWED_TYPES.

        An earlier version of this module accepted ``type: lesson`` and let
        it activate the provenance tolerance — so a file the canonical
        linter flags twice (invalid type + stray node_type) was completely
        invisible to the sweep. Per D4 the enforcement code is the
        authority; this pins the parity.
        """
        path = write_memory(
            tmp_path, "lesson_x", mem_type="lesson", extra_frontmatter="  node_type: memory\n"
        )
        assert "metadata.node_type" in load_memory(path).unknown_keys

    def test_invalid_type_is_reported(self, tmp_path: Path) -> None:
        """A present-but-unrecognised metadata.type is definite drift.

        For corpora with no linter of their own (attune's ~/.attune store),
        this sweep is the only checker — the linter's type rule must be
        represented here or invalid types are undetectable there.
        """
        write_memory(tmp_path, "lesson_y", mem_type="lesson")
        write_memory(tmp_path, "project_ok", mem_type="project")

        report = audit(scan_corpus([tmp_path]), today=TODAY)
        assert [(p.stem, t) for p, t in report.invalid_types] == [("lesson_y", "lesson")]
        assert not report.clean

    def test_missing_type_is_not_reported_as_invalid(self, tmp_path: Path) -> None:
        """Absence is not value-drift — sweep roots may include corpora with
        a different file format where the linter claims no jurisdiction."""
        (tmp_path / "kindfile.md").write_text("# just a heading\n\nprose\n", encoding="utf-8")
        report = audit(scan_corpus([tmp_path]), today=TODAY)
        assert report.invalid_types == ()

    def test_flags_forbidden_top_level_key(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "p_two", extra_frontmatter="type: project\n")
        assert "type" in load_memory(path).unknown_keys

    def test_verified_field_is_tolerated_before_p2(self, tmp_path: Path) -> None:
        """A file carrying the future P2 key must not read as a violation."""
        path = write_memory(tmp_path, "p_three", extra_frontmatter="verified: 2026-08-01\n")
        mem = load_memory(path)
        assert mem.verified == date(2026, 8, 1)
        assert mem.unknown_keys == ()

    def test_folded_description_continuation_is_not_a_key(self, tmp_path: Path) -> None:
        """P2 gate (D6#1): parser alignment with the canonical linter.

        A folded multi-line ``description: >`` whose continuation lines
        contain ``:`` used to parse those lines as unknown top-level keys —
        a false positive on exactly the drifting files the ``verified:``
        loop depends on. The canonical linter counts only non-indented keys.
        """
        path = tmp_path / "p_folded.md"
        path.write_text(
            "---\n"
            "name: p_folded\n"
            "description: >\n"
            "  recall 6/6 vs grep-baseline: 5/6;\n"
            "  OR-mode required: always\n"
            "metadata:\n"
            "  type: project\n"
            "verified: 2026-08-01\n"
            "---\n\nThe claim.\n",
            encoding="utf-8",
        )
        mem = load_memory(path)
        assert mem.unknown_keys == ()
        assert mem.description == "recall 6/6 vs grep-baseline: 5/6; OR-mode required: always"
        assert mem.verified == date(2026, 8, 1)

    def test_literal_block_description_joins_and_terminates(self, tmp_path: Path) -> None:
        """``|`` literal blocks behave like folded ones, and the first
        non-indented key after the block ends continuation collection."""
        path = tmp_path / "p_literal.md"
        path.write_text(
            "---\n"
            "name: p_literal\n"
            "description: |\n"
            "  line one: a\n"
            "  line two: b\n"
            "metadata:\n"
            "  type: reference\n"
            "---\n\nBody.\n",
            encoding="utf-8",
        )
        mem = load_memory(path)
        assert mem.unknown_keys == ()
        assert mem.description == "line one: a line two: b"
        assert mem.mem_type == "reference"

    def test_folded_block_as_last_frontmatter_key_flushes(self, tmp_path: Path) -> None:
        path = tmp_path / "p_tail_fold.md"
        path.write_text(
            "---\n"
            "name: p_tail_fold\n"
            "metadata:\n"
            "  type: user\n"
            "description: >\n"
            "  tail folded: value\n"
            "---\n\nBody.\n",
            encoding="utf-8",
        )
        mem = load_memory(path)
        assert mem.unknown_keys == ()
        assert mem.description == "tail folded: value"

    def test_block_scalar_headers_with_indent_digit_or_comment(self, tmp_path: Path) -> None:
        """Codex D11 finding: ``>2`` / ``|2-`` / ``> # comment`` headers are
        valid YAML block scalars too — their continuation must be collected,
        not discarded with the indicator retained as the value."""
        for stem, header in [
            ("p_fold_digit", ">2"),
            ("p_lit_digit_chomp", "|2-"),
            ("p_fold_comment", "> # folded on purpose"),
        ]:
            path = tmp_path / f"{stem}.md"
            path.write_text(
                "---\n"
                f"name: {stem}\n"
                f"description: {header}\n"
                "  the real: text\n"
                "metadata:\n"
                "  type: project\n"
                "---\n\nBody.\n",
                encoding="utf-8",
            )
            mem = load_memory(path)
            assert mem.unknown_keys == (), stem
            assert mem.description == "the real: text", stem

    def test_unknown_key_with_block_scalar_flags_only_the_key(self, tmp_path: Path) -> None:
        """Both directions: the forbidden key is still flagged exactly once,
        and its continuation lines are not flagged as further keys."""
        path = tmp_path / "p_unknown_fold.md"
        path.write_text(
            "---\n"
            "name: p_unknown_fold\n"
            "description: fine\n"
            "notes: >\n"
            "  stray: content\n"
            "  more: content\n"
            "metadata:\n"
            "  type: project\n"
            "---\n\nBody.\n",
            encoding="utf-8",
        )
        mem = load_memory(path)
        assert mem.unknown_keys == ("notes",)

    def test_deferred_link_is_not_a_link(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "p_four", body="See [[?not_yet]] and [[real]].")
        mem = load_memory(path)
        assert mem.links == ("real",)
        assert mem.deferred_links == ("not_yet",)

    def test_unreadable_file_does_not_raise(self, tmp_path: Path) -> None:
        """One bad file must not stop the sweep reporting on the rest."""
        path = tmp_path / "broken.md"
        path.write_bytes(b"\xff\xfe not utf-8")
        assert load_memory(path).name is None


class TestAge:
    def test_age_from_mtime_when_unverified(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "p_age", age_days=61)
        assert unverified_age_days(load_memory(path), TODAY) == 61

    def test_verified_date_wins_over_mtime(self, tmp_path: Path) -> None:
        path = write_memory(
            tmp_path,
            "p_verified",
            age_days=61,
            extra_frontmatter="verified: 2026-08-05\n",
        )
        assert unverified_age_days(load_memory(path), TODAY) == 2

    def test_age_never_negative(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "p_future", extra_frontmatter="verified: 2099-01-01\n")
        assert unverified_age_days(load_memory(path), TODAY) == 0


class TestVerdictBinding:
    """P2 tasks 2+4: digest binding decides whether ``verified:`` stands."""

    def _verified(self, root: Path, stem: str = "project_v", body: str = "The claim.\n"):
        path = write_memory(
            root, stem, "project", body=body, extra_frontmatter="verified: 2026-07-01\n"
        )
        return load_memory(path)

    def _verdict_for(self, mem, verdict: str = "keep") -> VerdictRecord:
        return VerdictRecord.create(mem.stem, verdict, mem.digest, who="patrick")

    def test_basis_label_matrix(self, tmp_path: Path) -> None:
        plain = load_memory(write_memory(tmp_path, "project_plain"))
        assert resolve_age_basis(plain) == (plain.mtime_date, "mtime")

        mem = self._verified(tmp_path)
        assert resolve_age_basis(mem) == (date(2026, 7, 1), "verified-unbound")

        bound = self._verdict_for(mem)
        assert resolve_age_basis(mem, bound) == (date(2026, 7, 1), "verified")

        stale = VerdictRecord.create(mem.stem, "keep", "some-other-digest", who="patrick")
        assert resolve_age_basis(mem, stale) == (mem.mtime_date, "invalidated")

        wrong = self._verdict_for(mem, "wrong")
        assert resolve_age_basis(mem, wrong) == (mem.mtime_date, "tombstoned")

    def test_tombstone_applies_without_a_verified_field(self, tmp_path: Path) -> None:
        """Codex D11 finding: a `wrong` verdict on an UNVERIFIED memory must
        still read tombstoned — the earlier ordering returned plain mtime."""
        mem = load_memory(write_memory(tmp_path, "project_unverified"))
        wrong = VerdictRecord.create(mem.stem, "wrong", mem.digest, who="patrick")
        assert resolve_age_basis(mem, wrong) == (mem.mtime_date, "tombstoned")

    def test_verdicts_scope_to_their_own_corpus(self, tmp_path: Path) -> None:
        """Codex D11 finding: a verdict in corpus A must never bind or
        tombstone a same-named memory in corpus B."""
        root_a = tmp_path / "corpus_a"
        root_b = tmp_path / "corpus_b"
        mem_a = self._verified(root_a, stem="project_shared")
        self._verified(root_b, stem="project_shared")
        append_verdict(root_a, self._verdict_for(mem_a, "wrong"))

        report = sweep([root_a, root_b], today=TODAY)
        bases = {
            (mem.path.parent.name, stem): basis
            for (mem, _), (stem, basis, _) in zip(report.ranked, report.age_bases, strict=False)
        }
        assert bases[("corpus_a", "project_shared")] == "tombstoned"
        assert bases[("corpus_b", "project_shared")] == "verified-unbound"

    def test_invalidation_reroutes_age_to_mtime(self, tmp_path: Path) -> None:
        """A substantive edit voids the verified date (D6 #2)."""
        mem = self._verified(tmp_path)
        stale = VerdictRecord.create(mem.stem, "keep", "different", who="patrick")
        assert unverified_age_days(mem, TODAY, stale) == max(0, (TODAY - mem.mtime_date).days)
        assert unverified_age_days(mem, TODAY, self._verdict_for(mem)) == 37

    def test_formatting_only_edit_preserves_the_binding(self, tmp_path: Path) -> None:
        mem = self._verified(tmp_path, body="line one\nline two\n")
        verdict = self._verdict_for(mem)

        reformatted = self._verified(tmp_path, body="line one   \n\n\nline two\n")
        assert resolve_age_basis(reformatted, verdict)[1] == "verified"

        reworded = self._verified(tmp_path, body="line one\nline three\n")
        assert resolve_age_basis(reworded, verdict)[1] == "invalidated"

    def test_sweep_reads_the_log_and_reports_per_file_basis(self, tmp_path: Path) -> None:
        mem = self._verified(tmp_path)
        write_memory(tmp_path, "project_bare")
        append_verdict(tmp_path, self._verdict_for(mem))

        report = sweep([tmp_path], today=TODAY)
        bases = {(stem, basis) for stem, basis, _ in report.age_bases}
        assert bases == {("project_v", "verified"), ("project_bare", "mtime")}
        days = {stem: d for stem, _, d in report.age_bases}
        assert days["project_v"] == 37, "JSON/report days must be basis-aware"
        scores = {m.stem: s for m, s in report.ranked}
        assert scores["project_v"] == pytest.approx(37.0)

    def test_sweep_leaves_log_and_corpus_byte_identical(self, tmp_path: Path) -> None:
        """The advisory posture extends to the verdict log: sweep only reads."""
        mem = self._verified(tmp_path)
        append_verdict(tmp_path, self._verdict_for(mem))
        log = tmp_path / VERDICTS_FILENAME
        before = log.read_bytes()

        sweep([tmp_path], today=TODAY)
        assert log.read_bytes() == before


class TestFrequencyRanking:
    """P3 task 5: the R6 fold — age × volatility × serve frequency."""

    def test_factor_floor_and_monotonic_growth(self) -> None:
        from attune.memory.curated_audit import FREQUENCY_FLOOR, frequency_factor

        assert frequency_factor(0) == FREQUENCY_FLOOR
        assert frequency_factor(-5) == FREQUENCY_FLOOR, "negative counts clamp"
        assert frequency_factor(1) > frequency_factor(0)
        assert frequency_factor(30) > frequency_factor(5) > frequency_factor(1)

    def test_none_serves_is_neutral_not_floor(self, tmp_path: Path) -> None:
        """No frequency evidence must keep the score AGE-ONLY — pretending
        every memory is unserved would silently scale real scores."""
        mem = load_memory(write_memory(tmp_path, "project_x", age_days=40))
        base = risk_score(mem, TODAY)
        assert risk_score(mem, TODAY, None, None) == base
        assert risk_score(mem, TODAY, None, 0) < base

    def test_audit_rank_basis_states_what_ordered_it(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a", age_days=10)
        age_only = audit(scan_corpus([tmp_path]), today=TODAY)
        assert age_only.rank_basis == "age-only"
        assert age_only.serves_by_stem == ()

        with_freq = audit(scan_corpus([tmp_path]), today=TODAY, serves={"project_a": 3})
        assert with_freq.rank_basis == "age×frequency"
        assert dict(with_freq.serves_by_stem) == {"project_a": 3}

    def test_served_memory_outranks_equally_old_unserved(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_hot", age_days=40)
        write_memory(tmp_path, "project_cold", age_days=40)
        report = audit(scan_corpus([tmp_path]), today=TODAY, serves={"project_hot": 20})
        order = [mem.stem for mem, _ in report.ranked]
        assert order.index("project_hot") < order.index("project_cold")


class TestAcceptanceProofCases:
    """Requirements § Acceptance: the two 2026-07-10 proof cases MUST
    produce OPPOSITE outcomes — a change catching both is as wrong as
    one catching neither."""

    def _corpus(self, tmp_path: Path):
        # The pip-audit shape: 8 weeks stale, served in every session.
        write_memory(tmp_path, "project_pip_audit_class", age_days=56)
        # The rag-gate shape: wrong within HOURS — brand new by mtime.
        write_memory(tmp_path, "project_rag_gate_class", age_days=0)
        # Background noise: an older-but-never-served project memory and
        # a settled feedback rule.
        write_memory(tmp_path, "project_unserved_older", age_days=63)
        write_memory(tmp_path, "feedback_settled", "feedback", age_days=120)
        return scan_corpus([tmp_path])

    def test_stale_high_serve_ranks_top(self, tmp_path: Path) -> None:
        report = audit(
            self._corpus(tmp_path),
            today=TODAY,
            serves={"project_pip_audit_class": 25, "project_rag_gate_class": 25},
        )
        top_stem = report.ranked[0][0].stem
        assert top_stem == "project_pip_audit_class", (
            "the 8-week-stale, served-every-session memory must surface "
            f"TOP-ranked; got {top_stem}"
        )
        # And it carries a visible unverified-age at recall.
        top_mem = report.ranked[0][0]
        expected_days = unverified_age_days(top_mem, TODAY)
        assert expected_days >= 50, "fixture must stay ~8 weeks stale"
        assert f"{expected_days} days unverified" in annotate("x", top_mem, TODAY)

    def test_hours_old_memory_is_not_claimed(self, tmp_path: Path) -> None:
        """The rag-gate case rotted in HOURS — no age mechanism can catch
        it, and this sweep must not pretend to."""
        report = audit(
            self._corpus(tmp_path),
            today=TODAY,
            serves={"project_pip_audit_class": 25, "project_rag_gate_class": 25},
        )
        scores = {mem.stem: score for mem, score in report.ranked}
        assert scores["project_rag_gate_class"] == 0.0, (
            "an hours-old memory must score zero — flagging it would claim "
            "a detection this mechanism cannot make"
        )
        bases = {stem: basis for stem, basis, _ in report.age_bases}
        tier = epistemic_tier("project", bases["project_rag_gate_class"], 0)
        assert tier == "settled"


class TestEpistemicTiers:
    """P2 task 8: calibrated tiers, not bare day-counts (D6 #5)."""

    def test_tier_calibrates_by_type_volatility(self) -> None:
        # 61 days: suspect for project (61 x 1.0 > 45), settled for
        # feedback (61 x 0.15 = 9.15 <= 10) — the base-rate gap D6#5 names.
        assert epistemic_tier("project", "mtime", 61) == "suspect"
        assert epistemic_tier("feedback", "mtime", 61) == "settled"
        assert epistemic_tier("project", "mtime", 39) == "check-before-acting"
        assert epistemic_tier("reference", "mtime", 3) == "settled"

    def test_tombstoned_and_invalidated_are_suspect_regardless_of_age(self) -> None:
        assert epistemic_tier("feedback", "tombstoned", 0) == "suspect"
        assert epistemic_tier("user", "invalidated", 1) == "suspect"

    def test_suspect_project_carries_the_explicit_instruction(self) -> None:
        label = format_status_annotation("project", "mtime", 61)
        assert label.startswith("⟨suspect · project · 61d unverified⟩")
        assert "verify against the repo before acting" in label

    def test_non_project_suspect_has_no_repo_instruction(self) -> None:
        label = format_status_annotation("reference", "mtime", 200)
        assert "suspect" in label
        assert "verify against the repo" not in label

    def test_verification_states_render_distinctly(self) -> None:
        assert "verified 3d ago" in format_status_annotation("project", "verified", 3)
        assert "unbound" in format_status_annotation("project", "verified-unbound", 3)
        assert "voided by edit" in format_status_annotation("project", "invalidated", 3)
        assert "judged WRONG" in format_status_annotation("project", "tombstoned", 3)


class TestAnnotation:
    @pytest.mark.parametrize(
        ("days", "expected"),
        [(0, "verified today"), (1, "1 day unverified"), (61, "61 days unverified")],
    )
    def test_annotation_text(self, days: int, expected: str) -> None:
        assert expected in format_age_annotation(days)

    def test_annotate_appends_to_rendered_text(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "p_ann", age_days=5)
        out = annotate("the memory line", load_memory(path), TODAY)
        assert out.startswith("the memory line")
        assert "5 days unverified" in out


class TestRankingPinsBothDirections:
    """The core acceptance from requirements § Acceptance.

    Age alone is the wrong ranking signal — see decisions.md D1. These tests
    fail if someone reverts risk to raw age, and they fail if someone starts
    treating the hours-old case as catchable by staleness.
    """

    def test_stale_project_outranks_older_feedback(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_pip_audit_broken", "project", age_days=56)
        for i in range(3):
            write_memory(tmp_path, f"feedback_rule_{i}", "feedback", age_days=66)

        report = audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path])
        top = report.ranked[0][0]

        assert top.stem == "project_pip_audit_broken", (
            "the stale project memory must rank first even though the "
            "feedback rules are older — ranking by raw age is the sign error "
            "D1 rejects"
        )

    def test_hours_old_project_memory_is_not_flagged(self, tmp_path: Path) -> None:
        """D1 boundary marker.

        ``project_rag_gate_corpus_stale`` was wrong within hours. No
        age-based mechanism can catch it, and this spec must not pretend to.
        If a later change makes the curated sweep start machine-verifying
        claims in order to catch this case, this test fails — that is the
        intent.
        """
        write_memory(tmp_path, "project_rag_gate_corpus_stale", "project", age_days=0)
        write_memory(tmp_path, "project_old_thing", "project", age_days=40)

        report = audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path])
        scores = {mem.stem: score for mem, score in report.ranked}

        assert scores["project_rag_gate_corpus_stale"] == 0.0
        assert report.ranked[-1][0].stem == "project_rag_gate_corpus_stale"

    def test_user_and_feedback_rank_below_project_at_equal_age(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a", "project", age_days=30)
        write_memory(tmp_path, "feedback_b", "feedback", age_days=30)
        write_memory(tmp_path, "user_c", "user", age_days=30)

        order = [mem.stem for mem, _ in audit(scan_corpus([tmp_path]), today=TODAY).ranked]
        assert order == ["project_a", "feedback_b", "user_c"]

    def test_unknown_type_surfaces_rather_than_hides(self) -> None:
        assert volatility(None) == DEFAULT_VOLATILITY
        assert volatility("nonsense") == DEFAULT_VOLATILITY
        assert DEFAULT_VOLATILITY > volatility("feedback")

    def test_risk_is_age_times_volatility(self, tmp_path: Path) -> None:
        path = write_memory(tmp_path, "project_x", "project", age_days=10)
        assert risk_score(load_memory(path), TODAY) == pytest.approx(10.0)


class TestIntegrity:
    def test_broken_link_reported_and_deferred_link_is_not(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a", body="See [[project_gone]] and [[?later]].")
        write_index(tmp_path, ["project_a"])

        report = audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path])
        assert [link for _, link in report.broken_links] == ["project_gone"]

    def test_name_must_equal_filename_stem(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a", name="something_else")
        report = audit(scan_corpus([tmp_path]), today=TODAY)
        assert [p.stem for p in report.name_mismatches] == ["project_a"]

    def test_orphan_and_dangling_pointer_both_reported(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_indexed")
        write_memory(tmp_path, "project_orphan")
        write_index(tmp_path, ["project_indexed", "project_never_written"])

        report = audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path])
        assert [p.stem for p in report.orphans] == ["project_orphan"]
        assert [stem for _, stem in report.dangling_pointers] == ["project_never_written"]

    def test_index_file_is_not_itself_a_memory(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a")
        write_index(tmp_path, ["project_a"])
        assert [m.stem for m in scan_corpus([tmp_path])] == ["project_a"]

    def test_table_form_index_counts_as_a_pointer(self, tmp_path: Path) -> None:
        """Some indexes are tables, not link lists — a bare mention indexes.

        Requiring the markdown-link form produced 21 false orphans against
        the real corpus on 2026-08-07.
        """
        write_memory(tmp_path, "project_a")
        (tmp_path / "MEMORY.md").write_text(
            "| file | note |\n|---|---|\n| project_a.md | a thing |\n",
            encoding="utf-8",
        )
        assert audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path]).orphans == ()

    def test_corpus_without_an_index_has_no_orphans(self, tmp_path: Path) -> None:
        """No MEMORY.md means no pointer requirement — the linter self-skips."""
        write_memory(tmp_path, "project_a")
        write_memory(tmp_path, "project_b")
        assert audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path]).orphans == ()

    def test_clean_corpus_reports_clean(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a")
        write_index(tmp_path, ["project_a"])
        assert audit(scan_corpus([tmp_path]), today=TODAY, roots=[tmp_path]).clean


class TestAdvisoryByConstruction:
    def test_sweep_leaves_the_corpus_byte_identical(self, tmp_path: Path) -> None:
        """The sweep must never write. This is the whole posture of the spec."""
        write_memory(tmp_path, "project_a", age_days=90, body="[[project_gone]]")
        write_memory(tmp_path, "feedback_b", "feedback", age_days=120)
        write_index(tmp_path, ["project_a"])

        def digest() -> dict[str, str]:
            return {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(tmp_path.rglob("*.md"))
            }

        before = digest()
        report = sweep([tmp_path])
        assert report.scanned == 2
        assert digest() == before

    def test_no_memory_is_dropped_from_the_report(self, tmp_path: Path) -> None:
        """D1: age never removes a memory from a result — only ranks it."""
        write_memory(tmp_path, "user_ancient", "user", age_days=3650)
        write_memory(tmp_path, "project_fresh", "project", age_days=0)

        report = sweep([tmp_path])
        assert {mem.stem for mem, _ in report.ranked} == {
            "user_ancient",
            "project_fresh",
        }

    def test_missing_root_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a")
        report = sweep([tmp_path, tmp_path / "does_not_exist"])
        assert report.scanned == 1

    def test_age_basis_is_reported(self, tmp_path: Path) -> None:
        write_memory(tmp_path, "project_a")
        assert sweep([tmp_path]).age_basis == "mtime"

        write_memory(tmp_path, "project_b", extra_frontmatter="verified: 2026-08-01\n")
        assert sweep([tmp_path]).age_basis == "verified"
