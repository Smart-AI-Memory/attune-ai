"""Empathy LLM - Interaction Handlers

Level-specific interaction handlers (Levels 1-5) and async pattern
detection for EmpathyLLM.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import asyncio
import logging
from typing import Any

from .levels import EmpathyLevel
from .state import CollaborationState, PatternType, UserPattern

logger = logging.getLogger(__name__)


class InteractionMixin:
    """Mixin providing level-based interaction handlers for EmpathyLLM.

    Contains the five empathy-level handlers (reactive through systems)
    and the background pattern detection logic.
    """

    def _build_system_prompt(self, level: int) -> str:
        """Build system prompt including Claude memory (if enabled).

        Claude memory is prepended to the level-specific prompt,
        so instructions from CLAUDE.md files affect all interactions.

        Args:
            level: Empathy level (1-5)

        Returns:
            Complete system prompt
        """
        level_prompt = EmpathyLevel.get_system_prompt(level)

        # If Claude memory is enabled and loaded, prepend it
        if getattr(self, "_cached_memory", None):
            return f"""{self._cached_memory}

---
# Attune AI Instructions
{level_prompt}

Follow the CLAUDE.md instructions above, then apply the Attune AI below.
"""
        return level_prompt

    async def _level_1_reactive(
        self,
        user_input: str,
        state: CollaborationState,
        context: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Level 1: Reactive - Simple Q&A

        No memory, no patterns, just respond to question.
        """
        generate_kwargs: dict[str, Any] = {
            "messages": [{"role": "user", "content": user_input}],
            "system_prompt": self._build_system_prompt(1),
            "temperature": EmpathyLevel.get_temperature_recommendation(1),
            "max_tokens": EmpathyLevel.get_max_tokens_recommendation(1),
        }
        if model_override:
            generate_kwargs["model"] = model_override

        response = await self.provider.generate(**generate_kwargs)

        return {
            "content": response.content,
            "proactive": False,
            "metadata": {"tokens_used": response.tokens_used, "model": response.model},
        }

    async def _level_2_guided(
        self,
        user_input: str,
        state: CollaborationState,
        context: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Level 2: Guided - Ask clarifying questions

        Uses conversation history for context.
        """
        # Include conversation history
        messages = state.get_conversation_history(max_turns=5)
        messages.append({"role": "user", "content": user_input})

        generate_kwargs: dict[str, Any] = {
            "messages": messages,
            "system_prompt": self._build_system_prompt(2),
            "temperature": EmpathyLevel.get_temperature_recommendation(2),
            "max_tokens": EmpathyLevel.get_max_tokens_recommendation(2),
        }
        if model_override:
            generate_kwargs["model"] = model_override

        response = await self.provider.generate(**generate_kwargs)

        return {
            "content": response.content,
            "proactive": False,
            "metadata": {
                "tokens_used": response.tokens_used,
                "model": response.model,
                "history_turns": len(messages) - 1,
            },
        }

    async def _level_3_proactive(
        self,
        user_input: str,
        state: CollaborationState,
        context: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Level 3: Proactive - Act on detected patterns

        Checks for matching patterns and acts proactively.
        """
        # Check for matching pattern
        matching_pattern = state.find_matching_pattern(user_input)

        if matching_pattern:
            # Proactive action based on pattern
            prompt = f"""
User said: "{user_input}"

Pattern detected: When you {matching_pattern.trigger}, you typically {matching_pattern.action}.

Confidence: {matching_pattern.confidence:.0%}. Proactively {matching_pattern.action}.

[Provide the expected result/action]

Was this helpful? If not, I can adjust my pattern detection.
"""

            messages = [{"role": "user", "content": prompt}]
            proactive = True
            pattern_info = {
                "pattern_type": matching_pattern.pattern_type.value,
                "trigger": matching_pattern.trigger,
                "confidence": matching_pattern.confidence,
            }

        else:
            # Standard response + pattern detection
            messages = state.get_conversation_history(max_turns=10)
            messages.append({"role": "user", "content": user_input})
            proactive = False
            pattern_info = None

            # Run pattern detection in background (non-blocking)
            asyncio.create_task(self._detect_patterns_async(state, user_input))

        generate_kwargs: dict[str, Any] = {
            "messages": messages,
            "system_prompt": self._build_system_prompt(3),
            "temperature": EmpathyLevel.get_temperature_recommendation(3),
            "max_tokens": EmpathyLevel.get_max_tokens_recommendation(3),
        }
        if model_override:
            generate_kwargs["model"] = model_override

        response = await self.provider.generate(**generate_kwargs)

        return {
            "content": response.content,
            "proactive": proactive,
            "metadata": {
                "tokens_used": response.tokens_used,
                "model": response.model,
                "pattern": pattern_info,
            },
        }

    async def _level_4_anticipatory(
        self,
        user_input: str,
        state: CollaborationState,
        context: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Level 4: Anticipatory - Predict future needs

        Analyzes trajectory and alerts to future bottlenecks.
        """
        # Build prompt with trajectory analysis context
        trajectory_prompt = f"""
User request: "{user_input}"

COLLABORATION CONTEXT:
- Total interactions: {len(state.interactions)}
- Trust level: {state.trust_level:.2f}
- Detected patterns: {len(state.detected_patterns)}
- Success rate: {state.success_rate:.0%}

TASK:
1. Respond to immediate request
2. Analyze trajectory (where is this headed?)
3. Predict future bottlenecks (if any)
4. Alert with prevention steps (if needed)

Use anticipatory format:
- Current state analysis
- Trajectory prediction
- Alert (if bottleneck predicted)
- Prevention steps (actionable)
- Reasoning (based on experience)
"""

        messages = state.get_conversation_history(max_turns=15)
        messages.append({"role": "user", "content": trajectory_prompt})

        generate_kwargs: dict[str, Any] = {
            "messages": messages,
            "system_prompt": self._build_system_prompt(4),
            "temperature": EmpathyLevel.get_temperature_recommendation(4),
            "max_tokens": EmpathyLevel.get_max_tokens_recommendation(4),
        }
        if model_override:
            generate_kwargs["model"] = model_override

        response = await self.provider.generate(**generate_kwargs)

        return {
            "content": response.content,
            "proactive": True,  # Level 4 is inherently proactive
            "metadata": {
                "tokens_used": response.tokens_used,
                "model": response.model,
                "trajectory_analyzed": True,
                "trust_level": state.trust_level,
            },
        }

    async def _level_5_systems(
        self,
        user_input: str,
        state: CollaborationState,
        context: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Level 5: Systems - Cross-domain pattern learning

        Leverages shared pattern library across domains.
        """
        # Include pattern library context
        pattern_context = ""
        if self.pattern_library:
            pattern_context = f"\n\nSHARED PATTERN LIBRARY:\n{self.pattern_library}"

        prompt = f"""
User request: "{user_input}"

{pattern_context}

TASK:
1. Respond to request
2. Check if relevant cross-domain patterns apply
3. Contribute new patterns if discovered
4. Show how principle generalizes across domains
"""

        messages = state.get_conversation_history(max_turns=20)
        messages.append({"role": "user", "content": prompt})

        generate_kwargs: dict[str, Any] = {
            "messages": messages,
            "system_prompt": self._build_system_prompt(5),
            "temperature": EmpathyLevel.get_temperature_recommendation(5),
            "max_tokens": EmpathyLevel.get_max_tokens_recommendation(5),
        }
        if model_override:
            generate_kwargs["model"] = model_override

        response = await self.provider.generate(**generate_kwargs)

        return {
            "content": response.content,
            "proactive": True,
            "metadata": {
                "tokens_used": response.tokens_used,
                "model": response.model,
                "pattern_library_size": len(self.pattern_library),
                "systems_level": True,
            },
        }

    async def _detect_patterns_async(
        self,
        state: CollaborationState,
        current_input: str,
    ) -> None:
        """Detect user behavior patterns in background.

        Analyzes conversation history to identify:
        - Sequential patterns: User always does X then Y
        - Preference patterns: User prefers certain formats/styles
        - Temporal patterns: User does X at specific times
        - Conditional patterns: When Z happens, user does X

        This runs asynchronously to avoid blocking the main response.
        Detected patterns enable Level 3 proactive interactions.
        """
        try:
            from datetime import datetime

            interactions = state.interactions
            if len(interactions) < 3:
                # Need at least 3 interactions to detect patterns
                return

            # Analyze recent interactions for sequential patterns
            recent = interactions[-10:]  # Last 10 interactions
            user_messages = [i for i in recent if i.role == "user"]

            if len(user_messages) < 2:
                return

            # Pattern 1: Sequential patterns (X followed by Y)
            for i in range(len(user_messages) - 1):
                current = user_messages[i].content.lower()
                next_msg = user_messages[i + 1].content.lower()

                # Detect common sequential patterns
                sequential_triggers = [
                    ("review", "fix"),  # Review then fix
                    ("debug", "test"),  # Debug then test
                    ("implement", "test"),  # Implement then test
                    ("refactor", "review"),  # Refactor then review
                ]

                for trigger, action in sequential_triggers:
                    if trigger in current and action in next_msg:
                        pattern = UserPattern(
                            pattern_type=PatternType.SEQUENTIAL,
                            trigger=trigger,
                            action=f"Typically follows with {action}",
                            confidence=0.6 + (0.1 * min(i, 3)),
                            occurrences=1,
                            last_seen=datetime.now(),
                            context={"detected_from": "sequential_analysis"},
                        )
                        state.add_pattern(pattern)

            # Pattern 2: Preference patterns
            preference_indicators = {
                "concise": "brief, concise responses",
                "detailed": "comprehensive, detailed responses",
                "example": "responses with examples",
                "step by step": "step-by-step explanations",
                "code": "code-focused responses",
            }

            for indicator, preference in preference_indicators.items():
                occurrences = sum(1 for m in user_messages if indicator in m.content.lower())
                if occurrences >= 2:
                    pattern = UserPattern(
                        pattern_type=PatternType.PREFERENCE,
                        trigger=indicator,
                        action=f"User prefers {preference}",
                        confidence=min(0.9, 0.5 + (0.1 * occurrences)),
                        occurrences=occurrences,
                        last_seen=datetime.now(),
                        context={"preference_type": indicator},
                    )
                    state.add_pattern(pattern)

            # Pattern 3: Conditional patterns (error -> debug)
            conditional_triggers = [
                ("error", "debug", "When errors occur, user asks for debugging"),
                ("failed", "fix", "When tests fail, user asks for fixes"),
                ("slow", "optimize", "When performance issues arise, user asks for optimization"),
            ]

            for condition, response_keyword, description in conditional_triggers:
                for i, msg in enumerate(user_messages[:-1]):
                    if condition in msg.content.lower():
                        next_msg = user_messages[i + 1].content.lower()
                        if response_keyword in next_msg:
                            pattern = UserPattern(
                                pattern_type=PatternType.CONDITIONAL,
                                trigger=condition,
                                action=description,
                                confidence=0.7,
                                occurrences=1,
                                last_seen=datetime.now(),
                                context={"condition": condition, "response": response_keyword},
                            )
                            state.add_pattern(pattern)

            logger.debug(
                f"Pattern detection complete. Detected {len(state.detected_patterns)} patterns.",
            )

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Pattern detection should never break the main flow
            logger.warning(f"Pattern detection error (non-critical): {e}")
