"""attune_llm.hooks.scripts.session_start - DEPRECATED. Use attune.hooks.scripts.session_start instead.

This module re-exports from attune.hooks.scripts.session_start for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.session_start is deprecated. "
    "Use attune.hooks.scripts.session_start instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.session_start import *  # noqa: F401,F403
