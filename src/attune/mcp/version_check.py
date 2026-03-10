"""PyPI version check for attune-ai.

Checks for available updates at MCP server startup.
Network failures are silently ignored — this is best-effort only.
"""

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_cached_status: dict[str, Any] | None = None


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
        with urllib.request.urlopen(req, timeout=2) as resp:  # nosec B310
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
