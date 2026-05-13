"""Control: stdlib logger.info called with kwargs — real bug.

The file imports stdlib logging, not structlog. ``logger.info``
with ``user_id=...`` would raise TypeError. The rule must NOT
fire (the file does not use structlog).
"""

import logging

logger = logging.getLogger(__name__)


def record_event(user_id: str) -> None:
    """Real bug — stdlib Logger doesn't accept kwargs."""
    logger.info("user event", user_id=user_id)
