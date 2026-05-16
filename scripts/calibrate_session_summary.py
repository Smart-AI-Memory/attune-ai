#!/usr/bin/env python3
"""Calibration harness for the /sessions Haiku summarizer.

Runs ``attune.ops.session_summarizer.summarize_session()`` over every
committed fixture at ``tests/fixtures/ops/session_summaries/*.jsonl``
and emits a per-fixture record of
``{tokens_in, tokens_out, cost_usd, summary, summary_chars}`` to
``tests/fixtures/ops/session_summaries/snapshot.json``. The snapshot
is committed so future Haiku-prompt edits surface as a visible diff
the developer must review (and re-commit) before landing.

**Default mode** — regenerates the snapshot:

    ATTUNE_OPS_SESSIONS_LLM=1 python scripts/calibrate_session_summary.py

Requires ``ANTHROPIC_API_KEY`` in the environment. Uses a fresh
tempdir for the on-disk cache so every fixture incurs a real Haiku
call (no cache hits). Total spend per run: ~$0.02 at $0.001/fixture
× 12 fixtures.

**``--check`` mode** — fails on drift past the configured tolerance.
Compares a fresh run against the committed snapshot and exits 1 if
any fixture drifts more than:

- ``±10%`` on ``tokens_in`` (input is the redacted text, mostly stable)
- ``±50%`` on ``tokens_out`` (Haiku output length varies more)
- ``±20%`` on ``cost_usd`` (per decisions.md Decision 8)
- ``±50%`` on ``summary_chars`` (length-of-summary sanity)

Useful for developers who edit ``session_summarizer.SUMMARY_PROMPT``
and want to verify the prompt change doesn't blow up cost or
output shape before re-committing the snapshot.

**``--dry-run`` mode** — lists what would be summarized + the
fingerprint of the current prompt, without calling Haiku. Free.

The harness intentionally does NOT run inside CI's pytest suite —
that would require ``ANTHROPIC_API_KEY`` in CI secrets and burn
~$0.02 per build. The sibling ``tests/unit/ops/test_calibration_snapshot.py``
provides the CI gate (asserts the committed snapshot is structurally
sound + costs are within plausible ranges).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# scripts/ is not on the import path by default; add src/ relative
# to this file's location (scripts/ sits next to src/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from attune.ops import session_summarizer  # noqa: E402

DEFAULT_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ops" / "session_summaries"
)
DEFAULT_SNAPSHOT = DEFAULT_FIXTURE_DIR / "snapshot.json"

# Drift tolerances for --check mode. Tighter on inputs (deterministic
# given a stable prompt), looser on outputs (Haiku varies). See module
# docstring for rationale.
_TOLERANCE = {
    "tokens_in": 0.10,
    "tokens_out": 0.50,
    "cost_usd": 0.20,
    "summary_chars": 0.50,
}


@dataclass(frozen=True)
class DriftReport:
    """One fixture's drift result."""

    fixture: str
    failures: list[str]

    @property
    def ok(self) -> bool:
        return not self.failures


def _hash_prompt() -> str:
    """SHA-256 of the current SUMMARY_PROMPT — first 12 hex chars.

    Bundled into the snapshot so a prompt-only edit (which is what
    the snapshot is designed to catch) shows up as a visible diff
    in the snapshot JSON, separately from the per-fixture changes.
    """
    h = hashlib.sha256(session_summarizer.SUMMARY_PROMPT.encode("utf-8"))
    return h.hexdigest()[:12]


def _summarize_one(fixture: Path, attune_home: Path) -> dict:
    """Run the summarizer against one fixture; return a snapshot row.

    Returns ``{"error": "..."}`` if the summarizer returns None
    (LLM disabled, redaction failure, etc.) so the snapshot still
    records that the fixture was attempted.
    """
    # Fresh budget per fixture so a hypothetical breach in one
    # doesn't affect the next. Cap is generous ($10) — the budget
    # belongs in production-render code paths, not here.
    budget = session_summarizer.Budget(cap_usd=10.0)
    result = session_summarizer.summarize_session(fixture, attune_home=attune_home, budget=budget)
    if result is None:
        return {"error": "summarize_session returned None"}
    return {
        "source": result.source,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": round(result.cost_usd, 6),
        "summary": result.text,
        "summary_chars": len(result.text),
    }


