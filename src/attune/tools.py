"""Interactive user prompting tools.

Provides tools for asking users questions and getting structured responses.
This module implements the AskUserQuestion functionality used by the
meta-orchestrator for interactive agent team creation.

Integration with Claude Code:
    When running Python code that calls this function, Claude Code will
    detect the call and use its AskUserQuestion tool to prompt the user
    in the IDE. This is implemented via a request/response IPC mechanism.

Created: 2026-01-29
"""

import json
import logging
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Global callback for custom AskUserQuestion implementations
_custom_ask_function: Callable | None = None


def set_ask_user_question_handler(handler: Callable) -> None:
    """Set a custom handler for AskUserQuestion.

    This allows integration with different UI systems (CLI, web, IDE).

    Args:
        handler: Callable that takes questions list and returns response dict

    Example:
        >>> def my_handler(questions):
        ...     # Custom UI logic
        ...     return {"Pattern": "sequential"}
        >>> set_ask_user_question_handler(my_handler)

    """
    global _custom_ask_function
    _custom_ask_function = handler
    logger.info("Custom AskUserQuestion handler registered")


def AskUserQuestion(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Ask user questions and get structured responses.

    This function supports multiple integration modes:
    1. Custom handler (via set_ask_user_question_handler)
    2. Claude Code IPC (when running in Claude Code environment)
    3. Fallback to NotImplementedError (prompts caller to use automatic mode)

    Args:
        questions: List of question dictionaries, each with:
            - header: Short label for the question (str, max 12 chars)
            - question: Full question text (str)
            - multiSelect: Allow multiple selections (bool)
            - options: List of option dicts with label and description

    Returns:
        Dictionary mapping question headers to selected answers

    Raises:
        NotImplementedError: If no handler available and not in Claude Code
        RuntimeError: If user cancels or interaction fails

    Example:
        >>> response = AskUserQuestion(
        ...     questions=[{
        ...         "header": "Pattern",
        ...         "question": "Which pattern to use?",
        ...         "multiSelect": False,
        ...         "options": [
        ...             {"label": "sequential", "description": "One after another"},
        ...             {"label": "parallel", "description": "All at once"}
        ...         ]
        ...     }]
        ... )
        >>> response
        {"Pattern": "sequential"}

    """
    # Mode 1: Custom handler
    if _custom_ask_function is not None:
        logger.info("Using custom AskUserQuestion handler")
        return _custom_ask_function(questions)

    # Mode 2: Claude Code IPC
    # When running inside Claude Code, we can use a file-based IPC mechanism
    if _is_running_in_claude_code():
        logger.info("Using Claude Code IPC for AskUserQuestion")
        return _ask_via_claude_code_ipc(questions)

    # Mode 3: Fallback - raise error with helpful message
    logger.warning("No AskUserQuestion handler available")
    raise NotImplementedError(
        "AskUserQuestion requires either:\n"
        "1. Custom handler via set_ask_user_question_handler()\n"
        "2. Running in Claude Code environment\n"
        "3. Using interactive=False for automatic mode\n\n"
        "Use: orchestrator.analyze_and_compose(task, interactive=False)",
    )


def _is_running_in_claude_code() -> bool:
    """Check if code is running inside Claude Code environment.

    Returns:
        True if running in Claude Code, False otherwise

    """
    # Check for Claude Code environment markers
    return (
        os.getenv("CLAUDE_CODE_SESSION") is not None
        or os.getenv("CLAUDE_AGENT_MODE") is not None
        or Path("/tmp/.claude-code").exists()  # nosec B108
    )


def _ask_via_claude_code_ipc(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Ask user questions via Claude Code IPC mechanism.

    This creates a request file that Claude Code monitors, then waits for
    the response file to be created with the user's answers.

    Args:
        questions: List of question dictionaries

    Returns:
        User's responses as a dictionary

    Raises:
        RuntimeError: If communication fails or times out

    """
    import time
    import uuid

    request_id = str(uuid.uuid4())
    ipc_dir = Path(tempfile.gettempdir()) / ".claude-code-ipc"
    ipc_dir.mkdir(exist_ok=True)

    request_file = ipc_dir / f"ask-request-{request_id}.json"
    response_file = ipc_dir / f"ask-response-{request_id}.json"

    try:
        # Write request
        request_data = {
            "request_id": request_id,
            "questions": questions,
            "timestamp": time.time(),
        }

        request_file.write_text(json.dumps(request_data, indent=2))
        logger.info(f"Wrote IPC request: {request_file}")

        # Wait for response (max 60 seconds)
        timeout = 60
        start_time = time.time()

        while time.time() - start_time < timeout:
            if response_file.exists():
                # Read response
                response_data = json.loads(response_file.read_text())
                logger.info(f"Received IPC response: {response_data}")

                # Cleanup
                request_file.unlink(missing_ok=True)
                response_file.unlink(missing_ok=True)

                return response_data.get("answers", {})

            time.sleep(0.1)  # Poll every 100ms

        raise RuntimeError(
            f"Timeout waiting for user response (waited {timeout}s). "
            "User may have cancelled or Claude Code IPC is not active.",
        )

    except Exception as e:
        # Cleanup on error
        request_file.unlink(missing_ok=True)
        response_file.unlink(missing_ok=True)
        raise RuntimeError(f"Claude Code IPC failed: {e}") from e
