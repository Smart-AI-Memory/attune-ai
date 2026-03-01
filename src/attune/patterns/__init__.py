"""Pattern analysis and management for Attune AI.

Provides pattern confidence tracking, resolution, summarization,
git-based pattern extraction, and contextual pattern injection.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune.patterns.confidence import PatternConfidenceTracker
from attune.patterns.contextual import ContextualPatternInjector
from attune.patterns.git_extractor import GitPatternExtractor
from attune.patterns.resolver import PatternResolver
from attune.patterns.summary import PatternSummaryGenerator

__all__ = [
    "ContextualPatternInjector",
    "GitPatternExtractor",
    "PatternConfidenceTracker",
    "PatternResolver",
    "PatternSummaryGenerator",
]
