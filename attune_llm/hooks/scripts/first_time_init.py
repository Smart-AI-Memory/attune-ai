"""attune_llm.hooks.scripts.first_time_init - DEPRECATED. Use attune.hooks.scripts.first_time_init instead.

This module re-exports from attune.hooks.scripts.first_time_init for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.first_time_init is deprecated. "
    "Use attune.hooks.scripts.first_time_init instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.first_time_init import *  # noqa: F401,F403
