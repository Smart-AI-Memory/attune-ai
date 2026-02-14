"""attune_llm.learning.evaluator - DEPRECATED. Use attune.learning.evaluator instead.

This module re-exports from attune.learning.evaluator for backward compatibility.
Will be removed in attune-ai v3.0.0.
"""

import warnings

warnings.warn(
    "attune_llm.learning.evaluator is deprecated. Use attune.learning.evaluator instead. "
    "This module will be removed in attune-ai v3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
from attune.learning.evaluator import *  # noqa: F401,F403
