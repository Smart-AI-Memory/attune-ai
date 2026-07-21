"""Friction Matrix module for attune-ai.

Provides 2D risk/clarity evaluation and zone-based interruption governance.
"""

from .ambiguity import AmbiguityEvaluator
from .blast_radius import BlastRadiusClassifier
from .matrix import FrictionDirective, FrictionMatrix, FrictionZone

__all__ = [
    "BlastRadiusClassifier",
    "AmbiguityEvaluator",
    "FrictionMatrix",
    "FrictionZone",
    "FrictionDirective",
]
