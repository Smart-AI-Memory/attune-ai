#!/usr/bin/env python3
"""Build redacted Claude Code session fixtures for calibration / regression.

Walks ``~/.claude/projects/<encoded-project>*`` and produces a
small set of fixture JSONL files at
``tests/fixtures/ops/session_summaries/``. Each fixture is a real
session run through :func:`attune.ops.session_redaction.redact` —
no sensitive content lands in git.

**Patrick's interactive step.** This script writes candidate
fixtures to the fixtures dir but does NOT commit them. Review
each file by hand before staging. The intent (per the
ops-sessions-page spec, decisions.md Decision 8):

- ~10 representative sessions: short, long, multi-thread,
  abandoned-mid-conversation.
- Each fixture is the redacted form of a real session JSONL.
- A snapshot test will compare Haiku output against these to
  catch prompt drift in CI — ships in a follow-up PR after
  fixtures are curated.

Usage::

    # Default: attune-ai under your CLAUDE.md project root.
    python scripts/build_session_fixtures.py

    # Custom project root (any project with Claude Code history):
    python scripts/build_session_fixtures.py --project-root ~/other

    # Larger sample (default: 12 candidates → curate down to ~10):
    python scripts/build_session_fixtures.py --sample 20

    # Different output dir:
    python scripts/build_session_fixtures.py --out path/to/fixtures

The script picks the N most-recently-active sessions across all
matching encoded keys; you trim from there based on the
representativeness rubric above.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from a checkout without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from attune.ops import data, session_redaction  # noqa: E402


def _redact_jsonl(src: Path, dst: Path) -> tuple[int, dict[str, int]]:
    """Read ``src`` JSONL, redact each event's ``content``, write to ``dst``.

    Returns ``(event_count, aggregate_counts)`` for the per-file
    report. Aggregate counts sum per-category histogram across all
    events in the file.
    """
    aggregate: dict[str, int] = {}
    events_written = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open(encoding="utf-8") as r, dst.open("w", encoding="utf-8") as w:
        for raw in r:
            line = raw.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            content = event.get("content")
            if isinstance(content, str) and content:
                result = session_redaction.redact(content)
                event["content"] = result.text
                for k, v in result.counts.items():
                    aggregate[k] = aggregate.get(k, 0) + v
            w.write(json.dumps(event, ensure_ascii=False) + "\n")
            events_written += 1
    return events_written, aggregate


def _pick_candidates(project_root: Path, sample: int) -> list[Path]:
    """Find the N most-recently-active JSONLs across all encoded keys.

    Sorts by mtime descending. Returns paths, not Session records —
    the build script operates on raw files.
    """
    candidates: list[tuple[float, Path]] = []
    for sessions_dir in data.enumerate_project_encoded_keys(project_root):
        try:
            for jsonl in sessions_dir.glob("*.jsonl"):
                try:
                    mt = jsonl.stat().st_mtime
                except OSError:
                    continue
                candidates.append((mt, jsonl))
        except OSError:
            continue
    candidates.sort(reverse=True)
    return [p for _mt, p in candidates[:sample]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(os.environ.get("ATTUNE_FIXTURE_PROJECT", _REPO_ROOT)),
        help=(
            "Logical project root whose Claude Code sessions to harvest. "
            "Defaults to the repo containing this script."
        ),
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=12,
        help=(
            "Number of candidate sessions to harvest (default: 12). "
            "You curate down to ~10 representative ones before committing."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / "tests" / "fixtures" / "ops" / "session_summaries",
        help="Output directory for redacted fixture JSONLs.",
    )
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    out_dir = args.out.expanduser().resolve()

    candidates = _pick_candidates(project_root, args.sample)
    if not candidates:
        print(
            f"No sessions found under any encoded key for {project_root}. "
            "Check that ~/.claude/projects/ has matching dirs.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Harvesting {len(candidates)} fixture candidates from {project_root}"
        f"\n  → output: {out_dir}\n"
    )

    total_redactions: dict[str, int] = {}
    for src in candidates:
        dst = out_dir / src.name
        events, counts = _redact_jsonl(src, dst)
        mtime = datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc)
        per_file_counts = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "0"
        print(
            f"  {src.name}\n"
            f"    mtime  : {mtime.isoformat()}\n"
            f"    events : {events}\n"
            f"    redacts: {per_file_counts}\n"
            f"    wrote  : {dst}\n"
        )
        for k, v in counts.items():
            total_redactions[k] = total_redactions.get(k, 0) + v

    print(
        "Aggregate redactions across all candidates: "
        + (", ".join(f"{k}={v}" for k, v in sorted(total_redactions.items())) or "0")
    )
    print(
        "\nNext steps:\n"
        f"  1. Review each fixture in {out_dir}\n"
        "  2. Delete any that don't add representational variety\n"
        "  3. Spot-check that redactions look clean (no leaked keys/paths)\n"
        "  4. Stage the final set with: git add tests/fixtures/ops/session_summaries/\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
