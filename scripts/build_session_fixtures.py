#!/usr/bin/env python3
"""Build redacted session-summary calibration fixtures from real JSONLs.

Walks ``~/.claude/projects/<encoded>*`` for the chosen project,
applies :func:`attune.ops.session_redaction.redact` to every event
that carries a ``content`` field, and writes the redacted JSONL to
the calibration fixture directory.

**Dry-run by default.** Pass ``--write`` to persist. The redacted
content is committed to git per decisions.md Decision 8
("fixture-redaction discipline"); the original sensitive content
NEVER lands in git. Patrick reviews each fixture interactively
before committing.

Usage::

    # Dry-run: print stats per JSONL, no writes
    python scripts/build_session_fixtures.py

    # Write redacted JSONLs to the default fixtures dir
    python scripts/build_session_fixtures.py --write

    # Limit to N sessions (newest first)
    python scripts/build_session_fixtures.py --limit 10 --write

    # Override the source project root
    python scripts/build_session_fixtures.py --project-root /path/to/project

    # Override output dir
    python scripts/build_session_fixtures.py --out-dir tests/fixtures/foo --write

The script is intentionally minimal: no LLM calls, no calibration
runner, no snapshot computation. Those live in the (eventual)
``scripts/calibrate_session_summary.py`` follow-up — see
decisions.md Decision 8.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

from attune.ops import session_redaction
from attune.ops.data import enumerate_project_encoded_keys

DEFAULT_OUT_DIR = Path("tests/fixtures/ops/session_summaries")


def _enumerate_jsonls(project_root: Path) -> list[Path]:
    """Return every ``*.jsonl`` under the project's encoded keys,
    newest-mtime first.

    Reuses :func:`enumerate_project_encoded_keys` so the script
    sees the same multi-key reality the dashboard does (canonical
    key + per-worktree keys).
    """
    encoded_dirs = enumerate_project_encoded_keys(project_root)
    out: list[tuple[float, Path]] = []
    for sessions_dir in encoded_dirs:
        try:
            for jsonl in sessions_dir.glob("*.jsonl"):
                try:
                    out.append((jsonl.stat().st_mtime, jsonl))
                except OSError:
                    continue
        except OSError:
            continue
    out.sort(reverse=True)
    return [p for _mtime, p in out]


def _redact_jsonl(source: Path) -> tuple[list[str], dict[str, int]]:
    """Return ``(redacted_lines, counts)`` for one JSONL file.

    Per-event redaction: only the ``content`` string is rewritten;
    timestamps, types, and other metadata pass through unchanged.
    Counts aggregate across all events in the file.

    Lines that aren't JSON or aren't dicts are emitted verbatim —
    they have no addressable ``content`` field to redact and the
    summarizer would skip them anyway.
    """
    redacted_lines: list[str] = []
    total_counts: dict[str, int] = {}
    try:
        with source.open(encoding="utf-8") as fh:
            for raw in fh:
                line = raw.rstrip("\n")
                if not line.strip():
                    redacted_lines.append(line)
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    redacted_lines.append(line)
                    continue
                if not isinstance(event, dict):
                    redacted_lines.append(line)
                    continue
                content = event.get("content")
                if isinstance(content, str) and content:
                    result = session_redaction.redact(content)
                    event["content"] = result.text
                    for k, v in result.counts.items():
                        total_counts[k] = total_counts.get(k, 0) + v
                redacted_lines.append(json.dumps(event, ensure_ascii=False))
    except OSError as exc:
        print(f"  ERROR reading {source}: {exc}", file=sys.stderr)
        return [], {}
    return redacted_lines, total_counts


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "(no redactions)"
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


def build_fixtures(
    project_root: Path,
    out_dir: Path,
    *,
    write: bool,
    limit: int | None,
) -> int:
    """Walk JSONLs and emit redacted fixtures. Returns the count processed.

    When ``write=False`` (default), only prints per-file redaction
    counts. When ``write=True``, persists each redacted file as
    ``<out_dir>/<session-id>.jsonl``. The output dir is created on
    demand.
    """
    paths = _enumerate_jsonls(project_root)
    if not paths:
        print(f"No JSONLs found under encoded keys for {project_root}", file=sys.stderr)
        return 0
    if limit is not None:
        paths = paths[:limit]

    print(f"Source: {project_root}")
    print(f"Found {len(paths)} JSONL(s) across encoded keys.")
    if not write:
        print("(Dry-run — pass --write to persist.)")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Writing redacted fixtures to: {out_dir}")
    print()

    processed = 0
    for path in paths:
        lines, counts = _redact_jsonl(path)
        if not lines:
            continue
        session_id = path.stem
        print(f"  {session_id}  [{_format_counts(counts)}]")
        if write:
            target = out_dir / f"{session_id}.jsonl"
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        processed += 1

    print()
    if write:
        print(f"Wrote {processed} fixture(s). Review each before committing.")
    else:
        print(f"Would write {processed} fixture(s) — re-run with --write.")
    return processed


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build redacted session-summary calibration fixtures."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root whose encoded session keys to walk (default: cwd).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for fixtures (default: {DEFAULT_OUT_DIR}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of sessions processed (newest first).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually write the fixtures (default is dry-run).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    count = build_fixtures(
        args.project_root.expanduser().resolve(),
        args.out_dir,
        write=args.write,
        limit=args.limit,
    )
    return 0 if count >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
