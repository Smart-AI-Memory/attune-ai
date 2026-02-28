"""One-Command Workflows for Attune AI -- Facade Module

Power-user commands that automate common developer workflows:
- morning: Start-of-day briefing with patterns, debt, and focus areas
- ship: Pre-commit validation pipeline
- fix-all: Auto-fix all fixable issues
- learn: Watch for bug fixes and extract patterns

This module is a thin facade that re-exports the public API from
focused submodules while preserving full backward compatibility.
Implementations live in:
    attune._workflow_helpers   (shared utilities)
    attune.workflow_morning    (morning briefing)
    attune.workflow_ship       (pre-ship validation)
    attune.workflow_fixall     (auto-fix)
    attune.workflow_learn      (pattern learning)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

# ---------------------------------------------------------------------------
# Helpers (re-exported so existing imports keep working)
# ---------------------------------------------------------------------------
from attune._workflow_helpers import (  # noqa: F401
    _get_tech_debt_trend,
    _load_patterns,
    _load_stats,
    _run_command,
    _save_stats,
)

# Expose logger for backward compatibility
from attune.logging_config import get_logger as _get_logger
from attune.workflow_fixall import (  # noqa: F401
    cmd_fix_all,
    fix_all_workflow,
)
from attune.workflow_learn import (  # noqa: F401
    cmd_learn,
    learn_workflow,
)

# ---------------------------------------------------------------------------
# Workflow functions and CLI handlers
#
# Each submodule resolves helpers via sys.modules["attune.workflow_commands"]
# at call time, so monkeypatch.setattr(workflow_commands, "_run_command", ...)
# is visible to the implementations.
# ---------------------------------------------------------------------------
from attune.workflow_morning import (  # noqa: F401
    cmd_morning,
    morning_workflow,
)
from attune.workflow_ship import (  # noqa: F401
    _run_security_only,
    _run_tests_only,
    cmd_ship,
    ship_workflow,
)

logger = _get_logger(__name__)
