"""attune_llm.context.manager - DEPRECATED. Use attune.context.manager instead.

This module re-exports from attune.context.manager for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.context.manager is deprecated. Use attune.context.manager instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.context.manager import *  # noqa: F401,F403
