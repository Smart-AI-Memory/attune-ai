"""EmpathyOS - Core Implementation

The main entry point for the Attune AI, providing access to all
5 empathy levels and system thinking integrations.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

# Mixin imports (compose EmpathyOS via multiple inheritance)
from .core_modules.empathy_levels import EmpathyLevelsMixin
from .core_modules.feedback_management import FeedbackManagementMixin
from .core_modules.helpers import EmpathyHelpersMixin
from .core_modules.interaction import InteractionMixin
from .core_modules.memory_interface import MemoryInterfaceMixin
from .core_modules.shared_library import SharedLibraryMixin
from .core_modules.short_term_memory import ShortTermMemoryMixin
from .emergence import EmergenceDetector
from .exceptions import ValidationError  # noqa: F401 - re-exported
from .feedback_loops import FeedbackLoopDetector
from .leverage_points import LeveragePoint, LeveragePointAnalyzer  # noqa: F401 - re-exported
from .memory import Classification, UnifiedMemory  # noqa: F401 - re-exported
from .memory.backend import MemoryBackend  # noqa: F401 - re-exported
from .memory.types import (
    AccessTier,  # noqa: F401 - re-exported
    AgentCredentials,
    StagedPattern,  # noqa: F401 - re-exported
)

# Backward compat: re-export RedisShortTermMemory for existing callers
try:
    from .redis_memory import RedisShortTermMemory  # noqa: F401 - re-exported
except ImportError:
    RedisShortTermMemory = None  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    from .pattern_library import PatternLibrary


@dataclass
class InteractionResponse:
    """Response from an interaction with EmpathyOS.

    Attributes:
        level: Empathy level used (1-5)
        response: The response text
        confidence: Confidence score (0.0 to 1.0)
        predictions: Optional list of predictions (for Level 4+)
    """

    level: int
    response: str
    confidence: float = 1.0
    predictions: list[str] | None = None


@dataclass
class CollaborationState:
    """Stock & Flow model of AI-human collaboration

    Tracks:
    - Trust level (stock that accumulates/erodes)
    - Shared context (accumulated understanding)
    - Success/failure rates (quality metrics)
    - Flow rates (how fast trust builds/erodes)
    """

    # Stocks (accumulate over time)
    trust_level: float = 0.5  # 0.0 to 1.0, start neutral
    shared_context: dict = field(default_factory=dict)
    successful_interventions: int = 0
    failed_interventions: int = 0

    # Flow rates (change stocks per interaction)
    trust_building_rate: float = 0.05  # Per successful interaction
    trust_erosion_rate: float = 0.10  # Per failed interaction (erosion faster)
    context_accumulation_rate: float = 0.1

    # Metadata
    session_start: datetime = field(default_factory=datetime.now)
    total_interactions: int = 0
    trust_trajectory: list[float] = field(default_factory=list)  # Historical trust levels

    def update_trust(self, outcome: str):
        """Update trust stock based on interaction outcome"""
        if outcome == "success":
            self.trust_level += self.trust_building_rate
            self.successful_interventions += 1
        elif outcome == "failure":
            self.trust_level -= self.trust_erosion_rate
            self.failed_interventions += 1

        # Clamp to [0, 1]
        self.trust_level = max(0.0, min(1.0, self.trust_level))
        self.total_interactions += 1

        # Track trajectory
        self.trust_trajectory.append(self.trust_level)

    @property
    def current_level(self) -> float:
        """Get current trust level (alias for trust_level)."""
        return self.trust_level


class EmpathyOS(
    InteractionMixin,
    EmpathyLevelsMixin,
    EmpathyHelpersMixin,
    MemoryInterfaceMixin,
    SharedLibraryMixin,
    FeedbackManagementMixin,
    ShortTermMemoryMixin,
):
    """Empathy Operating System for AI-Human Collaboration.

    Integrates:
    - 5-level Empathy Maturity Model
    - Systems Thinking (feedback loops, emergence, leverage points)
    - Tactical Empathy (Voss)
    - Emotional Intelligence (Goleman)
    - Clear Thinking (Naval)

    Goal: Enable AI to operate at Levels 3-4 (Proactive/Anticipatory)

    Example:
        Basic usage with empathy levels::

            from attune import EmpathyOS

            # Create instance targeting Level 4 (Anticipatory)
            empathy = EmpathyOS(user_id="developer_123", target_level=4)

            # Level 1 - Reactive response
            response = empathy.level_1_reactive(
                user_input="How do I optimize database queries?",
                context={"domain": "software"}
            )

            # Level 2 - Guided with follow-up questions
            response = empathy.level_2_guided(
                user_input="I need help with my code",
                context={"task": "debugging"},
                history=[]
            )

        Memory operations::

            # Stash working data (short-term)
            empathy.stash("current_task", {"status": "debugging"})

            # Retrieve later
            task = empathy.retrieve("current_task")

            # Persist patterns (long-term)
            result = empathy.persist_pattern(
                content="Query optimization technique",
                pattern_type="technique"
            )

            # Recall patterns
            pattern = empathy.recall_pattern(result["pattern_id"])

    Methods are organized across mixins for maintainability:

    - **InteractionMixin**: interact(), record_success(), get/reset_collaboration_state()
    - **EmpathyLevelsMixin**: level_1_reactive() through level_5_systems()
    - **EmpathyHelpersMixin**: Private helper methods for empathy levels
    - **MemoryInterfaceMixin**: memory property, persist_pattern(), recall_pattern(), stash(), retrieve()
    - **SharedLibraryMixin**: async context manager, contribute_pattern(), query_patterns()
    - **FeedbackManagementMixin**: monitor_feedback_loops()
    - **ShortTermMemoryMixin**: Redis coordination, signals, pattern staging
    """

    def __init__(
        self,
        user_id: str,
        target_level: int = 3,
        confidence_threshold: float = 0.75,
        logger: logging.Logger | None = None,
        shared_library: PatternLibrary | None = None,
        short_term_memory: MemoryBackend | None = None,
        access_tier: AccessTier = AccessTier.CONTRIBUTOR,
        persistence_enabled: bool = True,
    ):
        """Initialize EmpathyOS

        Args:
            user_id: Unique identifier for user/team
            target_level: Target empathy level (1-5), default 3 (Proactive)
            confidence_threshold: Minimum confidence for anticipatory actions (0.0-1.0)
            logger: Optional logger instance for structured logging
            shared_library: Optional shared PatternLibrary for multi-agent collaboration.
                           When provided, enables agents to share discovered patterns,
                           supporting Level 5 (Systems Empathy) distributed memory networks.
            short_term_memory: Optional MemoryBackend for fast, TTL-based working
                              memory. Accepts any backend (FileSessionMemory, Redis, etc.).
            access_tier: Access tier for this agent (Observer, Contributor, Validator, Steward).
                        Determines what operations the agent can perform on shared memory.
            persistence_enabled: Whether to enable pattern/state persistence (default: True)

        """
        self.user_id = user_id
        self.target_level = target_level
        self.confidence_threshold = confidence_threshold
        self.persistence_enabled = persistence_enabled
        self.logger = logger or logging.getLogger(__name__)
        self.shared_library = shared_library

        # Short-term memory for multi-agent coordination
        self.short_term_memory = short_term_memory
        self.credentials = AgentCredentials(agent_id=user_id, tier=access_tier)

        # Collaboration state tracking
        self.collaboration_state = CollaborationState()

        # System thinking components
        self.feedback_detector = FeedbackLoopDetector()
        self.emergence_detector = EmergenceDetector()
        self.leverage_analyzer = LeveragePointAnalyzer()

        # Pattern storage for Level 3+
        self.user_patterns: list[dict] = []
        self.system_trajectory: list[dict] = []

        # Current empathy level
        self.current_empathy_level = 1

        # Session ID for tracking (generated on first use)
        self._session_id: str | None = None

        # Unified memory (lazily initialized)
        self._unified_memory: UnifiedMemory | None = None
