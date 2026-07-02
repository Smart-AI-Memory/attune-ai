#!/usr/bin/env bash
#
# Default-install smoke gate.
#
# The base `attune` CLI must boot under a DEFAULT install
# (`pip install attune-ai`, with NO extras). This catches the class of
# bug where the base CLI transitively imports an extras-only dependency
# (e.g. fastapi from `[ops]`) and crashes on startup — invisible to the
# normal test suite, which always installs the dev/ops extras.
#
# Concretely: 8.5.0 shipped with `attune --help` crashing with
# `ModuleNotFoundError: No module named 'fastapi'` on every default
# install, because a base-CLI import path pulled a symbol from the
# FastAPI web-route module. CI never saw it (fastapi was always present).
# This gate reproduces the real default-install environment and boots the
# CLI, so that class can never ship again.
#
# It also probes the personal-memory capture -> recall round-trip against
# the shipped wheel. 9.3.0 shipped with `attune memory recall` broken
# (capture succeeded; recall printed "No results found." and exited 0)
# while every unit test was green — the tests mocked the RAG layer that
# was broken. The probe asserts on recall CONTENT under a fake HOME,
# never on the exit code, so that class can't ship again either.
#
# Usage:
#   scripts/smoke_default_install.sh [path/to/attune_ai-*.whl]
#
# With no argument it builds a wheel from the repo (requires `build`).
# In CI, pass the wheel already produced by the `build` job.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

WHEEL="${1:-}"
if [[ -z "$WHEEL" ]]; then
  echo "== no wheel given — building one from the repo =="
  python -m build --wheel --outdir "$WORK/dist" "$ROOT"
  WHEEL="$(ls "$WORK"/dist/*.whl | head -n1)"
fi
echo "== wheel under test: $WHEEL =="

echo "== creating a fresh venv and BARE-installing (no extras) =="
python -m venv "$WORK/venv"
VPY="$WORK/venv/bin/python"
"$VPY" -m pip install --quiet --upgrade pip
"$VPY" -m pip install --quiet "$WHEEL"

echo "== sanity: confirm this is a true default install (extras absent) =="
"$VPY" - <<'PY'
import importlib.util
import sys

# fastapi belongs to the [ops] extra and is the marker for the web stack —
# it is exactly what the base CLI must NOT need. If a CORE dependency ever
# pulls it in transitively, this smoke would be testing the wrong thing
# (the original bug would pass), so fail loudly. (uvicorn is intentionally
# NOT checked: it is a core transitive dependency, present in every install.)
if importlib.util.find_spec("fastapi") is not None:
    sys.exit("ERROR: fastapi present in a bare install — not a clean default env (the [ops] gate is meaningless)")
print("confirmed: fastapi (the [ops] web stack) is absent — true default install")
PY

echo "== smoke: the base CLI must boot without extras =="
ATTUNE="$WORK/venv/bin/attune"
"$ATTUNE" --help >/dev/null
"$ATTUNE" version

echo "== smoke: personal-memory capture -> recall must round-trip =="
# The 9.3.0 regression class: recall exits 0 even with zero hits, so a
# boot-only smoke can't see it. Probe under a fake HOME (isolated global
# memory root, exactly the clean-venv + fake-HOME audit that caught the
# original bug) and assert on the returned content. ANTHROPIC_API_KEY is
# set EMPTY (not unset) so dotenv cannot inject a real key; the whole
# round-trip is keyless (polish degrades gracefully without attune-author).
PROBE_HOME="$WORK/home"
mkdir -p "$PROBE_HOME"
SENTINEL="smoke sentinel: the quarterly fox prefers decaf espresso"

(
  cd "$WORK"
  HOME="$PROBE_HOME" ANTHROPIC_API_KEY="" \
    "$ATTUNE" memory capture smoke-recall-probe "$SENTINEL" --kind reference
)
CAPTURED="$PROBE_HOME/.attune/memory/smoke-recall-probe/reference.md"
if [[ ! -f "$CAPTURED" ]]; then
  echo "FAIL: capture wrote nothing at $CAPTURED"
  exit 1
fi

RECALL_JSON="$(
  cd "$WORK"
  HOME="$PROBE_HOME" ANTHROPIC_API_KEY="" \
    "$ATTUNE" memory recall "quarterly fox decaf espresso" --json
)"
# NOTE: `python - <<HEREDOC` would consume stdin for the script itself,
# leaving json.load(sys.stdin) an empty stream — pipe into `-c` instead.
printf '%s' "$RECALL_JSON" | "$VPY" -c '
import json
import sys

hits = json.load(sys.stdin)
if not hits:
    sys.exit(
        "FAIL: recall returned zero hits for freshly captured content "
        "(the 9.3.0 broken-round-trip class - exit code alone would not catch this)"
    )
if not any("smoke-recall-probe" in hit.get("path", "") for hit in hits):
    sys.exit("FAIL: recall hits do not include the captured topic: %r" % hits)
print("confirmed: recall round-trips (%d hit(s), top: %s)" % (len(hits), hits[0]["path"]))
'

echo "PASS: default-install CLI boots and personal memory round-trips without extras"
