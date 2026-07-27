"""Enforce a byte-budget on the ground-truth context block list.

Drop order documented in the spec: dataclasses → public_api → cli_help.
The most disposable block goes first so the most-authoritative anchor
(CLI ``--help``) is the last to be dropped. We measure characters
rather than tokens — accurate enough for a 5KB-sized budget, and
keeps this module pure (no tokenizer dependency).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


#: Order in which blocks are dropped to fit the budget. Lower index =
#: drop first. Tags not in this list keep their original ordering and
#: are dropped last (after every listed tag has been removed).
_DROP_ORDER = ("dataclasses", "public_api", "cli_help")


def _budget_size(blocks: list[tuple[str, str]]) -> int:
    """Return the rendered byte size of the block list.

    Rendering format: ``<tag>\\n{body}\\n</tag>\\n`` with one blank
    line between blocks. The arithmetic here matches what the
    formatter in :mod:`attune.authoring.ground_truth.__init__` produces,
    so the caller's output stays inside the budget after rendering.
    """
    if not blocks:
        return 0
    total = 0
    for tag, body in blocks:
        total += len(tag) * 2 + len("<>\n\n</>\n") + len(body)
    total += len(blocks) - 1  # blank lines between blocks
    return total


def _drop_one(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Drop a single block per the documented order. Mutates a copy."""
    remaining = list(blocks)
    for tag in _DROP_ORDER:
        for idx, (existing_tag, _body) in enumerate(remaining):
            if existing_tag == tag:
                logger.warning(
                    "ground_truth.budget: dropped %s block to fit budget",
                    existing_tag,
                )
                remaining.pop(idx)
                return remaining
    # Fall through: drop the last block if no documented tag is present.
    if remaining:
        dropped_tag = remaining[-1][0]
        logger.warning(
            "ground_truth.budget: dropped %s block (fallback) to fit budget",
            dropped_tag,
        )
        remaining.pop()
    return remaining


def enforce_budget(
    blocks: list[tuple[str, str]],
    budget_bytes: int,
) -> list[tuple[str, str]]:
    """Drop blocks in documented order until the rendered size fits.

    Args:
        blocks: List of ``(tag, body)`` tuples in the order the caller
            wants to render them.
        budget_bytes: Maximum allowed rendered size in characters.
            Non-positive values disable enforcement (returns input
            unchanged).

    Returns:
        A possibly-shorter list of ``(tag, body)`` tuples. Always
        returns at least an empty list — never ``None``.
    """
    if budget_bytes <= 0:
        return blocks
    remaining = list(blocks)
    while remaining and _budget_size(remaining) > budget_bytes:
        remaining = _drop_one(remaining)
    return remaining


__all__ = ["enforce_budget"]
