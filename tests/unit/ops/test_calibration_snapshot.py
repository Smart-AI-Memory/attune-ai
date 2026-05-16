"""Snapshot regression CI gate for the /sessions Haiku calibration.

Companion to ``scripts/calibrate_session_summary.py``. The script
runs Haiku over every committed fixture and emits a JSON snapshot
at ``tests/fixtures/ops/session_summaries/snapshot.json``. THIS
test asserts the committed snapshot is structurally sound — same
fixture set the redaction snapshot covers, plausible per-fixture
cost/length, totals within the spec'd budget cap.

What this test does NOT do:

- It does **not** make real Haiku calls. CI has no
  ``ANTHROPIC_API_KEY`` and burning ~$0.02 per build would be a
  poor trade for the structural verification we get here for free.
- It does **not** assert summary CONTENT equality. Haiku output is
  non-deterministic; comparing text would noise-fail every run.

The actual regression signal for prompt edits comes from the
``--check`` mode of the calibrator script. A developer changing
``session_summarizer.SUMMARY_PROMPT`` is expected to:

1. Re-run ``python scripts/calibrate_session_summary.py``
2. Inspect the snapshot diff (cost, length, summary samples)
3. If satisfied, ``git add`` the updated snapshot

This test catches the OTHER failure modes — a developer removed a
fixture, edited the snapshot by hand, or the snapshot diverged
from the fixture set on disk.

Skipped (not failed) when the snapshot file is absent so a fresh
clone of the repo without the snapshot doesn't break CI before
Patrick's first calibration run lands the file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_FIXTURE_DIR = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "ops" / "session_summaries"
)
_SNAPSHOT_PATH = _FIXTURE_DIR / "snapshot.json"

# Plausible per-fixture cost band. Hard lower bound at $0.0001 catches
# accidentally-zeroed entries (would indicate a snapshot generated with
# the LLM disabled — only error rows). Upper bound at $0.05 matches
# the per-page-load budget cap; any single fixture above it means the
# input slice or output cap leaked something unreasonable.
_PER_FIXTURE_COST_BAND = (1e-4, 0.05)

# Plausible summary length in characters. Lower bound rules out empty
# or "Resume:" placeholder output. Upper bound catches a prompt that
# silently dropped the "be terse" instruction and lets Haiku ramble.
_SUMMARY_CHARS_BAND = (20, 2000)

# Plausible total spend across the fixture set. With 12 fixtures and
# ~$0.001 typical, $0.10 leaves 8× headroom for output variance + the
# occasional longer session.
_TOTAL_COST_CAP = 0.10


def _snapshot_or_skip() -> dict:
    if not _SNAPSHOT_PATH.is_file():
        pytest.skip(
            f"calibration snapshot absent at {_SNAPSHOT_PATH}; "
            "run scripts/calibrate_session_summary.py to generate"
        )
    return json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _fixture_names() -> set[str]:
    if not _FIXTURE_DIR.is_dir():
        return set()
    return {p.name for p in _FIXTURE_DIR.glob("*.jsonl")}


# ---------------------------------------------------------------------------
# Top-level shape
# ---------------------------------------------------------------------------


def test_snapshot_has_required_top_level_fields():
    """Snapshot must carry model id, prompt hash, totals, per-fixture rows."""
    snap = _snapshot_or_skip()
    assert set(snap.keys()) >= {"model", "prompt_hash", "totals", "fixtures"}
    assert isinstance(snap["model"], str) and snap["model"]
    assert isinstance(snap["prompt_hash"], str) and len(snap["prompt_hash"]) == 12
    assert isinstance(snap["totals"], dict)
    assert isinstance(snap["fixtures"], dict)


def test_snapshot_model_is_haiku_4_5():
    """Snapshot must come from claude-haiku-4-5; a different model means
    the cost math + token assumptions are off and the snapshot needs a
    regen."""
    snap = _snapshot_or_skip()
    assert snap["model"].startswith("claude-haiku-4-5"), (
        f"snapshot was built with {snap['model']!r}; expected a "
        "claude-haiku-4-5 variant. Re-run scripts/calibrate_session_summary.py."
    )


# ---------------------------------------------------------------------------
# Per-fixture invariants
# ---------------------------------------------------------------------------


def test_snapshot_fixtures_match_fixture_dir():
    """Snapshot must have exactly one entry per *.jsonl in the fixture dir.

    A developer who removed a fixture and forgot to re-run the
    calibrator gets a clear failure here. Same for the reverse —
    adding a fixture without re-running the calibrator.
    """
    snap = _snapshot_or_skip()
    snapshot_names = set(snap["fixtures"].keys())
    on_disk = _fixture_names()
    missing_in_snapshot = on_disk - snapshot_names
    extra_in_snapshot = snapshot_names - on_disk
    assert not missing_in_snapshot, (
        f"fixtures on disk but not in snapshot: {sorted(missing_in_snapshot)}; "
        "re-run scripts/calibrate_session_summary.py"
    )
    assert not extra_in_snapshot, (
        f"fixtures in snapshot but not on disk: {sorted(extra_in_snapshot)}; "
        "re-run scripts/calibrate_session_summary.py (the snapshot is stale)"
    )


def test_snapshot_records_have_required_fields():
    """Every per-fixture row must carry the calibration metrics.

    Error rows ({\"error\": \"...\"}) are tolerated here — a fixture
    that legitimately failed to summarize records the failure rather
    than vanishing. Per-row drift assertions live in the script's
    --check mode, not this CI gate.
    """
    snap = _snapshot_or_skip()
    for name, row in snap["fixtures"].items():
        assert isinstance(row, dict), f"{name}: row must be a dict"
        if "error" in row:
            continue
        required = {"source", "tokens_in", "tokens_out", "cost_usd", "summary", "summary_chars"}
        missing = required - set(row.keys())
        assert not missing, f"{name}: missing required fields {sorted(missing)}"


def test_snapshot_costs_within_per_fixture_band():
    """Per-fixture cost stays inside the plausible band.

    Catches snapshots accidentally generated with LLM disabled
    (every row would have cost_usd=0) or with a runaway prompt
    that blew out the per-call cost.
    """
    snap = _snapshot_or_skip()
    low, high = _PER_FIXTURE_COST_BAND
    for name, row in snap["fixtures"].items():
        if "error" in row:
            continue
        cost = float(row["cost_usd"])
        assert low <= cost <= high, (
            f"{name}: cost ${cost:.6f} outside plausible band "
            f"${low:.4f}-${high:.4f}. Re-run scripts/calibrate_session_summary.py."
        )


def test_snapshot_summary_chars_within_band():
    """Per-fixture summary length stays inside the plausible band."""
    snap = _snapshot_or_skip()
    low, high = _SUMMARY_CHARS_BAND
    for name, row in snap["fixtures"].items():
        if "error" in row:
            continue
        chars = int(row["summary_chars"])
        assert low <= chars <= high, (
            f"{name}: summary_chars={chars} outside plausible band "
            f"{low}-{high}. Either the prompt dropped its "
            "terseness instruction or Haiku returned an empty/stub response."
        )


def test_snapshot_source_is_haiku_not_cached():
    """Calibration runs use a fresh tempdir cache; every row should be
    source=haiku. A row with source=cached means the calibrator ran
    against a non-tempdir cache and didn't measure fresh model output."""
    snap = _snapshot_or_skip()
    for name, row in snap["fixtures"].items():
        if "error" in row:
            continue
        assert row["source"] == "haiku", (
            f"{name}: source={row['source']!r}; calibration must use a fresh "
            "cache so every fixture incurs a real Haiku call. "
            "Drop the cache dir or omit --attune-home from the calibrator call."
        )


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------


def test_snapshot_total_cost_below_cap():
    """Total spend across the fixture set must stay below the global cap.

    With 12 fixtures and ~$0.001 typical, $0.10 (~8× headroom) is a
    soft ceiling. A snapshot above this means either: (a) a prompt
    edit made Haiku much chattier, or (b) the fixture set grew
    without re-tuning the cap.
    """
    snap = _snapshot_or_skip()
    total = float(snap["totals"]["cost_usd"])
    assert total <= _TOTAL_COST_CAP, (
        f"total snapshot cost ${total:.4f} exceeds soft cap "
        f"${_TOTAL_COST_CAP:.4f}. Inspect the snapshot diff for a "
        "Haiku-output explosion or re-tune the cap if the fixture "
        "set legitimately grew."
    )


def test_snapshot_totals_match_per_fixture_sums():
    """``totals.cost_usd`` must equal the sum of per-fixture costs.

    Drift here means the snapshot was hand-edited rather than
    regenerated via the script — the totals were left stale.
    """
    snap = _snapshot_or_skip()
    summed = sum(float(row["cost_usd"]) for row in snap["fixtures"].values() if "error" not in row)
    total = float(snap["totals"]["cost_usd"])
    # Allow tiny rounding noise from the script's per-fixture round().
    assert abs(total - summed) < 0.01, (
        f"totals.cost_usd={total:.6f} but per-fixture sum is "
        f"{summed:.6f}. Snapshot was likely hand-edited; re-run the "
        "calibrator to regenerate."
    )


def test_snapshot_totals_count_matches_fixture_dir():
    """``totals.fixtures`` must equal the number of *.jsonl files on disk."""
    snap = _snapshot_or_skip()
    on_disk = len(_fixture_names())
    assert snap["totals"]["fixtures"] == on_disk, (
        f"totals.fixtures={snap['totals']['fixtures']} but on-disk count is "
        f"{on_disk}; snapshot is stale relative to the fixture dir"
    )


# ---------------------------------------------------------------------------
# Prompt-hash consistency
# ---------------------------------------------------------------------------


def test_snapshot_prompt_hash_matches_current_prompt():
    """``prompt_hash`` must match the SHA-256[:12] of the current
    ``session_summarizer.SUMMARY_PROMPT``.

    A mismatch means the prompt has been edited since the snapshot
    was generated. The developer must re-run the calibrator to
    update the snapshot before the change can land.
    """
    snap = _snapshot_or_skip()
    import hashlib

    from attune.ops import session_summarizer

    expected = hashlib.sha256(session_summarizer.SUMMARY_PROMPT.encode("utf-8")).hexdigest()[:12]
    assert snap["prompt_hash"] == expected, (
        f"snapshot prompt_hash={snap['prompt_hash']!r} but current "
        f"SUMMARY_PROMPT hashes to {expected!r}. The prompt has been "
        "edited since the snapshot was generated — re-run "
        "scripts/calibrate_session_summary.py and commit the new snapshot."
    )
