"""Extract ``<cli> <subcommand> --help`` output for prompt injection.

Spawns the consumer CLI as a subprocess with a 10-second timeout and
caches the output per (executable, subcommand) tuple for the duration
of the process. Cache invalidation isn't needed — the lookup is
per-polish-call and a regen of one feature uses the cache exactly once
for each subcommand it references.
"""

from __future__ import annotations

import logging
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

#: Hard cap on the time we wait for ``<cli> --help`` to return. CLIs
#: that don't respond in 10 seconds are degenerate; we'd rather skip
#: their help block than block the whole polish run.
_HELP_TIMEOUT_SECONDS = 10


@lru_cache(maxsize=128)
def _help_cached(
    executable: str,
    subcommand: str,
    cwd_str: str,
) -> str:
    """Cached worker for :func:`extract_cli_help`.

    Args:
        executable: CLI executable name (e.g., ``"attune"``).
        subcommand: Subcommand to query (e.g., ``"ops"``).
        cwd_str: Working directory for the subprocess, as a string so
            the cache key stays hashable.

    Returns:
        The CLI's ``--help`` stdout, or an empty string on failure.
    """
    args = [executable, subcommand, "--help"]
    try:
        result = subprocess.run(  # noqa: S603 - args are trusted manifest input
            args,
            cwd=cwd_str,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_HELP_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning(
            "ground_truth.cli_help: %s %s --help failed: %s",
            executable,
            subcommand,
            exc,
        )
        return ""

    if result.returncode != 0:
        logger.warning(
            "ground_truth.cli_help: %s %s --help exited %d (stderr: %s)",
            executable,
            subcommand,
            result.returncode,
            (result.stderr or "").strip()[:200],
        )
        return ""

    return result.stdout or ""


def extract_cli_help(
    executable: str,
    subcommand: str,
    *,
    project_root: Path,
) -> str:
    """Return the cached ``<executable> <subcommand> --help`` output.

    Args:
        executable: CLI executable name. Must be on PATH.
        subcommand: Subcommand to query.
        project_root: Working directory for the subprocess. Allows the
            CLI to load project-local configuration when relevant.

    Returns:
        Captured stdout, or an empty string when the CLI is missing,
        non-zero, or times out. Empty results are silently dropped by
        the caller — they don't fail the polish.
    """
    if not executable or not subcommand:
        return ""
    return _help_cached(executable, subcommand, str(project_root))


def clear_cache() -> None:
    """Reset the in-process cache. Tests use this to isolate runs."""
    _help_cached.cache_clear()


__all__ = ["clear_cache", "extract_cli_help"]
