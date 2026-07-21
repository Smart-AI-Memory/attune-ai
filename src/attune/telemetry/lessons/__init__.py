"""Self-Healing Traps & Lesson Synthesis module for Attune AI.

Provides failure capture listeners, lesson synthesizers, and memory hydrators.
"""

from .hydrator import MemoryHydrator
from .listener import TrapFailureListener
from .synthesizer import LessonSynthesizer

__all__ = [
    "TrapFailureListener",
    "LessonSynthesizer",
    "MemoryHydrator",
]
