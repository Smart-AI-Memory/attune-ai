#!/usr/bin/env bash
# Run a command writing RAW output to a log — never pipe a background
# run (retro 2026-08-24 item 3.1: `... | tail` and `... | grep` buffer
# until exit, so the task's output file stays EMPTY for the whole run
# and progress is invisible; hit live twice in one day, and the trap
# is documented in the lessons corpus).
#
# Usage:  scripts/bg_run.sh <logfile> <command> [args...]
# Filter at READ time instead:  tail -f <logfile> | grep PASS
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "usage: bg_run.sh <logfile> <command> [args...]" >&2
  exit 125
fi
log="$1"; shift
"$@" >"$log" 2>&1
