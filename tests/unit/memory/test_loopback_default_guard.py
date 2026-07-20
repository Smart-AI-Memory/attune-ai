"""Regression guard: no ``"localhost"`` host defaults in the memory stack.

``getaddrinfo("localhost")`` runs BEFORE ``socket_connect_timeout``
applies and is uninterruptible by ``--timeout-method=thread``; a
stalled resolver wedged ``windows-latest`` workers for 20 minutes and
produced the exit-139 segfault class (sightings 1-4). PR #1282 swapped
every default host in the memory stack and the centralized redis
config to the literal loopback ``127.0.0.1``.

This guard fails if a ``host=...="localhost"`` default or a
``REDIS_HOST`` env fallback of ``"localhost"`` reappears anywhere on
that surface. Deliberate string-compare uses (``_LOCAL_HOSTS`` mode
inference, docstrings, CORS origin checks) do not match the patterns.

Spec: docs/specs/windows-exit139-segfault/
"""

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Every production file #1282 had to fix lives on this surface.
GUARDED_PATHS = [
    REPO_ROOT / "src" / "attune" / "memory",
    REPO_ROOT / "src" / "attune" / "redis_config.py",
]

# ``host: str = "localhost"``, ``redis_host="localhost"``,
# ``self.host = "localhost"`` — any lowercase *host name defaulted or
# assigned the resolvable hostname. ``_LOCAL_HOSTS`` (uppercase, set
# literal) and ``"host": "localhost"`` dict keys do not match.
_LOCALHOST_DEFAULT = re.compile(r"""[a-z_]*host\w*\s*(?::\s*[^=\n]+?)?=\s*["']localhost["']""")

# ``get_attune_env("REDIS_HOST", "localhost")`` / os.environ fallbacks.
_ENV_FALLBACK = re.compile(r"""["']REDIS_HOST["']\s*,\s*["']localhost["']""")


def _guarded_files() -> list[Path]:
    files: list[Path] = []
    for path in GUARDED_PATHS:
        if path.is_file():
            files.append(path)
        else:
            files.extend(sorted(path.rglob("*.py")))
    return files


def test_no_localhost_host_defaults_in_memory_stack() -> None:
    """No guarded file defaults or assigns a host to "localhost"."""
    files = _guarded_files()
    assert len(files) > 10, f"guard surface unexpectedly small: {files}"

    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _LOCALHOST_DEFAULT.search(line) or _ENV_FALLBACK.search(line):
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "'localhost' host default reintroduced — getaddrinfo on the "
        "default path wedges Windows CI workers (exit-139 class, "
        "docs/specs/windows-exit139-segfault/). Use the literal "
        "loopback '127.0.0.1':\n" + "\n".join(offenders)
    )


def test_unit_lane_pins_redis_host_to_loopback() -> None:
    """The tests/conftest.py belt-and-suspenders pin is in effect.

    conftest replaces an unset/empty/"localhost" REDIS_HOST with
    127.0.0.1 before collection; a deliberate non-default host is left
    alone. Whatever the source, no unit test may run with a
    resolvable-hostname default.
    """
    assert os.environ.get("REDIS_HOST") not in (None, "", "localhost"), (
        "REDIS_HOST is unset or 'localhost' during the unit lane — the "
        "tests/conftest.py loopback pin (PR #1282) is no longer applied"
    )
