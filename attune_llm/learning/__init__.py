"""attune_llm.learning - DEPRECATED. Use attune.learning instead.

This module re-exports from attune.learning for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.learning is deprecated. Use attune.learning instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.learning import *  # noqa: F401,F403
from attune.learning import __all__  # noqa: F811
