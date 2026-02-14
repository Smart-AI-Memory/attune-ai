"""attune_llm.hooks.config - DEPRECATED. Use attune.hooks.config instead.

This module re-exports from attune.hooks.config for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.config is deprecated. Use attune.hooks.config instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.config import *  # noqa: F401,F403
