"""Collaboration State Persistence.

Provides save/load for CollaborationState across sessions.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from attune.security.path_validation import _validate_file_path


@dataclass
class CollaborationState:
    """Stock & Flow model of AI-human collaboration state.

    Relocated here from the retired Empathy framework ``core`` module so
    ``StateManager`` stays self-contained. ``StateManager`` and this class
    are themselves deprecated and slated for removal in a future release;
    they are no longer used by the attune-ai workflow plugin at runtime.
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
    trust_trajectory: list[float] = field(default_factory=list)

    def update_trust(self, outcome: str) -> None:
        """Update trust stock based on interaction outcome."""
        if outcome == "success":
            self.trust_level += self.trust_building_rate
            self.successful_interventions += 1
        elif outcome == "failure":
            self.trust_level -= self.trust_erosion_rate
            self.failed_interventions += 1

        # Clamp to [0, 1]
        self.trust_level = max(0.0, min(1.0, self.trust_level))
        self.total_interactions += 1
        self.trust_trajectory.append(self.trust_level)

    @property
    def current_level(self) -> float:
        """Get current trust level (alias for trust_level)."""
        return self.trust_level


class StateManager:
    """Persist collaboration state across sessions

    Enables:
    - Long-term trust tracking
    - Historical analytics
    - User personalization
    """

    def __init__(self, storage_path: str = "./attune_state"):
        """Initialize StateManager with a storage directory.

        Args:
            storage_path: Directory for persisting user state JSON files.

        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True, parents=True)

    def save_state(self, user_id: str, state: CollaborationState):
        """Save user's collaboration state to JSON

        Args:
            user_id: User identifier
            state: CollaborationState instance

        Example:
            >>> manager = StateManager()
            >>> manager.save_state("user123", empathy.collaboration_state)

        """
        filepath = self.storage_path / f"{user_id}.json"

        data = {
            "user_id": user_id,
            "trust_level": state.trust_level,
            "total_interactions": state.total_interactions,
            "successful_interventions": state.successful_interventions,
            "failed_interventions": state.failed_interventions,
            "session_start": state.session_start.isoformat(),
            "trust_trajectory": state.trust_trajectory,
            "shared_context": state.shared_context,
            "saved_at": datetime.now().isoformat(),
        }

        validated_path = _validate_file_path(str(filepath))
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_state(self, user_id: str) -> CollaborationState | None:
        """Load user's previous state

        Args:
            user_id: User identifier

        Returns:
            CollaborationState if found, None otherwise

        Example:
            >>> manager = StateManager()
            >>> state = manager.load_state("user123")

        """
        filepath = self.storage_path / f"{user_id}.json"
        validated_path = _validate_file_path(str(filepath), allowed_dir=str(self.storage_path))

        if not validated_path.exists():
            return None

        try:
            with open(validated_path) as f:
                data = json.load(f)

            state = CollaborationState()
            state.trust_level = data["trust_level"]
            state.total_interactions = data["total_interactions"]
            state.successful_interventions = data["successful_interventions"]
            state.failed_interventions = data["failed_interventions"]
            state.session_start = datetime.fromisoformat(data["session_start"])
            state.trust_trajectory = data.get("trust_trajectory", [])
            state.shared_context = data.get("shared_context", {})

            return state

        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file - return None
            return None

    def list_users(self) -> list[str]:
        """List all users with saved state

        Returns:
            List of user IDs

        Example:
            >>> manager = StateManager()
            >>> users = manager.list_users()
            >>> print(f"Found {len(users)} users")

        """
        return [p.stem for p in self.storage_path.glob("*.json")]

    def delete_state(self, user_id: str) -> bool:
        """Delete user's saved state

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if didn't exist

        Example:
            >>> manager = StateManager()
            >>> deleted = manager.delete_state("user123")

        """
        filepath = self.storage_path / f"{user_id}.json"
        validated_path = _validate_file_path(str(filepath), allowed_dir=str(self.storage_path))

        if validated_path.exists():
            validated_path.unlink()
            return True
        return False
