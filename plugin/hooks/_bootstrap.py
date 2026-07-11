"""Shared cross-platform bootstrap helpers for hook scripts.

Stdlib-only. Hook scripts import this (same-directory import, like
``_sdk_gate``) before doing any I/O:

- :func:`ensure_utf8_stdio` — force UTF-8 (``errors="replace"``) on
  stdout/stderr. On Windows the console default is often cp1252,
  which cannot encode em-dashes/emoji and would crash the hook.
- :func:`read_stdin_utf8` — read the hook payload as UTF-8 bytes
  regardless of locale (``sys.stdin.buffer`` bypasses the
  locale-encoded text wrapper, which is cp1252 on most Windows
  machines).
- :func:`ensure_repo_src_on_path` — make the repo's ``src/``
  importable so hooks can lazily import ``attune.*`` without the
  POSIX-only ``PYTHONPATH=src python …`` env-prefix syntax in the
  hook registration.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 with replacement.

    No-op when the streams are already UTF-8 (macOS/Linux default)
    or do not support ``reconfigure`` (e.g. pytest capture objects).
    """
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if (
            encoding
            and encoding.lower() not in ("utf-8", "utf8")
            and hasattr(stream, "reconfigure")
        ):
            stream.reconfigure(encoding="utf-8", errors="replace")


def read_stdin_utf8(limit: int | None = None) -> str:
    """Read stdin as UTF-8 text, independent of the locale encoding.

    Args:
        limit: Optional byte cap (e.g. 10_000 to bound hook input).

    Returns:
        Decoded payload; undecodable bytes become U+FFFD replacements
        rather than raising, so a hook never crashes on odd input.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is None:  # already detached/wrapped (tests)
        return sys.stdin.read() if limit is None else sys.stdin.read(limit)
    data = buffer.read() if limit is None else buffer.read(limit)
    return data.decode("utf-8", errors="replace")


def ensure_repo_src_on_path() -> None:
    """Insert the repo's ``src/`` directory at the front of ``sys.path``.

    Resolved relative to this file — ``parents[3]`` climbs
    ``scripts/`` → ``hooks/`` → ``attune/`` → ``src/`` — so it works
    from any cwd, any worktree, and any platform without env-prefix
    syntax in the registration.
    """
    try:
        src = Path(__file__).resolve().parents[3]
    except IndexError:
        return
    # Require the real package (__init__.py), not just a directory named
    # "attune" — from the plugin copy, parents[3] lands OUTSIDE the repo,
    # where an unrelated "attune" dir (e.g. a workspace umbrella checkout)
    # would otherwise shadow the installed package as a namespace package.
    if not (src / "attune" / "__init__.py").is_file():  # plugin copy / moved layout — no-op
        return
    src_str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
