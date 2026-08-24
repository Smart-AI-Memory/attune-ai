"""Bounded command runner — a portable `timeout(1)` for macOS.

macOS ships no `timeout` binary (GNU coreutils), so ad-hoc bounded
runs during diagnosis either hang forever or grow bespoke kill logic
(retro 2026-08-24 item 7: a hung diagnostic cost dead time twice).

Usage::

    python scripts/with_timeout.py 30 -- cmd arg1 arg2

Exit codes follow GNU timeout's convention: the command's own exit
code when it finishes in time, 124 on timeout, 125 for usage errors.
The whole process group is killed on timeout so children die too.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys

TIMEOUT_EXIT = 124
USAGE_EXIT = 125


def main(argv: list[str]) -> int:
    """Run ``argv`` as ``<seconds> -- <cmd...>`` with a hard bound."""
    if len(argv) < 3 or argv[1] != "--":
        print(
            "usage: with_timeout.py <seconds> -- <command> [args...]",
            file=sys.stderr,
        )
        return USAGE_EXIT
    try:
        seconds = float(argv[0])
    except ValueError:
        print(f"invalid seconds value: {argv[0]!r}", file=sys.stderr)
        return USAGE_EXIT
    if seconds <= 0:
        print("seconds must be positive", file=sys.stderr)
        return USAGE_EXIT

    cmd = argv[2:]
    # POSIX: new session so a timeout kills children too (a bare
    # proc.kill() strands grandchildren, which is the original hang).
    # Windows has no killpg; taskkill /T below kills the tree instead.
    posix = os.name == "posix"
    proc = subprocess.Popen(cmd, start_new_session=posix)  # noqa: S603
    try:
        return proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        if posix:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
        else:
            subprocess.run(  # noqa: S603
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
            )
            proc.kill()  # idempotent backstop if taskkill missed it
        proc.wait()
        print(
            f"with_timeout: command exceeded {seconds:g}s and was killed",
            file=sys.stderr,
        )
        return TIMEOUT_EXIT


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
