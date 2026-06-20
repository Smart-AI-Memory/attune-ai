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

echo "PASS: default-install CLI boots without extras"