def _build_snapshot(fixtures: list[Path], attune_home: Path) -> dict:
    """Run the summarizer over every fixture, build the snapshot dict."""
    per_fixture = {f.name: _summarize_one(f, attune_home) for f in sorted(fixtures)}
    succeeded = [v for v in per_fixture.values() if "error" not in v]
    totals = {
        "fixtures": len(per_fixture),
        "succeeded": len(succeeded),
        "tokens_in": sum(v["tokens_in"] for v in succeeded),
        "tokens_out": sum(v["tokens_out"] for v in succeeded),
        "cost_usd": round(sum(v["cost_usd"] for v in succeeded), 6),
    }
    return {
        "model": session_summarizer.HAIKU_MODEL_ID,
        "prompt_hash": _hash_prompt(),
        "totals": totals,
        "fixtures": per_fixture,
    }


def _compute_drift(
    committed: dict,
    fresh: dict,
    *,
    tolerance: dict[str, float] = _TOLERANCE,
) -> list[DriftReport]:
    """Compare two snapshots per-fixture; return per-fixture drift reports.

    A missing fixture in either side counts as a drift failure for
    that fixture so a developer can't silently remove a fixture from
    the calibration set by re-running the calibrator without --check.
    """
    reports: list[DriftReport] = []
    committed_fx = committed.get("fixtures", {})
    fresh_fx = fresh.get("fixtures", {})

    for name in sorted(set(committed_fx) | set(fresh_fx)):
        failures: list[str] = []
        c = committed_fx.get(name)
        f = fresh_fx.get(name)
        if c is None:
            failures.append("fixture present in fresh run but not committed snapshot")
            reports.append(DriftReport(fixture=name, failures=failures))
            continue
        if f is None:
            failures.append("fixture present in committed snapshot but not fresh run")
            reports.append(DriftReport(fixture=name, failures=failures))
            continue
        if "error" in c or "error" in f:
            if c.get("error") != f.get("error"):
                failures.append(
                    f"error status changed: committed={c.get('error')!r}, "
                    f"fresh={f.get('error')!r}"
                )
            reports.append(DriftReport(fixture=name, failures=failures))
            continue
        for field, tol in tolerance.items():
            c_val = float(c.get(field, 0))
            f_val = float(f.get(field, 0))
            if c_val == 0:
                # Avoid div-by-zero. Treat 0→nonzero as a drift.
                if f_val != 0:
                    failures.append(
                        f"{field}: committed=0, fresh={f_val} (any change from zero is a drift)"
                    )
                continue
            ratio = abs(f_val - c_val) / c_val
            if ratio > tol:
                failures.append(
                    f"{field}: committed={c_val}, fresh={f_val}, "
                    f"drift={ratio:.1%} (tolerance ±{tol:.0%})"
                )
        reports.append(DriftReport(fixture=name, failures=failures))
    return reports


