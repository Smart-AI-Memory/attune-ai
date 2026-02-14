"""attune_llm.hooks.scripts.session_end - DEPRECATED. Use attune.hooks.scripts.session_end instead.

This module re-exports from attune.hooks.scripts.session_end for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.session_end is deprecated. "
    "Use attune.hooks.scripts.session_end instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.session_end import *  # noqa: F401,F403
