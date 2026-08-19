"""Hook Scripts

Pre-built hook scripts for common Attune AI events.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.hooks.scripts.evaluate_session import (
    apply_learned_patterns,
    get_learning_summary,
    run_evaluate_session,
)
from attune.hooks.scripts.first_time_init import (
    check_init,
    handle_init_response,
    initialize_project,
)
from attune.hooks.scripts.suggest_compact import main as suggest_compact

__all__ = [
    "apply_learned_patterns",
    "check_init",
    "get_learning_summary",
    "handle_init_response",
    "initialize_project",
    "run_evaluate_session",
    "suggest_compact",
]
