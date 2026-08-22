"""Residual packet, schema v1 (release-audit-stage R4).

The properties that matter are the REFUSALS and the SCOPE rules, not
the happy path: a packet that quietly truncated, or that let warnings
crowd out hits, would let a chair rule on a subset while believing they
ruled on the whole.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.classes.baseline import Baseline
from attune.classes.packet import (
    DISPOSITIONS,
    MAX_ITEMS,
    PacketOverCap,
    build_packet,
)

_CALIBRATED = {
    "invariant": "parsed then used unguarded",
    "class_ids": ["C3"],
    "calibrated_here": True,
    "calibration": {"repo": "r", "recall": 0.72, "precision": 1.0},
}
_ADVISORY = {
    "invariant": "same shape, uncalibrated here",
    "class_ids": ["C9"],
    "calibrated_here": False,
    "calibration": {"repo": "other/repo", "recall": 0.1, "precision": 0.0},
}


def _baseline(**kw) -> Baseline:
    return Baseline(
        tag=kw.pop("tag", "v1.0.0"),
        baseline_sha="a" * 40,
        head_sha="b" * 40,
        source="last-release-tag",
        changed=kw.pop("changed", ("src/attune/mod.py",)),
        deleted=kw.pop("deleted", ()),
    )


def _sweep(hits, rules=None):
    return {"hits": hits, "rules": rules or {"R1": _CALIBRATED}, "scan_errors": []}


def _hit(line, rule_id="R1"):
    return {"rule_id": rule_id, "path": "src/attune/mod.py", "line": line, "detail": "d"}


def _register(rows=()):
    return {"rows": list(rows), "scan_errors": [], "defer_problems": []}


class TestOverCapIsARefusal:
    def test_too_many_items_raises_rather_than_truncating(self, tmp_path):
        hits = [_hit(i) for i in range(MAX_ITEMS + 3)]

        with pytest.raises(PacketOverCap) as exc:
            build_packet(_baseline(), _sweep(hits), _register(), repo_root=tmp_path)

        breach = exc.value.diagnostics["breaches"][0]
        assert breach["cap"] == "items"
        assert breach["actual"] == MAX_ITEMS + 3, "the diagnostic reports the REAL count"
        assert "split" in exc.value.diagnostics["remedy"]

    def test_refusal_carries_the_reserved_exit_code(self):
        assert PacketOverCap.exit_code == 2

    def test_under_cap_builds(self, tmp_path):
        packet = build_packet(
            _baseline(), _sweep([_hit(1), _hit(2)]), _register(), repo_root=tmp_path
        )

        assert len(packet.items) == 2


class TestD5ExposureNeverCompetesWithHits:
    """Exposure warns through the §3 matrix ONLY — never as an item."""

    def test_ungated_classes_produce_a_matrix_not_items(self, tmp_path):
        register = _register(
            [{"class_id": f"C{i}", "status": "FIXED-BUT-UNGATED"} for i in range(9)]
        )

        packet = build_packet(_baseline(), _sweep([]), register, repo_root=tmp_path)

        assert packet.items == (), "exposure must not mint residual items"
        assert len(packet.sections["3_ungated_exposure"]) == 9
        assert all("changed_surface" in row for row in packet.sections["3_ungated_exposure"])

    def test_many_ungated_classes_cannot_push_a_packet_over_cap(self, tmp_path):
        """The D5 failure mode: warnings crowding hits out of the cap."""
        register = _register(
            [{"class_id": f"C{i}", "status": "FIXED-BUT-UNGATED"} for i in range(40)]
        )

        packet = build_packet(_baseline(), _sweep([_hit(1)]), register, repo_root=tmp_path)

        assert len(packet.items) == 1


class TestAdvisoryHitsAreReportedNotRuled:
    """R1: uncalibrated is advisory — never blocks, never clears."""

    def test_advisory_hit_is_a_sweep_row_but_not_an_item(self, tmp_path):
        sweep = _sweep([_hit(1, "ADV")], rules={"ADV": _ADVISORY})

        packet = build_packet(_baseline(), sweep, _register(), repo_root=tmp_path)

        assert len(packet.sections["2_sweep_hits"]) == 1
        assert packet.items == (), "nothing for the chair to rule on"

    def test_calibrated_hit_defaults_to_blocking(self, tmp_path):
        packet = build_packet(_baseline(), _sweep([_hit(1)]), _register(), repo_root=tmp_path)

        assert packet.items[0].default_disposition == "GATE-FIRST"
        assert packet.blocking == packet.items


class TestSectionsAndDispositions:
    def test_every_item_carries_exactly_one_default(self, tmp_path):
        register = _register([{"class_id": "C7", "status": "OPEN", "calibrated_hits": 2}])

        packet = build_packet(_baseline(), _sweep([_hit(1)]), register, repo_root=tmp_path)

        defaults = packet.sections["7_default_dispositions"]
        assert len(defaults) == len(packet.items)
        assert {d["item_id"] for d in defaults} == {i.item_id for i in packet.items}
        assert all(d["disposition"] in DISPOSITIONS for d in defaults)

    def test_item_ids_are_unique_so_rulings_map_one_to_one(self, tmp_path):
        packet = build_packet(
            _baseline(), _sweep([_hit(1), _hit(2), _hit(3)]), _register(), repo_root=tmp_path
        )

        ids = [i.item_id for i in packet.items]
        assert len(ids) == len(set(ids))

    def test_all_eight_sections_are_present(self, tmp_path):
        packet = build_packet(_baseline(), _sweep([]), _register(), repo_root=tmp_path)

        for section in range(8):
            assert any(k.startswith(f"{section}_") for k in packet.sections), f"missing §{section}"

    def test_null_section_states_absence_explicitly(self, tmp_path):
        packet = build_packet(_baseline(), _sweep([]), _register(), repo_root=tmp_path)

        null = packet.sections["6_null"]
        assert null["no_calibrated_hits"] is True
        assert null["no_new_boundaries"] is True

    def test_packet_hash_is_stable_and_content_bound(self, tmp_path):
        a = build_packet(_baseline(), _sweep([_hit(1)]), _register(), repo_root=tmp_path)
        b = build_packet(_baseline(), _sweep([_hit(1)]), _register(), repo_root=tmp_path)
        c = build_packet(_baseline(), _sweep([_hit(2)]), _register(), repo_root=tmp_path)

        assert a.packet_hash == b.packet_hash, "same input must hash the same"
        assert a.packet_hash != c.packet_hash, "different residual must hash differently"

    def test_no_file_contents_or_diff_hunks_leak_in(self, tmp_path):
        """R4: zero diff hunks, no file contents — the excerpt is capped."""
        long_detail = {"rule_id": "R1", "path": "p.py", "line": 1, "detail": "x" * 5000}

        packet = build_packet(_baseline(), _sweep([long_detail]), _register(), repo_root=tmp_path)

        assert len(packet.sections["2_sweep_hits"][0]["excerpt"]) <= 120
