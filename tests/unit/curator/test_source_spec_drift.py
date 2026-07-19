"""Spec-drift source reader tests (spec-lifecycle-gates RR-6/T6).

Real fixture spec dirs on disk — the reader's file-to-summary
boundary runs unmocked, mirroring the sibling source tests.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from attune.curator.sources import spec_drift


def _spec(root: Path, slug: str, status: str, *, age_days: float = 0.0) -> Path:
    d = root / "docs" / "specs" / slug
    d.mkdir(parents=True)
    f = d / "requirements.md"
    f.write_text(f"# {slug}\n\n**Status: {status}**\n", encoding="utf-8")
    if age_days:
        stamp = time.time() - age_days * 86_400
        os.utime(f, (stamp, stamp))
    return d


class TestSpecDriftReader:
    def test_stale_spec_surfaces_as_candidate(self, tmp_path):
        _spec(tmp_path, "rotting-spec", "in progress", age_days=90)
        summary = spec_drift.read(project_root=tmp_path)
        (item,) = summary.items
        assert item.item_id == "spec-drift:rotting-spec"
        assert "stale" in item.title
        assert item.link == "docs/specs/rotting-spec/"

    def test_active_and_complete_specs_do_not_surface(self, tmp_path):
        _spec(tmp_path, "fresh-spec", "in progress")
        _spec(tmp_path, "done-spec", "complete")
        summary = spec_drift.read(project_root=tmp_path)
        assert summary.items == []

    def test_empty_result_has_stable_hash_and_never_raises(self, tmp_path):
        first = spec_drift.read(project_root=tmp_path)  # no docs/specs at all
        second = spec_drift.read(project_root=tmp_path)
        assert first.items == []
        assert first.state_hash == second.state_hash

    def test_candidate_reaches_curator_registry(self):
        """RR-5-style proof: the reader is enumerated by the curator."""
        from attune.curator import core

        assert spec_drift in core._SOURCE_MODULES
