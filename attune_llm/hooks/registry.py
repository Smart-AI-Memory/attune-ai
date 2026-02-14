"""attune_llm.hooks.registry - DEPRECATED. Use attune.hooks.registry instead.

This module re-exports from attune.hooks.registry for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.registry is deprecated. Use attune.hooks.registry instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.registry import *  # noqa: F401,F403
