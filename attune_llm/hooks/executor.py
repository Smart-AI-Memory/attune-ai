"""attune_llm.hooks.executor - DEPRECATED. Use attune.hooks.executor instead.

This module re-exports from attune.hooks.executor for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.executor is deprecated. Use attune.hooks.executor instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.executor import *  # noqa: F401,F403
