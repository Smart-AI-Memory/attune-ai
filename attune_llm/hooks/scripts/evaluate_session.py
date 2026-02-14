"""attune_llm.hooks.scripts.evaluate_session - DEPRECATED. Use attune.hooks.scripts.evaluate_session instead.

This module re-exports from attune.hooks.scripts.evaluate_session for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.hooks.scripts.evaluate_session is deprecated. "
    "Use attune.hooks.scripts.evaluate_session instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.hooks.scripts.evaluate_session import *  # noqa: F401,F403
