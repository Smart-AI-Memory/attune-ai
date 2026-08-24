#!/usr/bin/env bash
# Run the test suite EXACTLY as CI's test lane does (retro 2026-08-24
# item 3.2). Two local-run mistakes this mirrors away:
#
#   1. Scope: CI collects the WHOLE tests/ tree — local sweeps scoped
#      to tests/unit missed top-level tests/models + tests/security
#      failures twice on 2026-08-24.
#   2. Auth: CI sets ANTHROPIC_API_KEY to the EMPTY STRING (keyless).
#      Unsetting it instead lets load_dotenv inject the real key from
#      ~/.attune/anthropic.env and a "keyless" run spends real money
#      (corpus lesson, 2026-06-10).
#
# Mirrors .github/workflows/tests.yml's test-lane invocation. If that
# workflow's pytest line changes, change this in the same PR —
# tests/unit/scripts/test_ci_local_mirror.py pins the two stay in sync.
set -euo pipefail
cd "$(dirname "$0")/.."
ANTHROPIC_API_KEY="" pytest -n auto --timeout=60 --timeout-method=thread -m "not network and not integration" "$@"
