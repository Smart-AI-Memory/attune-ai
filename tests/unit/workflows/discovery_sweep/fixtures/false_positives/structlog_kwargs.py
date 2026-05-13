"""False-positive fixture: structlog kwargs.

Scanners that assume stdlib Logger semantics flag the kwargs as
TypeError. structlog's bound logger accepts them.
"""

import structlog

logger = structlog.get_logger(__name__)


def record_event(user_id: str, payload: dict) -> None:
    """Emit a structured log event with kwargs."""
    logger.info("user.event", user_id=user_id, payload_keys=list(payload))
