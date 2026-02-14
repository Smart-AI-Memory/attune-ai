"""attune_llm.hooks.scripts.telemetry_hook - DEPRECATED. Use attune.hooks.scripts.telemetry_hook instead.

This module re-exports from attune.hooks.scripts.telemetry_hook for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.telemetry_hook is deprecated. "
    "Use attune.hooks.scripts.telemetry_hook instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.telemetry_hook import *  # noqa: F401,F403
