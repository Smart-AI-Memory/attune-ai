"""Refactoring Crew - Checkpoint Management

Standalone functions for creating checkpoints and rolling back changes
during refactoring operations.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import uuid
from datetime import datetime

from .types import CodeCheckpoint


def create_checkpoint(
    file_path: str,
    content: str,
    finding_id: str,
) -> CodeCheckpoint:
    """Create a checkpoint before applying a change.

    Args:
        file_path: Path to the file.
        content: Current content of the file.
        finding_id: ID of the finding being applied.

    Returns:
        CodeCheckpoint that can be used for rollback.

    """
    checkpoint = CodeCheckpoint(
        id=str(uuid.uuid4()),
        file_path=file_path,
        original_content=content,
        timestamp=datetime.now().isoformat(),
        finding_id=finding_id,
    )
    return checkpoint


def rollback(checkpoint: CodeCheckpoint) -> str:
    """Get the original content from a checkpoint.

    Args:
        checkpoint: The checkpoint to rollback to.

    Returns:
        The original file content.

    """
    return checkpoint.original_content
