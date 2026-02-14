"""attune_llm.hooks.scripts.suggest_compact - DEPRECATED. Use attune.hooks.scripts.suggest_compact instead.

This module re-exports from attune.hooks.scripts.suggest_compact for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.suggest_compact is deprecated. "
    "Use attune.hooks.scripts.suggest_compact instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.suggest_compact import *  # noqa: F401,F403
