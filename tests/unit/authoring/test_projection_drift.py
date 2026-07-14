"""Projection drift gate — masters and projected outputs in lockstep.

Single-sourced (``status: manual``) features are exempt from the
LLM-freshness staleness check by design, which left master→projection
drift unguarded: PR #1059 edited ``models.md`` / ``spec-engine.md``
masters and their committed templates carried a stale ``source_hash``
for three weeks, caught only by an unrelated full projection run.

This suite is the enforcer for that class:

- the **corpus gate** re-renders every real master in memory and
  fails when any committed output differs (ignoring ``generated_at``
  stamps) — the fix is always
  ``python scripts/project_features.py <feature>`` in the same PR;
- the **tripwire tests** prove the gate actually fires on a mutated
  master and on a deleted output (verify-it-fires, not just
  verify-it-passes);
- the **idempotence tests** pin the no-churn write path: re-running
  projection over an unchanged master rewrites nothing.
"""

from __future__ import annotations

from pathlib import Path

from attune.authoring.projector import (
    check_projection_drift,
    normalize_generated_stamps,
    project_feature,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MASTERS_DIR = REPO_ROOT / "content" / "features"


# --- the corpus gate ---------------------------------------------------------


def test_projected_outputs_match_their_masters():
    # The drift gate proper: every committed projection output must
    # match a fresh render of its master. A failure here means a
    # master (or the projector) changed without re-projection — run
    # `python scripts/project_features.py <feature>` (and
    # `python scripts/sync_help_bundle.py`) in the same PR.
    assert MASTERS_DIR.is_dir(), f"masters dir missing: {MASTERS_DIR}"
    findings = check_projection_drift(REPO_ROOT, REPO_ROOT / ".help")
    assert findings == [], "projection drift detected:\n" + "\n".join(findings)


# --- tripwires: the gate must FIRE, not just pass ---------------------------


def _seed_project(tmp_path: Path) -> Path:
    """A minimal project with one master, fully projected to disk."""
    masters = tmp_path / "content" / "features"
    masters.mkdir(parents=True)
    (masters / "feat.md").write_text(
        "---\n"
        "feature: feat\n"
        "summary: A feature\n"
        "---\n\n"
        "## Overview\n\nthe overview\n\n"
        "## Concepts\n\nthe concepts\n\n"
        "## Notes & tips\n\nthe notes\n",
        encoding="utf-8",
    )
    project_feature(masters / "feat.md", tmp_path, tmp_path / ".help", dry_run=False)
    return masters / "feat.md"


def test_gate_clean_after_projection(tmp_path):
    _seed_project(tmp_path)
    assert check_projection_drift(tmp_path, tmp_path / ".help") == []


def test_gate_fires_on_master_edit(tmp_path):
    master = _seed_project(tmp_path)
    master.write_text(
        master.read_text(encoding="utf-8").replace("the overview", "the EDITED overview"),
        encoding="utf-8",
    )

    findings = check_projection_drift(tmp_path, tmp_path / ".help")

    assert findings, "gate must fire when a master changes without re-projection"
    assert any("differs from its master" in f for f in findings)
    assert all("feat:" in f for f in findings)


def test_gate_fires_on_missing_output(tmp_path):
    _seed_project(tmp_path)
    (tmp_path / ".help" / "templates" / "feat" / "concept.md").unlink()

    findings = check_projection_drift(tmp_path, tmp_path / ".help")

    assert any("missing" in f for f in findings)


def test_gate_ignores_timestamp_only_difference(tmp_path):
    # A re-render whose only difference is generated_at is NOT drift.
    _seed_project(tmp_path)
    concept = tmp_path / ".help" / "templates" / "feat" / "concept.md"
    stamped = concept.read_text(encoding="utf-8")
    concept.write_text(
        stamped.replace(
            stamped.splitlines()[5],  # the generated_at: line
            "generated_at: 1999-01-01T00:00:00+00:00",
        ),
        encoding="utf-8",
    )

    assert check_projection_drift(tmp_path, tmp_path / ".help") == []


# --- idempotent writes -------------------------------------------------------


def test_reprojection_of_unchanged_master_writes_nothing(tmp_path):
    master = _seed_project(tmp_path)

    second = project_feature(master, tmp_path, tmp_path / ".help", dry_run=False)

    assert second.written == []
    assert sorted(second.unchanged) == sorted(o.path for o in second.outputs)


def test_reprojection_preserves_original_timestamp(tmp_path):
    master = _seed_project(tmp_path)
    concept = tmp_path / ".help" / "templates" / "feat" / "concept.md"
    before = concept.read_text(encoding="utf-8")

    project_feature(master, tmp_path, tmp_path / ".help", dry_run=False)

    assert concept.read_text(encoding="utf-8") == before


def test_reprojection_after_master_edit_rewrites(tmp_path):
    master = _seed_project(tmp_path)
    master.write_text(
        master.read_text(encoding="utf-8").replace("the overview", "the EDITED overview"),
        encoding="utf-8",
    )

    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=False)

    assert result.written  # content change -> real rewrite
    assert check_projection_drift(tmp_path, tmp_path / ".help") == []


# --- normalizer --------------------------------------------------------------


def test_normalize_covers_frontmatter_and_footer_stamps():
    fm = "generated_at: 2026-07-14T00:00:00+00:00\nbody\n"
    footer = "<!-- attune-generated: source_hash=abc feature=f kind=k generated_at=2026-07-14 -->"
    assert "2026-07-14" not in normalize_generated_stamps(fm)
    assert "2026-07-14" not in normalize_generated_stamps(footer)
    # Everything else is untouched.
    assert "source_hash=abc" in normalize_generated_stamps(footer)
