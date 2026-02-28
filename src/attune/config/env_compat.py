"""Environment variable compatibility layer.

Supports both ATTUNE_ (canonical) and EMPATHY_ (deprecated) prefixes.
ATTUNE_ takes precedence when both are set.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

logger = logging.getLogger(__name__)

# Track which deprecation warnings have been issued to avoid spam
_warned_vars: set[str] = set()


def get_attune_env(name: str, default: str | None = None) -> str | None:
    """Get an environment variable, checking ATTUNE_ first then EMPATHY_ fallback.

    Args:
        name: Variable name without prefix (e.g. "LOG_LEVEL", "REDIS_MOCK").
        default: Default value if neither prefix is set.

    Returns:
        The value from ATTUNE_{name}, or EMPATHY_{name} with a deprecation
        warning, or the default.

    """
    attune_key = f"ATTUNE_{name}"
    empathy_key = f"EMPATHY_{name}"

    attune_val = os.environ.get(attune_key)
    if attune_val is not None:
        return attune_val

    empathy_val = os.environ.get(empathy_key)
    if empathy_val is not None:
        if empathy_key not in _warned_vars:
            _warned_vars.add(empathy_key)
            logger.warning(
                "%s is deprecated, use %s instead",
                empathy_key,
                attune_key,
            )
        return empathy_val

    return default


def iter_attune_env_prefix(prefix: str, suffix: str = "") -> Iterator[tuple[str, str]]:
    """Yield (middle_part, value) for env vars matching ATTUNE_{prefix}*{suffix}.

    Also checks EMPATHY_{prefix}*{suffix} as fallback. If both ATTUNE_ and
    EMPATHY_ versions exist for the same middle part, ATTUNE_ wins.

    Args:
        prefix: The prefix after ATTUNE_/EMPATHY_ (e.g. "WORKFLOW_").
        suffix: Optional suffix the key must end with (e.g. "_PROVIDER").

    Yields:
        Tuples of (middle_part, value) where middle_part is the string
        between prefix and suffix.

    """
    attune_prefix = f"ATTUNE_{prefix}"
    empathy_prefix = f"EMPATHY_{prefix}"

    # Collect results: middle_part -> value, ATTUNE_ wins
    results: dict[str, str] = {}
    empathy_keys_used: dict[str, str] = {}  # middle -> empathy key name

    for key, value in os.environ.items():
        for env_prefix, is_attune in [
            (attune_prefix, True),
            (empathy_prefix, False),
        ]:
            if not key.startswith(env_prefix):
                continue
            rest = key[len(env_prefix) :]
            if suffix and not rest.endswith(suffix):
                continue
            middle = rest[: len(rest) - len(suffix)] if suffix else rest

            if is_attune:
                results[middle] = value
                # Remove from empathy tracking if ATTUNE_ overrides
                empathy_keys_used.pop(middle, None)
            elif middle not in results:
                results[middle] = value
                empathy_keys_used[middle] = key

    # Issue deprecation warnings for EMPATHY_ keys actually used
    for middle, empathy_key in empathy_keys_used.items():
        attune_key = f"{attune_prefix}{middle}{suffix}"
        if empathy_key not in _warned_vars:
            _warned_vars.add(empathy_key)
            logger.warning(
                "%s is deprecated, use %s instead",
                empathy_key,
                attune_key,
            )

    yield from results.items()
