"""attune_llm.learning.storage - DEPRECATED. Use attune.learning.storage instead.

This module re-exports from attune.learning.storage for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.learning.storage is deprecated. Use attune.learning.storage instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.learning.storage import *  # noqa: F401,F403
