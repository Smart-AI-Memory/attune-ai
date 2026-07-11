#!/usr/bin/env python
"""CLI wrapper for the ``/handoff`` slash command.

Generates a resume prompt from the current cwd's git state plus
the most-recent in-flight spec, prints it to stdout, and appends
it to ``~/.attune/last-handoff.md`` so users can recover the
prompt later.

Behavior matches the Stop-hook auto-warning's resume body —
single source of truth via ``_resume_prompt.build_resume_prompt``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path

# Force utf-8 on stdout and stderr. On Windows the default cp1252
# encoding can't emit emoji/em-dash and would crash this hook (caught
# by the outer try/except → silent breakage). errors='replace'
# substitutes '?' for any stray non-encodable byte.
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _resume_prompt import build_resume_prompt  # noqa: E402
from _state import discover_specs, git_state, workspace_roots  # noqa: E402

_LAST_HANDOFF_FILE = Path.home() / ".attune" / "last-handoff.md"


def _resolve_last_handoff_path() -> Path:
    override = os.environ.get("ATTUNE_AI_LAST_HANDOFF_FILE")
    if override:
        return Path(override)
    return _LAST_HANDOFF_FILE


def _append_to_history(body: str) -> None:
    """Append the prompt to the history file with a timestamp separator."""
    target = _resolve_last_handoff_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        header = f"\n--- handoff at {ts} ---\n\n"
        with target.open("a", encoding="utf-8") as fh:
            fh.write(header)
            fh.write(body)
            if not body.endswith("\n"):
                fh.write("\n")
    except OSError:
        # Don't fail the command just because the recovery file
        # couldn't be written — the user still gets the prompt
        # on stdout.
        return


def main() -> int:
    cwd = Path.cwd()
    roots = workspace_roots(cwd=cwd)
    specs = discover_specs(roots)
    spec = specs[0] if specs else None
    git = git_state(cwd)
    body = build_resume_prompt(spec, git)
    _append_to_history(body)
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
