#!/usr/bin/env python3
"""PreToolUse(Bash) guard: `timeout` does not exist on macOS.

`timeout(1)` is GNU coreutils. macOS ships neither it nor `gtimeout`
unless coreutils is installed, so a Bash command that opens with
`timeout ...` fails with `command not found: timeout` and the work
inside it never runs — while the shell still reports the exit status of
whatever came next, so the failure is easy to miss.

Origin: measured, not guessed (2026-08-25 calibration). A full-text
sweep of session transcripts found `command not found: timeout` in AT
LEAST 18 distinct sessions between 2026-07-19 and 2026-08-25, spanning
three repos (attune-ai, attune-forms, IndianRailroadTicketing). It is
the single most repeated non-existent command in the corpus by a wide
margin; every other unresolvable candidate appeared once or was a
scanner artifact.

18 is a FLOOR, not an estimate: the sweep can only see sessions where
the error string survived into a stored transcript, so it undercounts
by an unknown amount. The number is stated as a floor rather than
rounded up because a guard whose justification is a guess cannot ask
anyone to trust its judgment.

The fix needs no new tooling: the Bash tool takes its own `timeout`
parameter (milliseconds), which is what those 18 sessions wanted.

Blocks (exit 2) only when ALL of these hold, so the guard self-disables
rather than nagging:
  - the platform is macOS,
  - `timeout` is genuinely absent from PATH (install coreutils and this
    guard stops firing on its own),
  - `timeout` appears in COMMAND POSITION — not inside quotes, a
    heredoc body, a comment, or as a flag like `--timeout 30`.

Escape hatch: include ATTUNE_ALLOW_TIMEOUT=1 in the command.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow the call
    exit 2: block the call, reason on stderr
"""

from __future__ import annotations

import json
import re
import shutil
import sys

#: Heredoc bodies are payloads, not commands — a script being WRITTEN
#: may legitimately contain `timeout` for a Linux runner.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\s*\2\s*$", re.S | re.M)

#: `timeout` in command position: at the start, or after a separator,
#: optionally preceded by env assignments (`TZ=UTC timeout 5 ...`).
_TIMEOUT_CMD = re.compile(
    r"(?:^|[;&|(]|\n)\s*(?:[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|\S*)\s+)*" r"timeout(?=\s)"
)


def _strip_noise(command: str) -> str:
    """Remove heredoc bodies, quoted strings, and comments.

    Each removal is replaced by a space rather than deleted so that
    command separators around it keep their positions.
    """
    text = _HEREDOC.sub(" ", command)
    text = re.sub(r"'[^']*'", " ", text)
    text = re.sub(r'"[^"]*"', " ", text)
    return re.sub(r"(?m)#.*$", " ", text)


def uses_bare_timeout(command: str) -> bool:
    """Return True when `command` invokes `timeout` as a program."""
    return bool(_TIMEOUT_CMD.search(_strip_noise(command)))


def main() -> int:
    """Block a macOS Bash command that shells out to `timeout`."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # Never block on a malformed payload.

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "ATTUNE_ALLOW_TIMEOUT=1" in command:
        return 0
    if sys.platform != "darwin" or shutil.which("timeout"):
        return 0
    if not uses_bare_timeout(command):
        return 0

    print(
        "Blocked: `timeout` is GNU coreutils and is not installed on this "
        "Mac, so this command would fail with `command not found: timeout` "
        "and the work inside it would never run (measured in at least 18 "
        "sessions since 2026-07-19). Use the Bash tool's own `timeout` parameter "
        "instead — it takes milliseconds, e.g. timeout: 480000 for 8 "
        "minutes. Override once with ATTUNE_ALLOW_TIMEOUT=1.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
