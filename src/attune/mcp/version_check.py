"""PyPI version check for attune-ai.

Checks for available updates at MCP server startup.
Network failures are silently ignored — this is best-effort only.
"""

import json
import logging
import os
import threading
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_cached_status: dict[str, Any] | None = None

#: ``ATTUNE_VERSION_CHECK`` values that switch the background check off.
_FALSEY = frozenset({"0", "false", "no", "off"})
_start_lock = threading.Lock()
_started = False


def background_check_enabled() -> bool:
    """False when ``ATTUNE_VERSION_CHECK`` opts out (the test suite does)."""
    return os.environ.get("ATTUNE_VERSION_CHECK", "1").strip().lower() not in _FALSEY


def start_background_check() -> threading.Thread | None:
    """Run :func:`check_for_updates` on a daemon thread at most ONCE per process.

    Every ``AttuneMCPServer`` construction used to start its own thread. A
    per-test server fixture then ran several concurrent checks inside one
    xdist worker, and two of them racing in ``ssl.load_default_certs``
    segfaulted the interpreter (CI run 34173042218, 2026-09-08). One thread
    per process removes the race; the env opt-out keeps test suites from
    reaching PyPI at all.

    Returns:
        The started thread, or None when the check is disabled or a thread
        was already started in this process.

    """
    global _started  # noqa: PLW0603

    if not background_check_enabled():
        return None
    with _start_lock:
        if _started:
            return None
        _started = True
    thread = threading.Thread(target=check_for_updates, name="attune-version-check", daemon=True)
    thread.start()
    return thread


def check_for_updates() -> dict[str, Any] | None:
    """Check PyPI for a newer version of attune-ai.

    Fetches the latest version from PyPI JSON API with a 2-second timeout.
    Compares against the installed version. Results are cached for the
    lifetime of the process.

    Returns:
        Dict with keys (latest, current, update_available) or None if
        the check fails or the current version is up to date.

    """
    global _cached_status  # noqa: PLW0603

    if _cached_status is not None:
        return _cached_status

    try:
        import attune

        current = attune.__version__
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Can't determine current version — skip check
        return None

    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/attune-ai/json",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(
            req, timeout=2
        ) as resp:  # noqa: S310  # nosec B310 — hardcoded https URL
            data = json.loads(resp.read().decode("utf-8"))

        latest = data.get("info", {}).get("version", "")
        if not latest:
            return None

        update_available = _compare_versions(current, latest)

        _cached_status = {
            "latest": latest,
            "current": current,
            "update_available": update_available,
        }
        return _cached_status

    except Exception:  # noqa: BLE001
        # INTENTIONAL: Network failures silently skip — version check is best-effort
        return None


def get_update_status() -> dict[str, Any] | None:
    """Get cached update status.

    Returns:
        Cached result from check_for_updates(), or None if not yet checked.

    """
    return _cached_status


def _compare_versions(current: str, latest: str) -> bool:
    """Compare version strings to determine if an update is available.

    Uses tuple comparison of integer version parts.
    Falls back to string comparison if parsing fails.

    Args:
        current: Currently installed version string
        latest: Latest available version string

    Returns:
        True if latest is newer than current

    """
    try:
        current_parts = tuple(int(x) for x in current.split(".")[:3])
        latest_parts = tuple(int(x) for x in latest.split(".")[:3])
        return latest_parts > current_parts
    except (ValueError, TypeError):
        return latest != current
