"""Complete Workflow Example

Demonstrates the full Attune AI 4.7.0 workflow:
- SessionStart → Hooks fire, context restored
- Commands → Execute with full context
- Learning → Extract patterns from interactions
- SessionEnd → Save state, evaluate session

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
https://github.com/affaan-m/everything-claude-code (MIT License)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from attune.agents_md import AgentRegistry
from attune.context import CompactState, ContextManager
from attune.context.compaction import PatternSummary
from attune.hooks.config import HookEvent
from attune.hooks.registry import HookRegistry
from attune.learning import (
    LearnedSkillsStorage,
    PatternExtractor,
    SessionEvaluator,
)


class EmpathyWorkflow:
    """Orchestrates the complete Attune AI workflow."""

    def __init__(self, user_id: str, storage_dir: Path):
        self.user_id = user_id
        self.storage_dir = storage_dir

        # Initialize all components
        self.hook_registry = HookRegistry()
        self.context_manager = ContextManager(storage_dir=storage_dir / "context")
        self.learning_storage = LearnedSkillsStorage(storage_dir=storage_dir / "learning")
        self.evaluator = SessionEvaluator()
        self.extractor = PatternExtractor()
        self.agent_registry = AgentRegistry()

        # Session state
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.interactions: list[dict[str, Any]] = []
        self.corrections: list[dict[str, Any]] = []

        # Register hooks
        self._register_hooks()

    def _register_hooks(self):
        """Register session lifecycle hooks."""

        # Session start: restore context
        def session_start_handler(ctx):
            print(f"[HOOK] Session starting for user: {ctx.get('user_id')}")
            state = self.context_manager.restore_state(self.user_id)
            if state:
                print(f"[HOOK] Restored trust level: {state.trust_level}")
                print(f"[HOOK] Restored empathy level: {state.empathy_level}")
                if state.pending_handoff:
                    print(f"[HOOK] Pending work: {state.pending_handoff.situation}")
            return {"success": True, "restored": state is not None}

        # Pre-compact: save state
        def pre_compact_handler(ctx):
            print("[HOOK] Pre-compact: saving state...")
            return {"success": True}

        # Session end: evaluate and learn
        def session_end_handler(ctx):
            print("[HOOK] Session ending: evaluating for learning...")
            quality = self.evaluator.evaluate(
                interaction_count=len(self.interactions),
                corrections_count=len(self.corrections),
                error_resolutions=ctx.get("error_resolutions", 0),
                explicit_preferences=ctx.get("preferences_count", 0),
            )
            print(f"[HOOK] Session quality: {quality.value}")
            return {"success": True, "quality": quality.value}

        self.hook_registry.register(HookEvent.SESSION_START, session_start_handler)
        self.hook_registry.register(HookEvent.PRE_COMPACT, pre_compact_handler)
        self.hook_registry.register(HookEvent.SESSION_END, session_end_handler)

    def start_session(self):
        """Start a new session."""
        print("\n" + "=" * 60)
        print("SESSION START")
        print("=" * 60)

        self.hook_registry.fire_sync(
            HookEvent.SESSION_START,
            {"user_id": self.user_id, "session_id": self.session_id},
        )

        self.context_manager.session_id = self.session_id
        self.context_manager.current_phase = "active"

    def record_interaction(self, user_input: str, response: str):
        """Record an interaction."""
        self.interactions.append(
            {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "response": response,
            }
        )
        print(f"\n[INTERACTION] Recorded: {user_input[:50]}...")

    def record_correction(self, original: str, corrected: str, reason: str):
        """Record a user correction (valuable for learning)."""
        self.corrections.append(
            {
                "original": original,
                "corrected": corrected,
                "reason": reason,
            }
        )
        print(f"\n[CORRECTION] Recorded: '{original}' → '{corrected}'")

    def save_state(self, trust_level: float = 0.75, empathy_level: int = 3):
        """Save current state for later restoration."""
        print("\n" + "-" * 40)
        print("SAVING STATE")
        print("-" * 40)

        self.hook_registry.fire_sync(HookEvent.PRE_COMPACT, {"user_id": self.user_id})

        # Create handoff for continuity
        handoff = self.context_manager.set_handoff(
            situation=f"Session {self.session_id} in progress",
            background=f"{len(self.interactions)} interactions recorded",
            assessment="Session data collected for learning",
            recommendation="Review extracted patterns on next session",
            priority="normal",
        )

        # Convert learned patterns to summaries
        patterns = self.learning_storage.get_all_patterns(self.user_id)
        pattern_summaries = [
            PatternSummary(
                pattern_type=p.category.value,
                trigger=p.trigger,
                action=p.resolution,
                confidence=p.confidence,
                occurrences=1,
            )
            for p in patterns[:5]  # Top 5
        ]

        # Create and save compact state
        state = CompactState(
            user_id=self.user_id,
            trust_level=trust_level,
            empathy_level=empathy_level,
            detected_patterns=pattern_summaries,
            session_id=self.session_id,
            current_phase=self.context_manager.current_phase,
            completed_phases=self.context_manager.completed_phases,
            pending_handoff=handoff,
            interaction_count=len(self.interactions),
        )

        path = self.context_manager._state_manager.save_state(state)
        print(f"[STATE] Saved to: {path}")

    def extract_patterns(self):
        """Extract patterns from corrections and interactions."""
        print("\n" + "-" * 40)
        print("EXTRACTING PATTERNS")
        print("-" * 40)

        if not self.corrections:
            print("[LEARNING] No corrections to learn from")
            return []

        patterns = self.extractor.extract_corrections(
            corrections=self.corrections,
            session_id=self.session_id,
        )

        for pattern in patterns:
            self.learning_storage.save_pattern(self.user_id, pattern)
            print(f"[LEARNING] Extracted: {pattern.trigger} → {pattern.resolution}")

        return patterns

    def end_session(self):
        """End the session with evaluation."""
        print("\n" + "=" * 60)
        print("SESSION END")
        print("=" * 60)

        # Extract patterns before ending
        patterns = self.extract_patterns()

        # Fire session end hook
        self.hook_registry.fire_sync(
            HookEvent.SESSION_END,
            {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "interaction_count": len(self.interactions),
                "corrections": self.corrections,
                "patterns_extracted": len(patterns),
            },
        )

        # Print summary
        print("\n" + "-" * 40)
        print("SESSION SUMMARY")
        print("-" * 40)
        print(f"Session ID: {self.session_id}")
        print(f"User: {self.user_id}")
        print(f"Interactions: {len(self.interactions)}")
        print(f"Corrections: {len(self.corrections)}")
        print(f"Patterns Extracted: {len(patterns)}")


def main():
    """Run the complete workflow example."""
    print("\n" + "=" * 60)
    print("EMPATHY FRAMEWORK 4.7.0 - COMPLETE WORKFLOW EXAMPLE")
    print("=" * 60)
    print("\nArchitectural patterns inspired by everything-claude-code")
    print("by Affaan Mustafa (MIT License)")
    print("=" * 60)

    # Setup
    storage_dir = Path("./example_storage")
    workflow = EmpathyWorkflow(user_id="demo_user", storage_dir=storage_dir)

    # Start session
    workflow.start_session()

    # Simulate interactions
    workflow.record_interaction(
        user_input="How do I handle errors in async functions?",
        response="Use try/except blocks around await calls.",
    )

    workflow.record_interaction(
        user_input="What about the error message?",
        response="Log the error using print().",
    )

    # User correction - valuable for learning!
    workflow.record_correction(
        original="Log the error using print()",
        corrected="Use the logging module instead",
        reason="Better for production code with configurable levels",
    )

    workflow.record_interaction(
        user_input="Got it, thanks!",
        response="You're welcome! Let me know if you have other questions.",
    )

    # Save state (simulating compaction)
    workflow.save_state(trust_level=0.8, empathy_level=4)

    # End session
    workflow.end_session()

    # Verify stored patterns
    print("\n" + "=" * 60)
    print("VERIFICATION: STORED PATTERNS")
    print("=" * 60)

    patterns = workflow.learning_storage.get_all_patterns("demo_user")
    for p in patterns:
        print(f"\n[PATTERN] {p.category.value}")
        print(f"  Trigger: {p.trigger}")
        print(f"  Resolution: {p.resolution}")
        print(f"  Confidence: {p.confidence:.0%}")

    # Verify saved state
    print("\n" + "=" * 60)
    print("VERIFICATION: SAVED STATE")
    print("=" * 60)

    restored = workflow.context_manager.restore_state("demo_user")
    if restored:
        print(f"\nUser: {restored.user_id}")
        print(f"Trust Level: {restored.trust_level}")
        print(f"Empathy Level: {restored.empathy_level}")
        print(f"Interactions: {restored.interaction_count}")
        if restored.pending_handoff:
            print("\nPending Handoff:")
            print(f"  Situation: {restored.pending_handoff.situation}")
            print(f"  Recommendation: {restored.pending_handoff.recommendation}")

    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