def _format_drift_summary(reports: list[DriftReport]) -> str:
    """Human-readable drift summary for --check mode output."""
    failing = [r for r in reports if not r.ok]
    if not failing:
        return "OK — snapshot matches within tolerance."
    lines = [f"DRIFT — {len(failing)} of {len(reports)} fixtures failed:"]
    for r in failing:
        lines.append(f"  {r.fixture}:")
        for failure in r.failures:
            lines.append(f"    - {failure}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calibration harness for the /sessions Haiku summarizer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Regenerate snapshot (requires ANTHROPIC_API_KEY)\n"
            "  python scripts/calibrate_session_summary.py\n\n"
            "  # Check fresh run against committed snapshot — fail on drift\n"
            "  python scripts/calibrate_session_summary.py --check\n\n"
            "  # Dry-run — show prompt fingerprint, no API calls\n"
            "  python scripts/calibrate_session_summary.py --dry-run\n"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare fresh run to committed snapshot; exit 1 on drift.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt fingerprint + fixture list; no Haiku calls.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURE_DIR,
        help=f"Fixture directory (default: {DEFAULT_FIXTURE_DIR})",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help=f"Snapshot file (default: {DEFAULT_SNAPSHOT})",
    )
    parser.add_argument(
        "--attune-home",
        type=Path,
        default=None,
        help="Cache dir (default: fresh tempdir each run so every call is real).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.fixtures.is_dir():
        print(f"ERROR: fixture dir not found: {args.fixtures}", file=sys.stderr)
        return 1
    fixtures = sorted(args.fixtures.glob("*.jsonl"))
    if not fixtures:
        print(f"ERROR: no *.jsonl fixtures in {args.fixtures}", file=sys.stderr)
        return 1

    prompt_hash = _hash_prompt()
    print(f"Model:         {session_summarizer.HAIKU_MODEL_ID}")
    print(f"Prompt hash:   {prompt_hash}")
    print(f"Fixtures:      {len(fixtures)} from {args.fixtures}")
    print(f"Snapshot:      {args.snapshot}")
    print()

    if args.dry_run:
        for f in fixtures:
            print(f"  {f.name}")
        print()
        print("Dry-run — no Haiku calls made.")
        return 0

    # Live runs need the LLM gate flipped + a key in the env. The
    # summarizer's own llm_enabled() check would otherwise return
    # None on every fixture and the snapshot would be all errors.
    if not session_summarizer.llm_enabled():
        print(
            "ERROR: Haiku path disabled. Need ANTHROPIC_API_KEY in env "
            "AND ATTUNE_OPS_SESSIONS_LLM not set to '0'.",
            file=sys.stderr,
        )
        return 1

    # Fresh tempdir for the cache means every fixture incurs a real
    # call (no cache hits from a prior run). Override via --attune-home
    # if you want to inspect the cache files afterward.
    cleanup_tempdir = False
    if args.attune_home is None:
        attune_home = Path(tempfile.mkdtemp(prefix="attune-calib-"))
        cleanup_tempdir = True
    else:
        attune_home = args.attune_home
        attune_home.mkdir(parents=True, exist_ok=True)

    try:
        fresh = _build_snapshot(fixtures, attune_home)
    finally:
        if cleanup_tempdir:
            # Best-effort cleanup. Tempdir contents are just cached
            # summary JSONs — small, won't accumulate.
            import shutil

            shutil.rmtree(attune_home, ignore_errors=True)

    print(f"Fresh totals:  {fresh['totals']}")
    print()

    if args.check:
        if not args.snapshot.is_file():
            print(
                f"ERROR: no snapshot at {args.snapshot} to check against. "
                "Run without --check to generate one.",
                file=sys.stderr,
            )
            return 1
        committed = json.loads(args.snapshot.read_text(encoding="utf-8"))
        drift_reports = _compute_drift(committed, fresh)
        print(_format_drift_summary(drift_reports))
        failing = [r for r in drift_reports if not r.ok]
        return 1 if failing else 0

    # Default mode: write the snapshot.
    args.snapshot.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(fresh, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    args.snapshot.write_text(payload, encoding="utf-8")
    print(f"Snapshot written to {args.snapshot}")
    print(f"Total cost:    ${fresh['totals']['cost_usd']:.6f}")
    print()
    print("Review the diff and commit when satisfied:")
    print(
        f"  git diff {args.snapshot.relative_to(Path.cwd()) if args.snapshot.is_absolute() else args.snapshot}"
    )
    return 0


if __name__ == "__main__":
    # Don't propagate ATTUNE_OPS_SESSIONS_LLM=0 from a parent shell
    # that may have disabled it. Caller can still override via env if
    # they really want the script to no-op (see --dry-run instead).
    if (
        os.environ.get("ATTUNE_OPS_SESSIONS_LLM") == "0"
        and "--dry-run" not in sys.argv
        and "--check" not in sys.argv
    ):
        print(
            "WARNING: ATTUNE_OPS_SESSIONS_LLM=0 is set. The summarizer "
            "will return None for every fixture and the snapshot will "
            "contain only errors. Unset the env var or use --dry-run.",
            file=sys.stderr,
        )
    raise SystemExit(main())
