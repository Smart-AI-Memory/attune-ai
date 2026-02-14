"""attune_llm.learning.extractor - DEPRECATED. Use attune.learning.extractor instead.

This module re-exports from attune.learning.extractor for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.learning.extractor is deprecated. Use attune.learning.extractor instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.learning.extractor import *  # noqa: F401,F403
