"""Dead-suite guard — a module-level ``importorskip`` must be able to import.

The class this kills (found twice on 2026-08-16): a test module opens
with ``pytest.importorskip("dep")`` and ``dep`` is not in the ``[dev]``
extra / ``dev`` group, so the WHOLE module silently skips in every
environment, CI included, forever — the webhook SSRF/DNS-pinning suite
(aiohttp, PR #2074) and both backend auth-security suites (bcrypt, this
PR) had never executed anywhere. CI stays green; the suite is dead.

This guard fails when any module-level importorskip's dependency is
missing from THIS environment, unless the (file, dep) pair is
allowlisted below with a reason. An empty allowlist is the healthy
state: every skip-capable suite actually runs where the tests run.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]

_IMPORTORSKIP_RE = re.compile(r'pytest\.importorskip\(\s*["\']([^"\']+)["\']')

#: (test file relative to tests/, dependency) -> reason the skip is
#: acceptable. Add entries ONLY for genuinely environment-conditional
#: dependencies (platform-specific, license-gated), never for "we
#: forgot to add it to [dev]" — that is the bug this guard exists for.
ALLOWED_MODULE_SKIPS: dict[tuple[str, str], str] = {}


def _module_level_importorskips() -> list[tuple[str, str]]:
    """Every (file, dep) whose importorskip runs at module import time.

    Heuristic: the call appears at column 0 (module level). An indented
    importorskip inside a fixture or test skips only its own scope and
    cannot kill a whole module.
    """
    found: list[tuple[str, str]] = []
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        rel = str(path.relative_to(TESTS_ROOT))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(("pytest.importorskip", "_ = pytest.importorskip")) or re.match(
                r"^\w+\s*=\s*pytest\.importorskip", line
            ):
                match = _IMPORTORSKIP_RE.search(line)
                if match:
                    found.append((rel, match.group(1)))
    return found


def test_every_module_level_importorskip_can_import() -> None:
    dead: list[str] = []
    for rel, dep in _module_level_importorskips():
        if (rel, dep) in ALLOWED_MODULE_SKIPS:
            continue
        try:
            importlib.import_module(dep)
        except Exception:  # noqa: BLE001 — any import failure means a dead module
            dead.append(f"{rel}: importorskip({dep!r}) skips the WHOLE module")
    assert not dead, (
        "Dead suite(s) — these modules silently skip in this environment. "
        "Add the dependency to the [dev] extra AND the dev dependency "
        "group (the mirror guard holds them equal), or allowlist the "
        "pair with a reason if the skip is genuinely environmental:\n  " + "\n  ".join(dead)
    )


def test_allowlist_entries_are_still_needed() -> None:
    """An allowlisted dep that has become importable is stale ceremony —
    remove the entry so the guard stays meaningful."""
    stale = []
    for (rel, dep), reason in ALLOWED_MODULE_SKIPS.items():
        try:
            importlib.import_module(dep)
        except Exception:  # noqa: BLE001
            continue
        stale.append(f"{rel}: {dep} now imports ({reason!r} no longer applies)")
    assert not stale, "Stale allowlist entries:\n  " + "\n  ".join(stale)
