"""Detect stale external ``attune.plugins`` / ``attune.wizards`` entries.

16.0.0 collapsed both entry-point groups to direct registration
(release-16-manifest D1), so a third-party distribution that still
declares entries in them fails by SILENT non-loading — nothing in the
user's own code is greppable, so the migration guide cannot reach them.
This module is the cheap detector the 16.0 round table ratified: one
scan of installed distribution metadata at startup, one warning line
per offending distribution, pointing at the migration guide.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from importlib import metadata

logger = logging.getLogger(__name__)

#: Entry-point groups collapsed in 16.0.0. ``attune.memory_backends``
#: (the one seam the architecture ruling keeps) is deliberately absent.
STALE_GROUPS: frozenset[str] = frozenset({"attune.plugins", "attune.wizards"})

MIGRATION_GUIDE = "docs/migration/upgrading-to-16.0.0.md"

# Once-per-process guard: the scan runs at most once, however many
# registries call in.
_scan_done = False


def _normalize(dist_name: str) -> str:
    """Normalize a distribution name per PEP 503."""
    return dist_name.strip().lower().replace("_", "-")


def _find_stale_distributions() -> dict[str, list[str]]:
    """Map external dist name -> sorted stale groups it still declares.

    Iterates installed distributions directly (rather than
    ``metadata.entry_points(group=...)``) so the owning distribution's
    name is available uniformly across supported Python versions.
    attune-ai itself is skipped — its own groups are pinned absent from
    pyproject by a drift guard, and its dist is never the audience.
    """
    stale: dict[str, set[str]] = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"] or ""
        if not name or _normalize(name) == "attune-ai":
            continue
        groups = {ep.group for ep in dist.entry_points} & STALE_GROUPS
        if groups:
            stale.setdefault(name, set()).update(groups)
    return {name: sorted(groups) for name, groups in stale.items()}


def warn_stale_entry_points() -> None:
    """Warn once per process about stale external entry-point registrations.

    Called from the plugin and wizard registries' first load. Fail-open
    by contract: a metadata scan error is debug-logged and swallowed —
    the warning is best-effort advice and must never affect startup.
    """
    global _scan_done
    if _scan_done:
        return
    _scan_done = True

    try:
        stale = _find_stale_distributions()
    except Exception:  # noqa: BLE001
        # INTENTIONAL fail-open: reading arbitrary installed packages'
        # metadata can raise anything; startup must not care.
        logger.debug("Stale entry-point scan failed; skipping", exc_info=True)
        return

    for dist_name in sorted(stale):
        logger.warning(
            "Package '%s' registers entry points in %s, which attune-ai "
            "16.0.0 no longer loads — its plugins/wizards are silently "
            "ignored. See %s.",
            dist_name,
            ", ".join(f"'{g}'" for g in stale[dist_name]),
            MIGRATION_GUIDE,
        )


def _reset_scan_cache() -> None:
    """Reset the once-per-process guard (test hook)."""
    global _scan_done
    _scan_done = False
