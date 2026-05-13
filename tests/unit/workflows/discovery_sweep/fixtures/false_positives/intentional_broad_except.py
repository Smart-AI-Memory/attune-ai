"""False-positive fixture: intentional broad except w/ noqa + INTENTIONAL.

Documented graceful-degradation pattern from coding standards.
"""

import logging

logger = logging.getLogger(__name__)


def get_package_version() -> str:
    """Get package version with graceful fallback."""
    try:
        from importlib.metadata import version

        return version("attune-ai")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: fallback for dev installs without metadata
        logger.debug("version metadata unavailable")
        return "dev"
