"""attune_llm.hooks.scripts.security_guard - DEPRECATED. Use attune.hooks.scripts.security_guard instead.

This module re-exports from attune.hooks.scripts.security_guard for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.security_guard is deprecated. "
    "Use attune.hooks.scripts.security_guard instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.security_guard import *  # noqa: F401,F403
